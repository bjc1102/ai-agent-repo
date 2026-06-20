# Rerank RAG — Ragas 평가 결과 메모

- **파이프라인**: Dense (ChromaDB) Top 20 + BM25 Top 20 → union → **Cohere Rerank (`rerank-multilingual-v3.0`)** → Top 10
- **생성 모델**: gemini-3-flash-preview (5버전 공통)
- **평가용 LLM**: GPT-4o-mini
- **평가용 임베딩**: text-embedding-3-small
- **Golden Dataset**: 15문항
- **평가 소요 시간**: 276초 (≈ 4분 36초), /evaluate 호출은 Cohere rate limit 으로 2분 1초
- **결과 CSV**: `ragas_scores.csv`

---

## 전체 평균 (15문항) — vs Basic, vs Hybrid

| 메트릭 | Basic | Hybrid | **Rerank** | ΔHb→Re | 총 Δ(B→R) |
|---|---|---|---|---|---|
| **Context Recall** | 1.000 | 1.000 | **0.933** | **-0.067** ⚠️ | -0.067 |
| **Context Precision (w/ ref)** | 0.778 | 0.879 | **0.941** | **+0.062** ↑ | **+0.163** |
| **Faithfulness** | 0.554 | 0.780 | **0.837** | **+0.057** ↑ | **+0.283** |
| **Answer Relevancy** | 0.556 | 0.755 | **0.772** | +0.017 | **+0.216** |
| **Answer Correctness** | 0.637 | 0.699 | **0.698** | -0.001 ≈ | +0.061 |

### 해석
- **Rerank 의 본질: Precision ↑ / Recall ↓ trade-off**
  - top 20 union → top 10 으로 압축하면서 **정답 근거 일부가 10위 밖으로 밀림** (CRec 첫 감소)
  - 동시에 **상위 10개의 순위 품질** 은 현저히 개선 (CPrec 0.941 로 최고)
- **Faithfulness 추가 +0.057**: 상위 청크가 "진짜 근거" 일수록 Gemini 가 더 충실히 답변
- **Answer Correctness 정체**: Hybrid (0.699) ≈ Rerank (0.698) — 최종 품질은 거의 동등
  - → **이 데이터셋에선 BM25 추가만으로 Rerank 이득을 상당 부분 먹음**
  - → Rerank 는 Precision·Faith 지표엔 선명하지만 "정답률" 관점에선 미미

---

## 난이도별 평균 (AnswerCorrectness)

| 난이도 | N | Basic | Hybrid | **Rerank** | ΔHb→Re |
|---|---|---|---|---|---|
| easy | 4 | 0.52 | 0.85 | **0.75** | -0.10 ⚠️ |
| **medium** | 4 | 0.75 | 0.76 | **0.83** | **+0.07** ↑ |
| hard | 3 | 0.49 | 0.32 | **0.37** | +0.05 |
| cross-year | 4 | 0.75 | 0.78 | **0.76** | -0.02 |

- **medium 에서 Rerank 가 최강 (0.83)**: 문맥 추론이 필요한 문항에 Cohere cross-encoder 의 강점이 드러남
- easy 는 Hybrid 대비 소폭 하락: 일부 문항(q03, q04)에서 Rerank 가 정답 근거를 10위 밖으로 밀어냄
- cross-year 소폭 하락: q15 의 CRec=0.00 충격 (아래 참고)

---

## 문항별 상세 — ΔAnsCor 는 (vs Basic / vs Hybrid)

| qid | diff | year | Rec | Prec | Faith | Rel | Cor | Δ(B→R)/(H→R) |
|---|---|---|---|---|---|---|---|---|
| q01 | easy | 2025 | 1.00 | 0.89 | 1.00 | 0.91 | **0.98** | +0.00 / +0.00 |
| q02 | easy | 2024 | 1.00 | 0.91 | 1.00 | 0.93 | **0.99** | **+0.93** / -0.01 |
| q03 | easy | 2026 | 1.00 | 0.77 | 0.50 | 0.97 | **0.50** | +0.45 / **-0.31** ⚠️ |
| q04 | easy | 2023 | 1.00 | 1.00 | 0.67 | 0.86 | **0.53** | -0.47 / -0.07 ⚠️ |
| q05 | medium | 2024 | 1.00 | 1.00 | 0.89 | 0.89 | **0.54** | -0.42 / -0.09 |
| q06 | medium | 2025 | 1.00 | 1.00 | 1.00 | 0.95 | **0.99** | +0.00 / **+0.27** ↑ |
| q07 | medium | 2025 | 1.00 | 1.00 | 1.00 | 0.81 | **0.99** | -0.01 / -0.01 |
| q08 | medium | 2024 | 1.00 | 1.00 | 0.50 | 0.85 | **0.79** | **+0.74** / +0.12 |
| q09 | hard | 2026 | 1.00 | 0.93 | 0.83 | 0.00 | **0.19** | **-0.80** / +0.15 ⚠️ |
| q10 | hard | 2024 | 1.00 | 1.00 | 1.00 | 0.79 | **0.52** | +0.47 / +0.00 |
| q11 | hard | 2023 | 1.00 | 1.00 | 1.00 | 0.86 | **0.41** | -0.03 / +0.00 |
| q12 | cross-year | 2025+2026 | 1.00 | 1.00 | 0.67 | 0.97 | **0.95** | +0.00 / +0.16 ↑ |
| q13 | cross-year | 2024+2025 | 1.00 | 1.00 | 1.00 | 0.89 | **0.79** | -0.16 / -0.16 |
| q14 | cross-year | 2025+2026 | 1.00 | 0.83 | 1.00 | 0.90 | **0.93** | +0.20 / +0.20 ↑ |
| q15 | cross-year | 2018+2026 | **0.00** 🔴 | 0.79 | 0.50 | 0.00 | **0.37** | -0.00 / -0.26 |

