"""
공용 인덱싱 스크립트 (5개 버전 공통)

- PDF 경로:  week-5/pdf/
- DB 경로:   week-5/chroma_db/            (단일 공용 ChromaDB)
- 컬렉션명:   medical_aid_unified
- .env:      week-5/DChanhong/basic/.env   (OPENAI_API_KEY 재사용)

실행:
    cd week-5/DChanhong
    python indexing.py              # 기존 컬렉션 삭제 후 전체 재인덱싱
    python indexing.py --pdf-dir /custom/path
    python indexing.py --db-dir /custom/path
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Any

import pandas as pd
import pdfplumber
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# =============================================================================
# 경로 상수
# =============================================================================
THIS_DIR = Path(__file__).resolve().parent          # week-5/DChanhong
WEEK5_DIR = THIS_DIR.parent                          # week-5
DEFAULT_PDF_DIR = WEEK5_DIR / "pdf"
DEFAULT_DB_DIR = WEEK5_DIR / "chroma_db"
DEFAULT_ENV = THIS_DIR / "basic" / ".env"

COLLECTION_NAME = "medical_aid_unified"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL_DEFAULT = "text-embedding-3-small"


# =============================================================================
# PDF 파서 (각 버전의 pdf_parser.py 와 동일 로직을 인라인화)
# =============================================================================

# 비정상 표 필터링 임계값:
# 2017/2023 PDF 에서 pdfplumber 가 페이지 레이아웃을 거대 표(12행 × 147열, 대부분 None)
# 로 오인 → markdown 변환 시 파이프 기호만 30,000자 이상 뿜어냄.
# 이런 "유령 표"를 제거하기 위한 기준.
MAX_TABLE_COLS = 30          # 30열 넘으면 레이아웃 표로 간주 → skip
MIN_NON_EMPTY_RATIO = 0.3    # 셀의 30% 미만이 채워져 있으면 → skip


def _is_valid_table(table: List[List[Any]]) -> bool:
    if not table or not table[0]:
        return False
    if len(table[0]) > MAX_TABLE_COLS:
        return False
    rows = len(table)
    cols = len(table[0])
    total = rows * cols
    if total == 0:
        return False
    non_empty = sum(
        1 for row in table for cell in row if cell and str(cell).strip()
    )
    return (non_empty / total) >= MIN_NON_EMPTY_RATIO


def table_to_markdown(table_data: List[List[Any]]) -> str:
    if not table_data or not any(table_data):
        return ""
    try:
        df = pd.DataFrame(table_data[1:], columns=table_data[0]).fillna("")
        return "\n" + df.to_markdown(index=False) + "\n"
    except Exception:
        try:
            df = pd.DataFrame(table_data).fillna("")
            return "\n" + df.to_markdown(index=False, header=False) + "\n"
        except Exception:
            return ""


def parse_pdf(file_path: Path) -> List[Document]:
    documents: List[Document] = []
    file_name = file_path.name

    # 20\d{2} → 2016 ~ 2099 까지 매칭 (기존 202\d 는 2016~2019 놓침)
    year_match = re.search(r"20\d{2}", file_name)
    source_year = year_match.group() if year_match else "unknown"

    print(f"[{source_year}] 파싱 시작: {file_name}")

    skipped_tables = 0
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            table_markdowns = []
            for table in page.extract_tables():
                if not _is_valid_table(table):
                    skipped_tables += 1
                    continue
                md_table = table_to_markdown(table)
                if md_table.strip():
                    table_markdowns.append(md_table)

            combined = text
            if table_markdowns:
                combined += "\n\n### [표 데이터]\n" + "\n".join(table_markdowns)

            if combined.strip():
                documents.append(
                    Document(
                        page_content=combined,
                        metadata={
                            "source": file_name,
                            "source_year": source_year,
                            "page": page_num + 1,
                        },
                    )
                )

    print(
        f"[{source_year}] 파싱 완료: {len(documents)} 페이지"
        + (f" (유령 표 {skipped_tables}개 skip)" if skipped_tables else "")
    )
    return documents


# =============================================================================
# 인덱싱 파이프라인
# =============================================================================
def load_env(env_path: Path) -> None:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"[env] loaded: {env_path}")
    else:
        print(f"[env] {env_path} not found — rely on shell env")
        load_dotenv(override=True)


def build_embeddings() -> OpenAIEmbeddings:
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL_DEFAULT)
    if not api_key:
        print("[error] OPENAI_API_KEY 가 비어있습니다", file=sys.stderr)
        sys.exit(1)
    print(f"[embeddings] model={model}")
    return OpenAIEmbeddings(model=model, openai_api_key=api_key)


def run_indexing(pdf_dir: Path, db_dir: Path) -> dict:
    if not pdf_dir.exists():
        print(f"[error] PDF 경로 없음: {pdf_dir}", file=sys.stderr)
        sys.exit(1)

    pdf_files = sorted([f for f in pdf_dir.glob("*.pdf")])
    if not pdf_files:
        print(f"[error] PDF 없음: {pdf_dir}", file=sys.stderr)
        sys.exit(1)

    db_dir.mkdir(parents=True, exist_ok=True)

    embeddings = build_embeddings()

    # 1) 기존 컬렉션 삭제 후 재생성 (idempotent)
    vector_store = Chroma(
        persist_directory=str(db_dir),
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )
    try:
        vector_store.delete_collection()
        print(f"[indexing] 기존 컬렉션 삭제: {COLLECTION_NAME}")
    except Exception as e:
        print(f"[indexing] delete_collection 경고: {e}")

    vector_store = Chroma(
        persist_directory=str(db_dir),
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )

    # 2) 전체 PDF 파싱
    all_documents: List[Document] = []
    for pdf_file in pdf_files:
        all_documents.extend(parse_pdf(pdf_file))

    # 3) 청킹
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )
    chunks = splitter.split_documents(all_documents)

    # 4) chunk_id 부여 (RRF·Rerank 중복제거 키)
    for chunk in chunks:
        src = chunk.metadata.get("source", "unknown")
        page = chunk.metadata.get("page", "-")
        start = chunk.metadata.get("start_index", 0)
        chunk.metadata["chunk_id"] = f"{src}__p{page}__s{start}"

    # 5) 삽입
    vector_store.add_documents(chunks)

    # 6) 요약
    year_counts: dict[str, int] = {}
    for c in chunks:
        y = c.metadata.get("source_year", "unknown")
        year_counts[y] = year_counts.get(y, 0) + 1

    return {
        "files": [f.name for f in pdf_files],
        "total_chunks": len(chunks),
        "chunks_by_year": dict(sorted(year_counts.items())),
        "db_dir": str(db_dir),
        "collection": COLLECTION_NAME,
    }


# =============================================================================
# CLI
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Week-5 공용 ChromaDB 인덱싱")
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()

    print(f"[paths] pdf_dir = {args.pdf_dir}")
    print(f"[paths] db_dir  = {args.db_dir}")

    load_env(args.env)
    summary = run_indexing(args.pdf_dir, args.db_dir)

    print("\n================ 인덱싱 완료 ================")
    print(f"파일 수       : {len(summary['files'])}")
    print(f"총 청크 수    : {summary['total_chunks']}")
    print(f"컬렉션        : {summary['collection']}")
    print(f"DB 경로       : {summary['db_dir']}")
    print("년도별 청크   :")
    for y, n in summary["chunks_by_year"].items():
        print(f"   {y} : {n}")


if __name__ == "__main__":
    main()
