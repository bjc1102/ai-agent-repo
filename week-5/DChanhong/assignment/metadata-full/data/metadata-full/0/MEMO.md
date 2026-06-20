# Metadata-Full RAG — Ragas 평가 결과 메모

- **파이프라인**: **Year Pre-filter** (질문 → 년도 추출 → Chroma `where`/BM25 부분코퍼스) + Dense (ChromaDB) + BM25 (Kiwi 형태소) + **Cohere Rerank (`rerank-multilingual-v3.0`)**
- **검색 파라미터**: candidates=20 (Dense 20 + BM25 20 union) → Rerank → top_k=10
- **생성 모델**: gemini-3-flash-preview (5버전 공통)
- **평가용 LLM**: GPT-4o-mini
- **평가용 임베딩**: text-embedding-3-small
- **Golden Dataset**: 15문항 (week-5/data/golden_dataset_v2.jsonl)
- **결과 CSV**: `ragas_scores.csv`

---

## 전체 평균 (15문항) — vs Basic / Hybrid / Rerank

| 메트릭 | Basic | Hybrid | Rerank | **Metadata-Full** | ΔRe→MF | 총 Δ(B→MF) |
|---|---|---|---|---|---|---|
| **Context Recall** | 1.000 | 1.000 | 0.933 | **0.933** | ±0.000 | -0.067 |
| **Context Precision (w/ ref)** | 0.778 | 0.879 | 0.941 | **0.922** | -0.019 | **+0.144** |
| **Faithfulness** | 0.554 | 0.780 | 0.837 | **0.714** | **-0.123** ⚠️ | +0.160 |
| **Answer Relevancy** | 0.556 | 0.755 | 0.772 | **0.681** | **-0.091** ⚠️ | +0.125 |
| **Answer Correctness** | 0.637 | 0.699 | 0.698 | **0.696** | -0.002 ≈ | +0.059 |

### 해석
- **Pre-filter 효과는 "정확한 년도 시그널" 1개 차원으로만 작용** — Rerank 대비 Cor 는 동등하지만 Faith·Rel 이 떨어짐
- **Faith -0.123 / Rel -0.091** 의 원인:
  - Pre-filter 가 candidates 풀을 좁혀 후보가 적어지고, 그 안에서 Rerank top-10 이 재선택되면서 **표·각주 등 보조 청크가 떨어져 나감** → Gemini 가 "표에 명시 안 됨" 판단을 더 자주 함 (q09, q13 등)
  - Faithfulness 가 부분 점수(0.5/0.67/0.75)로 깎이는 케이스가 5건 발생
- **Context Recall 그대로 0.933**: q15 의 2018 청크가 여전히 top-10 밖 (Rerank 와 동일한 한계 — Pre-filter 가 후보엔 넣었으나 Rerank 가 다시 밀어냄)
- **결론**: Pre-filter + Rerank 조합으로도 **Answer Correctness 평균은 Hybrid/Rerank 와 거의 동률** — "5버전 비교 표" 의 가장 중요한 의외성

---

## 난이도별 평균 (AnswerCorrectness)

| 난이도 | N | Basic | Hybrid | Rerank | **Metadata-Full** | ΔRe→MF |
|---|---|---|---|---|---|---|
| easy | 4 | 0.52 | 0.85 | 0.75 | **0.82** | **+0.07** ↑ |
| medium | 4 | 0.75 | 0.76 | **0.83** | **0.75** | **-0.08** ⚠️ |
| hard | 3 | 0.49 | 0.32 | 0.37 | **0.38** | +0.01 |
| cross-year | 4 | 0.75 | 0.78 | 0.76 | **0.75** | -0.01 |

- **easy 회복** (Hybrid 0.85 ≒ MdFull 0.82): Pre-filter 가 단년도 질문(q02/q03)에 노이즈 청크를 사전 차단
- **medium 하락 (-0.08)**: q05 (0.63→0.35) 가 평균을 끌어내림 — Pre-filter 가 후보를 좁힌 뒤 Rerank 가 핵심 청크를 잘못 재정렬
- **hard 미해결**: q09 가 0.03→0.15→0.15 로 정체 — Pre-filter 만으론 부족, 표 파싱 문제 잔존
- **cross-year 정체**: q15 (Rec=0) 충격이 그대로

---

## 문항별 상세 — ΔAnsCor 는 (vs Basic / vs Rerank)

