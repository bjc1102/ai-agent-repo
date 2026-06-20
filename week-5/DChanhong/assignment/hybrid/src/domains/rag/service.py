import os
from pathlib import Path
import json
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from kiwipiepy import Kiwi

from src.core.config import settings, BASE_DIR
from .schemas import QueryRequest, QueryResponse, SourceDocument


# =============================================================================
# BM25 용 한국어 형태소 토크나이저
# Kiwi 는 한국어를 "형태소" 단위로 쪼개주는 라이브러리.
# 예: "본인부담금은" → ["본인", "부담", "금", "은"]
# BM25 는 어휘(키워드) 기반 검색이라, 한국어 조사 처리가 검색 품질에 직결됨.
# =============================================================================
kiwi = Kiwi()


def korean_tokenizer(text: str) -> List[str]:
    return [token.form for token in kiwi.tokenize(text)]


class HybridRAGService:
    """
    Hybrid RAG:
      1) Dense retrieval  (공용 ChromaDB, 의미 유사도)
      2) Sparse retrieval (BM25 + Kiwi 형태소, 키워드 매칭, 런타임에 ChromaDB 내용으로 구축)
      3) RRF (Reciprocal Rank Fusion) 로 두 결과를 결합

    인덱싱은 week-5/DChanhong/indexing.py 로 1회 수행.
    """

    RRF_K = 60  # RRF 상수 (논문 표준값)

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0,
        )

        self.vector_store = None
        self.bm25: BM25Okapi | None = None
        self.bm25_docs: List[Document] = []

        self._init_vector_store()
        self._sync_bm25_index()

    # ------------------------------------------------------------------
    # 초기화 / 인덱싱
    # ------------------------------------------------------------------
    def _init_vector_store(self):
        self.vector_store = Chroma(
            persist_directory=settings.SHARED_DB_DIR,
            embedding_function=self.embeddings,
            collection_name=settings.SHARED_COLLECTION,
        )

    def _sync_bm25_index(self):
        """ChromaDB 에 있는 문서들을 읽어서 BM25 인덱스를 메모리에 재구성."""
        try:
            if not self.vector_store:
                return

            all_data = self.vector_store.get()
            if not all_data or not all_data.get("documents"):
                print("[bm25] 벡터 스토어에 인덱싱된 문서 없음")
                return

            documents = []
            for i in range(len(all_data["documents"])):
                documents.append(
                    Document(
                        page_content=all_data["documents"][i],
                        metadata=all_data["metadatas"][i]
                        if all_data["metadatas"]
                        else {},
                    )
                )
            self.bm25_docs = documents

            tokenized_corpus = [korean_tokenizer(d.page_content) for d in documents]
            self.bm25 = BM25Okapi(tokenized_corpus)
            print(f"[bm25] {len(documents)} 청크 인덱싱 완료")
        except Exception as e:
            print(f"[bm25] 인덱스 동기화 실패: {e}")

    # ------------------------------------------------------------------
    # 검색 + 생성
    # ------------------------------------------------------------------
    async def get_answer(self, request: QueryRequest) -> QueryResponse:
        """Hybrid (Dense + BM25 + RRF) 검색 후 LLM 생성"""
        if not self.vector_store:
            return QueryResponse(
                answer="벡터 스토어가 초기화되지 않았습니다.",
                retrieved_contexts=[],
            )

        if not self.bm25:
            # BM25 가 없으면 Dense 단독으로 폴백
            print("[hybrid] BM25 없음 → Dense 단독 폴백")
            retriever = self.vector_store.as_retriever(
                search_kwargs={"k": request.k}
            )
            docs = retriever.invoke(request.question)
            return await self._generate(request, docs)

        # 1) Dense 검색 (Top 20)
        vector_results = self.vector_store.similarity_search(request.question, k=20)

        # 2) Sparse (BM25) 검색 (Top 20)
        tokenized_query = korean_tokenizer(request.question)
        bm25_results = self.bm25.get_top_n(tokenized_query, self.bm25_docs, n=20)

        # 3) RRF 결합
        final_docs = self._rrf_fuse(vector_results, bm25_results, top_k=request.k)

        return await self._generate(request, final_docs)

    @staticmethod
    def _doc_key(doc: Document) -> str:
        """문서 고유 키. chunk_id 가 있으면 그걸, 없으면 page_content 로 폴백."""
        return doc.metadata.get("chunk_id") or doc.page_content

    def _rrf_fuse(
        self,
        dense_results: List[Document],
        sparse_results: List[Document],
        top_k: int,
    ) -> List[Document]:
        """
        Reciprocal Rank Fusion (RRF)
          점수 = 1 / (rank + k),  k=60
        - rank 가 낮을수록(상위일수록) 점수 ↑
        - 두 검색 결과에서 모두 등장한 문서가 높은 점수를 얻음

        키로는 chunk_id 를 사용 (page_content 를 쓰면 2025/2026 같은
        다년도 청크가 한 항목으로 병합되어버림).
        """
        rrf_scores: dict[str, float] = {}

        # Dense 결과 점수 누적
        for rank, doc in enumerate(dense_results):
            key = self._doc_key(doc)
            rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (rank + 1 + self.RRF_K)

        # Sparse 결과 점수 누적
        for rank, doc in enumerate(sparse_results):
            key = self._doc_key(doc)
            rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (rank + 1 + self.RRF_K)

        # 원본 Document 객체 보존 (metadata 살리기)
        all_docs_map = {
            self._doc_key(d): d for d in (dense_results + list(sparse_results))
        }

        sorted_keys = sorted(
            rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
        )
        return [all_docs_map[k] for k in sorted_keys[:top_k]]

    async def _generate(
        self, request: QueryRequest, docs: List[Document]
    ) -> QueryResponse:
        context_parts = []
        sources = []
        retrieved_contexts = []

        for doc in docs:
            year = doc.metadata.get("source_year", "unknown")
            file = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", "-")

            context_parts.append(
                f"[출처: {year}년 {file}, {page}p]\n{doc.page_content}"
            )
            retrieved_contexts.append(doc.page_content)
            sources.append(
                SourceDocument(content=doc.page_content, metadata=doc.metadata)
            )

        context = "\n\n---\n\n".join(context_parts)
        prompt = (
            "아래 컨텍스트를 바탕으로 질문에 답하세요.\n"
            "각 컨텍스트에는 출처 년도가 표시되어 있습니다. "
            "질문이 특정 년도를 묻는 경우 해당 년도의 정보만 사용하세요.\n"
            "컨텍스트에 없는 내용은 \"정보를 찾을 수 없습니다\"라고 답하세요.\n\n"
            f"컨텍스트:\n{context}\n\n"
            f"질문: {request.question}\n\n답변:"
        )

        response = await self.llm.ainvoke(prompt)
        answer_text = response.content
        if isinstance(answer_text, list):
            answer_text = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in answer_text
            )

        return QueryResponse(
            answer=str(answer_text),
            retrieved_contexts=retrieved_contexts,
            sources=sources if request.include_sources else None,
        )

    # ------------------------------------------------------------------
    # 평가 (Ragas 입력용 JSONL 생성)
    # ------------------------------------------------------------------
    async def run_evaluation(self) -> dict:
        input_file = Path(settings.SHARED_DATA_DIR) / "golden_dataset_v2.jsonl"
        base_output_dir = (BASE_DIR / "data" / "hybrid").resolve()
        os.makedirs(base_output_dir, exist_ok=True)

        index = 0
        while (base_output_dir / str(index)).exists():
            index += 1
        output_dir = base_output_dir / str(index)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "evaluation_results.jsonl"

        if not input_file.exists():
            return {"error": f"golden dataset 없음: {input_file}"}

        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        processed = 0
        for line in lines:
            try:
                data = json.loads(line)
                req = QueryRequest(
                    question=data["question"], include_sources=False
                )
                resp = await self.get_answer(req)

                out = {
                    "question": data["question"],
                    "ground_truth": data.get("ground_truth", ""),
                    "ground_truth_contexts": data.get("ground_truth_contexts", []),
                    "response": resp.answer,
                    "retrieved_contexts": resp.retrieved_contexts,
                    "difficulty": data.get("difficulty"),
                    "source_year": data.get("source_year"),
                }
                with open(output_file, "a", encoding="utf-8") as out_f:
                    out_f.write(json.dumps(out, ensure_ascii=False) + "\n")
                processed += 1
                print(f"[{processed}/{len(lines)}] {data['question'][:30]}...")
            except Exception as e:
                print(f"평가 실패: {e}")
                continue

        return {
            "status": "success",
            "index": index,
            "total": len(lines),
            "processed": processed,
            "output_file": str(output_file),
        }


rag_service = HybridRAGService()
