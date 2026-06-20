"""
evaluate_ragas.py — Ragas 5-metric scoring for one RAG version's output.

입력: RAG 버전 별로 /api/v1/rag/evaluate 가 생성한 evaluation_results.jsonl
출력: ragas_scores.csv  (문항별 × 5메트릭 점수표)

사용 예:
    # Basic 버전, 15문항 전체
    python evaluate_ragas.py \
        --input basic/data/basic/0/evaluation_results.jsonl

    # 파일럿 (처음 5문항만)
    python evaluate_ragas.py \
        --input basic/data/basic/0/evaluation_results.jsonl \
        --limit 5 \
        --output /tmp/basic_pilot.csv

평가 구성:
  - 평가용 LLM      : Claude Sonnet 4.5 (temperature=0)  — 생성 LLM(Gemini)과 다른 패밀리
  - 평가용 임베딩   : OpenAI text-embedding-3-small
  - 한국어 프롬프트: adapt_prompts(language="korean") → set_prompts
  - 메트릭 5종     : ContextRecall, LLMContextPrecisionWithReference,
                     Faithfulness, ResponseRelevancy, AnswerCorrectness
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from ragas import EvaluationDataset, evaluate
from ragas.dataset_schema import SingleTurnSample
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
# ragas.metrics.collections 버전은 InstructorLLM 만 받으므로
# TASK.md 에 맞춰 LangchainLLMWrapper 호환되는 레거시 경로 사용.
# (DeprecationWarning 뜨지만 기능 정상, v1.0 까지는 지원)
from ragas.metrics import (
    AnswerCorrectness,
    ContextRecall,
    Faithfulness,
    LLMContextPrecisionWithReference,
    ResponseRelevancy,
)

from langchain_openai import ChatOpenAI, OpenAIEmbeddings


# =============================================================================
# 기본값
# =============================================================================
THIS_DIR = Path(__file__).resolve().parent            # week-5/DChanhong
DEFAULT_ENV = THIS_DIR / "basic" / ".env"             # 공용 .env 재사용
# 평가용 LLM: GPT-4o-mini (생성은 Gemini → 패밀리 분리 OK, 비용 저렴)
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING = "text-embedding-3-small"


# =============================================================================
# 환경·데이터 로드
# =============================================================================
def load_env(env_path: Path) -> None:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"[env] loaded: {env_path}")
    else:
        load_dotenv(override=True)
        print(f"[env] {env_path} 없음 — shell env 사용")


def load_dataset(jsonl_path: Path, limit: int | None) -> EvaluationDataset:
    samples: List[SingleTurnSample] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                break
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            samples.append(
                SingleTurnSample(
                    user_input=d["question"],
                    response=d.get("response", ""),
                    retrieved_contexts=d.get("retrieved_contexts", []) or [],
                    reference=d.get("ground_truth", "") or "",
                    reference_contexts=d.get("ground_truth_contexts", []) or [],
                )
            )
    print(f"[data] {len(samples)} sample(s) 로드: {jsonl_path}")
    return EvaluationDataset(samples=samples)


# =============================================================================
# 평가 LLM / 임베딩
# =============================================================================
def build_evaluator(model: str, embedding_model: str):
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("[error] OPENAI_API_KEY 가 없습니다", file=sys.stderr)
        sys.exit(1)

    # 평가용 LLM: OpenAI (생성 LLM 인 Gemini 와 다른 패밀리)
    llm = ChatOpenAI(
        model=model,
        temperature=0,
        openai_api_key=openai_key,
    )
    emb = OpenAIEmbeddings(
        model=embedding_model,
        openai_api_key=openai_key,
    )
    return LangchainLLMWrapper(llm), LangchainEmbeddingsWrapper(emb)


async def _adapt_to_korean(metrics, evaluator_llm):
    """Ragas 0.4+ 에서 adapt_prompts 가 coroutine. 각 메트릭 순회하며 한국어 적용."""
    for m in metrics:
        name = m.__class__.__name__
        try:
            adapted = await m.adapt_prompts(language="korean", llm=evaluator_llm)
            m.set_prompts(**adapted)
            print(f"[prompts] {name}: 한국어 어댑트 OK ({len(adapted)}개 프롬프트)")
        except Exception as e:
            # 어댑트 실패해도 영문 프롬프트로 동작함
            print(f"[prompts] {name}: 한국어 어댑트 실패 → 영문 그대로 ({e})")


def build_metrics(evaluator_llm, evaluator_emb, korean: bool = True):
    """5개 메트릭 인스턴스 + (옵션) 한국어 프롬프트 적용."""
    metrics = [
        ContextRecall(llm=evaluator_llm),
        LLMContextPrecisionWithReference(llm=evaluator_llm),
        Faithfulness(llm=evaluator_llm),
        ResponseRelevancy(llm=evaluator_llm, embeddings=evaluator_emb),
        AnswerCorrectness(llm=evaluator_llm, embeddings=evaluator_emb),
    ]

    if korean:
        asyncio.run(_adapt_to_korean(metrics, evaluator_llm))

    return metrics


# =============================================================================
# 메인
# =============================================================================
def main():
    ap = argparse.ArgumentParser(description="Ragas 5-metric scoring")
    ap.add_argument("--input", type=Path, required=True,
                    help="evaluation_results.jsonl 경로")
    ap.add_argument("--output", type=Path, default=None,
                    help="결과 CSV 경로 (기본: <input_dir>/ragas_scores.csv)")
    ap.add_argument("--limit", type=int, default=None,
                    help="처음 N 문항만 (파일럿)")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help=f"평가용 LLM (기본: {DEFAULT_MODEL})")
    ap.add_argument("--embedding-model", default=DEFAULT_EMBEDDING,
                    help=f"평가용 embedding (기본: {DEFAULT_EMBEDDING})")
    ap.add_argument("--env", type=Path, default=DEFAULT_ENV,
                    help=f".env 경로 (기본: {DEFAULT_ENV})")
    ap.add_argument("--no-korean", action="store_true",
                    help="한국어 프롬프트 어댑트 스킵 (영문 그대로)")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"[error] 입력 파일 없음: {args.input}", file=sys.stderr)
        sys.exit(1)

    load_env(args.env)

    # 1) Dataset
    dataset = load_dataset(args.input, args.limit)
    if len(dataset) == 0:
        print("[error] 샘플 0개", file=sys.stderr)
        sys.exit(1)

    # 2) Evaluator
    print(f"[model] LLM       : {args.model}")
    print(f"[model] embedding : {args.embedding_model}")
    evaluator_llm, evaluator_emb = build_evaluator(args.model, args.embedding_model)

    # 3) Metrics (한국어 어댑트 포함)
    metrics = build_metrics(evaluator_llm, evaluator_emb, korean=not args.no_korean)

    # 4) Evaluate
    print(f"\n[evaluate] 시작 (문항 {len(dataset)} × 메트릭 {len(metrics)})")
    t0 = time.time()
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_emb,
    )
    elapsed = time.time() - t0
    print(f"[evaluate] 완료: {elapsed:.1f}s")

    # 5) Save
    df = result.to_pandas()
    out_path = args.output or (args.input.parent / "ragas_scores.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"[save] {out_path}")

    # 6) Summary
    print("\n===== 평균 스코어 =====")
    num_cols = df.select_dtypes(include="number").columns
    for c in num_cols:
        mean = df[c].mean()
        nan_count = df[c].isna().sum()
        tag = f" ({nan_count} NaN)" if nan_count else ""
        print(f"  {c:<35} {mean:.3f}{tag}")


if __name__ == "__main__":
    main()