| qid | diff | year | Rec | Prec | Faith | Rel | Cor | Δ(B→MF)/(Re→MF) |
|---|---|---|---|---|---|---|---|---|
| q01 | easy | 2025 | 1.00 | 1.00 | 1.00 | 0.91 | **0.97** | -0.01 / -0.01 |
| q02 | easy | 2024 | 1.00 | 0.85 | 0.00 | 0.90 | **0.98** | **+0.92** 🎯 / -0.01 |
| q03 | easy | 2026 | 1.00 | 1.00 | 1.00 | 0.98 | **0.73** | **+0.68** / **+0.23** ↑ |
| q04 | easy | 2023 | 1.00 | 0.92 | 1.00 | 0.71 | **0.60** | -0.40 ⚠️ / +0.07 |
| q05 | medium | 2024 | 1.00 | 1.00 | 0.63 | 0.86 | **0.35** | **-0.60** ⚠️ / **-0.19** ⚠️ |
| q06 | medium | 2025 | 1.00 | 0.85 | 1.00 | 0.88 | **0.98** | -0.01 / -0.01 |
| q07 | medium | 2025 | 1.00 | 0.62 | 0.00 | 0.81 | **0.99** | +0.00 / +0.00 |
| q08 | medium | 2024 | 1.00 | 0.97 | 1.00 | 0.85 | **0.69** | **+0.63** 🎯 / -0.10 |
| q09 | hard | 2026 | 1.00 | 1.00 | 0.67 | 0.00 | **0.15** | **-0.83** 🔴 / -0.04 |
| q10 | hard | 2024 | 1.00 | 0.90 | 0.50 | 0.69 | **0.47** | +0.42 / -0.05 |
| q11 | hard | 2023 | 1.00 | 1.00 | 0.75 | 0.84 | **0.51** | +0.07 / +0.10 |
| q12 | cross-year | 2025+2026 | 1.00 | 0.89 | 0.67 | 0.85 | **0.95** | +0.00 / +0.00 |
| q13 | cross-year | 2024+2025 | 1.00 | 1.00 | 0.75 | 0.00 | **0.57** | **-0.39** ⚠️ / **-0.22** ⚠️ |
| q14 | cross-year | 2025+2026 | 1.00 | 0.85 | 1.00 | 0.94 | **0.85** | +0.11 / -0.08 |
| q15 | cross-year | 2018+2026 | **0.00** 🔴 | 0.95 | 0.75 | 0.00 | **0.64** | +0.27 / +0.27 ↑ |

---

## 🎯 주요 성과

### 1. easy "정보 없음" 4건 모두 회복 유지 (Hybrid 수준 보존)
- q02 (2024 CT/MRI/PET): Cor 0.98 — Hybrid 와 동등
- q03 (2026 자연분만): Cor 0.73 — Rerank(0.50) 대비 **+0.23 회복** ✅
- q08 (2024 6세 미만): Cor 0.69 — Hybrid 와 동등
- q10 (2024 건강검진): Cor 0.47 — Hybrid 와 동등

→ Pre-filter 가 단년도 질문에서 **검색 노이즈를 줄여 Rerank 가 Hybrid 수준으로 정답 청크 유지**

### 2. q03 회복 — Pre-filter 의 진가
- Basic 0.05 → Hybrid 0.81 → Rerank **0.50** (퇴보) → **Metadata-Full 0.73**
- Rerank 단독은 자연분만 관련 다년도 청크가 cross-encoder 점수에서 2026 청크를 밀어냄
- Pre-filter 로 source_year="2026" 만 남기자 Rerank 가 진짜 2026 청크들 사이에서 정렬 → 정답 복귀

### 3. q15 정답률 소폭 회복 (+0.27 vs Basic, +0.27 vs Rerank)
- Recall=0 에도 불구하고 **Cor 0.64** 달성 (역대 최고)
- Pre-filter 가 2018 PDF 청크를 후보엔 포함시킴 → Rerank 가 밀어내도 일부 잔존 → Gemini 가 2026 답은 정확히 추출
- 하지만 2018 답은 여전히 "정보 없음" (응답 인용: *"2018년: 정보를 찾을 수 없습니다"*)
- → **Pre-filter + Rerank 의 조합이 cross-year 의 "한쪽 년도 누락" 을 완전히는 못 잡음**

---

## 🔴 약점·역설

### 1. q09 (hard/2026 추나요법) — Pre-filter 로도 미해결
| 버전 | answer_correctness | 응답 요약 |
|---|---|---|
| Basic | **0.98** | "80%" (정답) |
| Hybrid | 0.03 | "정보 없음" |
| Rerank | 0.19 | 부분 답 |
| **Metadata-Full** | **0.15** | **"단순추나/특수추나에 대한 디스크 협착증 외 본인부담률 정보는 표에 기재되어 있지 않습니다 → 정보 없음"** |

**원인**:
- Pre-filter 로 source_year="2026" 을 잘 잡았기에 **년도 혼동은 해소** (Faith 0.67 로 상승)
- 하지만 Gemini 가 표 해석에서 *복잡추나 행만 명시* 라고 판단 → 단순/특수추나 행 (실제로는 80% 동일) 을 인식 못함
- → **PDF 파싱 단계에서 표 행/열 구조가 평탄화되며 발생한 문제** (검색·rerank 가 아닌 ingestion 문제)

**시사점**: 표 파싱 품질 개선 (markdown 표 보존, 행/열 헤더 명시) 이 다음 개선 축