---

## 🎯 주요 성과

### 1. Precision·Faithfulness 최고치 달성
- Context Precision 0.941 (5버전 중 예상 최고)
- Faithfulness 0.837 — Basic 대비 +0.283 개선

### 2. medium 난이도 최강
- q06 Hybrid NaN → Rerank 0.99 (+0.27)
- q08 Hybrid 0.67 → Rerank 0.79 (+0.12)
- q14 (cross-year) Hybrid 0.74 → Rerank 0.93 (+0.20)

### 3. "정보 없음" 4건 대체로 유지 (q10 은 동등, q02·q08 은 개선 유지)

---

## 🔴 Rerank 의 약점

### 1. q09 (hard/2026 추나요법) 여전히 미해결
- Basic 0.98 → Hybrid 0.03 → **Rerank 0.19**
- 소폭 회복됐지만 완전 복구 못함
- Rerank 후보군에 여전히 여러 년도 추나 청크 혼재 → Gemini 가 "2026년" 특정 못함
- → **Pre-filter (metadata 버전)** 가 source_year="2026" 으로 제한해야 해결 가능

### 2. q15 (cross-year 2018+2026) **CRec=0.00 충격**
- Basic/Hybrid 는 Recall=1.0 이었는데 Rerank 에서 **0.00** 으로 급락
- Cohere rerank 가 2018 PDF 의 정답 근거를 top-10 밖으로 **완전히 밀어냄**
- 이유: cross-encoder 관점에서 "2018년 장기지속형 주사제 10%" 와 질문 "2018년과 2026년..." 간 의미 유사도가 2026 청크보다 낮게 평가됨
- 정답은 여전히 0.37 로 유지된 건 Gemini 가 2026 컨텍스트만으로 일부 답 추정한 덕분
- → **Metadata-full (Pre-filter + Rerank)** 가 두 연도 각각 확보 후 Rerank 해야 cross-year 해결

### 3. easy q03, q04 소폭 하락
- q03: Hybrid 0.81 → Rerank 0.50 (-0.31)
- q04: Basic 1.00 → Rerank 0.53 (-0.47)
- Rerank top-10 압축이 해당 문항의 핵심 청크를 밀어낸 것으로 추정

---

## 가설 재검증

### H2 (가장 크게 벌어질 메트릭)
- 원가설: "Context Precision 이 가장 크게 개선"
- 실제 **Basic → Rerank 총 변화**:
  - Faithfulness **+0.283** (최대)
  - Answer Relevancy +0.216
  - Context Precision +0.163
  - Answer Correctness +0.061
  - Context Recall **-0.067**
- → Rerank 에 가서야 Precision 이 주 개선 축이 되지만 **누적 변화로는 Faithfulness 가 여전히 1위**
- → **원가설은 "Hybrid 에선 Faith, Rerank 에선 Precision 으로 개선 축이 이동" 으로 정교화 필요**

### H4 (Faithfulness 가 낮아질 시나리오)
- 원가설 시나리오 ② "BM25 키워드 매칭이 노이즈 청크 소환 → Faith 하락"
- 실제: Rerank 가 오히려 Faith 를 더 올림 (+0.057) → 가설 시나리오 ② 는 Rerank 로 완화됨
- 시나리오 ③ "cross-year 에서 LLM 이 청크 합성" 은 q15 에서 정확히 발생 (Faith=0.50 중간값)

---

## 이어서 관찰할 것

| 관심사 | 확인 방법 |
|---|---|
| q09 (추나요법) Pre-filter 로 해결되나 | Metadata 결과 (년도 필터만) |
| q15 (장기비교) Recall 복구되나 | Metadata-full 결과 (필터 + Rerank) |
| cross-year 에서 Pre-filter 가 Rerank 약점 보완하나 | Metadata-full 의 cross-year 평균 |
| Answer Correctness 평균이 Metadata-full 에서 드디어 튀어오르나 | Metadata-full 결과 |

---

## 기술 메모

- Cohere rate limit (10 req/min 무료) 로 /evaluate 호출이 2분 소요 (정상)
- Ragas 채점은 정상 (NaN 없음, TimeoutError 없음)
- `"LLM returned 1 generations instead of requested 3"` 경고는 여전히 일부 문항에서 발생
- q09 의 faith=0.83 / cor=0.19 는 특이한 조합: 답변은 컨텍스트 기반이지만 **"정보 없음" 류 답변 자체가 grounded 한 것** 으로 평가됨 → Faith 는 실제 품질을 놓치는 경우 있음 (Ragas 한계)
ㅏㅏㅁ