### 2. q05 (medium/2024) **-0.60 vs Basic** 큰 폭 하락
- Basic 0.95 → Hybrid 0.63 → Rerank 0.54 → **MdFull 0.35**
- 모든 Advanced 버전에서 점진적 악화
- Pre-filter 로 2024 만 남겼는데도 Rerank 가 핵심 청크 (예외 항목 나열) 를 밀어냄
- → "직접 신청 가능한 예외 사례" 같은 **나열형 답변** 은 cross-encoder 가 단일 핵심 청크로 압축 못함

### 3. q13 (cross-year/2024+2025) **-0.39 vs Basic, -0.22 vs Rerank**
- Basic/Hybrid 모두 0.96 → MdFull **0.57**
- 응답: *"2025년: 관련 정보를 찾을 수 없습니다"*
- Pre-filter 가 2024+2025 두 년도를 모두 잡았음에도 **2025 노숙인진료시설 고시** 청크가 Rerank 후 top-10 에 안 남음
- Rel=0 → Ragas 가 2025 답변 누락을 정확히 포착

### 4. Faithfulness·Relevancy 가 Rerank 대비 **떨어짐** (-0.123 / -0.091)
- Pre-filter 로 후보풀 자체가 작아져 Rerank top-10 이 보조 청크 부족 → Gemini 응답이 "기재 안 됨" 류로 빠지면서 Faith 부분 감점
- 동시에 답이 "정보 없음" 류면 Rel=0 으로 직격 (q09, q13, q15)

---

## 가설 재검증

### H2 (가장 크게 벌어질 메트릭) — **재정교화 필요**
- Basic → Metadata-Full 누적 변화:
  - Faithfulness +0.160
  - Context Precision +0.144
  - Answer Relevancy +0.125
  - Answer Correctness +0.059
  - Context Recall **-0.067**
- Rerank 시점이 정점 (Faith +0.283), MdFull 에선 오히려 일부 후퇴
- → **개선 효과 곡선이 단조 증가가 아니라 "Rerank 에서 피크 → MdFull 에서 일부 감소"**

### H3 (년도 혼동) — **Pre-filter 가 부분 해결**
- q09: 년도 혼동(Hybrid Faith=0)은 해소(MdFull Faith=0.67) — Pre-filter 효과 증명
- 하지만 표 파싱 문제로 **최종 정답률(Cor)은 회복 못함**
- → 가설 "Pre-filter 가 hard 년도 혼동을 잡는다" 는 **검색 신호 차원에선 ✓, 최종 답변 차원에선 △**

### H4 (Rerank top-10 이 누락하는 케이스) — q13 추가
- 기존 q15 (cross-year 한쪽 누락) 외에 **q13 도 동일 패턴**
- → cross-year 에서 Rerank 가 **두 년도 모두를 균등 보장하는 메커니즘이 없음**
- → "년도별 top-K/2 분할" 같은 후처리 검토 필요

---

## 5버전 비교 — 한 줄 결론

| 버전 | 강점 | 약점 |
|---|---|---|
| Basic | 단순·기본선 | "정보 없음" 4건, hard 약함 |
| Hybrid | 키워드 매칭으로 "정보 없음" 회복 | q09 년도 혼동 발생 |
| Rerank | Faith·Prec 최고치 | q15 Recall 폭락, easy q03/q04 후퇴 |
| **Metadata-Full** | **q03 회복, q09 년도 혼동 해소(Faith 차원)** | **Faith·Rel 후퇴, q05/q13 악화** |
| Metadata (필터만) | (예정) | (예정) |

---

## 이어서 관찰할 것

| 관심사 | 확인 방법 |
|---|---|
| Pre-filter **단독** 효과 (Rerank 없이) | Metadata 버전 평가 후 비교 |
| q09 표 파싱 개선 시 정답 회복 여부 | PDF 파서 재작성 + 재인덱싱 |
| cross-year 에서 년도별 top-K 균등 분할이 q13/q15 해결하는지 | 후처리 로직 추가 실험 |
| Faith/Rel 후퇴의 진짜 원인 (후보풀 축소? Rerank 압축?) | candidates=40 으로 확장 후 재평가 |

---

## 기술 메모

- Pre-filter 동작: 질문 → year_extractor → Chroma `where={"source_year": {"$in": years}}` + BM25 in-memory 부분코퍼스 재구성
- Cohere Rerank 사용 (rerank-multilingual-v3.0), rate limit 영향 동일
- q15 의 Recall=0 에도 Cor=0.64 가 나오는 건 **2018 답 누락에도 2026 답이 정확** 했기 때문 (Ragas Cor 는 reference 와의 부분 일치 점수)
- "LLM returned 1 generations instead of requested 3" 경고 다수 — Answer Relevancy 노이즈 동일하게 존재
- q09 의 응답이 표 구조 해석에서 막힌 점 → **검색·rerank 를 아무리 개선해도 ingestion 단계 한계가 ceiling 으로 작용**
