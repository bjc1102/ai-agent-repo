# 5주차 실습 — RAG 시스템 정량 평가 (Ragas)

##. 이론 답변

→ **별도 파일**: [`THEORY.md`](./THEORY.md)
- Section 1: Golden Dataset
- Section 2: 평가의 필요성과 LLM-as-a-Judge
- Section 3: Ragas 4대 메트릭 (+ Answer Correctness)

---

## 1. 환경 정보

| 항목 | 값 |
|---|---|
| 생성용 LLM | `gemini-3-flash-preview` (4 변형 공통, temperature 기본) |
| 평가용 LLM | `gpt-4o-mini` (생성용과 다른 패밀리로 셀프 편향 회피) |
| 평가용 임베딩 | `text-embedding-3-small` (Ragas Answer Correctness · Response Relevancy 의 코사인 유사도용) |
| 벡터 저장소 | ChromaDB |
| 청킹 | RecursiveCharacterTextSplitter, `chunk_size=1000` / `chunk_overlap=200` |
| Ragas 버전 | 0.4.x (`adapt_prompts(language="korean")` + `set_prompts` 적용) |
| Rerank | Cohere `rerank-multilingual-v3.0` (Rerank · Metadata-Full 변형) |
| BM25 토크나이저 | Kiwi 한국어 형태소 (Hybrid 이상 변형) |
| 골든셋 | 15문항 (`data/golden_dataset_v2.jsonl`) |
| 실행 환경 | macOS (darwin 23.0.0), Python 3.x, FastAPI 기반 4 변형 서비스 |

### 4 변형 정의 — Advanced 진화 단계

| 변형 | 검색 파이프라인 | 추가 기법 |
|---|---|---|
| **Basic** | Dense (Chroma) Top-k | — |
| **Hybrid** | Dense Top-20 + BM25 Top-20 → **RRF (k=60)** | + BM25 키워드 매칭 |
| **Rerank** | Dense 20 + BM25 20 union → **Cohere Rerank** → Top-10 | + Cross-encoder 재정렬 |
| **Metadata-Full** | Year Pre-filter → (Dense + BM25) → Cohere Rerank → Top-10 | + 년도 메타데이터 사전 필터 |

---

## 2. 폴더 구조

```
week-5/DChanhong/
├── THEORY.md            ← 이론 정리
├── README.md            ← 이 파일 (실습 결과)
├── data/
│   └── golden_dataset_v2.jsonl    (15문항)
├── pdf/                 (2016~2026 의료급여제도 PDF 11개)
├── chroma_db/           (공용 벡터 저장소, 미커밋 — 32MB)
├── indexing.py          (PDF → 청킹 → Chroma 인덱싱)
├── evaluate_ragas.py    (5메트릭 평가 스크립트)
└── assignment/
    ├── basic/           data/basic/0/{MEMO.md, evaluation_results.jsonl, ragas_scores.csv}
    ├── hybrid/          data/hybrid/0/...
    ├── rerank/          data/rerank/0/...
    └── metadata-full/   data/metadata-full/0/...
```

---

## 3. Golden Dataset (v2) 확장 전략

### 3-1. 필드 구성

| 필드 | 의미 | 비고 |
|---|---|---|
| `id` | q01~q15 | 정렬 안정성 |
| `question` | 사용자 질문 | Ragas `user_input` 으로 매핑 |
| `ground_truth` | 모범 답변 (완전한 문장) | Ragas `reference` 로 매핑 |
| `ground_truth_contexts` | 정답 근거 청크 (리스트) | Ragas `reference_contexts` 로 매핑 |
| `difficulty` | `easy` / `medium` / `hard` / `cross-year` | 난이도별 분석용 |
| `source_year` | `2024` / `2025+2026` 등 | 년도 혼동 진단용 |

### 3-2. `ground_truth` 정제 원칙 — "년도 + 대상 + 조건 + 값" 한 문장

```
example: "2024년 의료급여 1종 수급권자의 CT·MRI·PET 검사 본인부담률은 5%입니다."
```

### 3-3. `ground_truth_contexts` 발췌 원칙

- **PDF 원본에서 의미 단위 (2~5문장)** 로 직접 발췌. 벡터 저장소 청크 경계와 일치할 필요 없음.
- 표·Q&A 형 본문은 **표 헤더와 값을 한 문단으로 평문화** 해서 작성 (q01, q02 등).
- **수동 어노테이션 원칙 준수** (LLM 자동 생성 금지) — Context Recall 신뢰도의 기준점이기 때문.

### 3-4. cross-year 처리

- `source_year="2025+2026"` 형식으로 표기, `ground_truth_contexts` 는 두 년도 청크를 모두 포함.
- 4 문항 (q12, q13, q14, q15) 으로 cross-year 비중 확보 — Pre-filter / Rerank 의 다년도 처리 능력 분리 진단.

### 3-5. 난이도 분포 (총 15문항)

| 난이도 | 개수 | 특징 |
|---|---|---|
| easy | 4 | 단년도 단일 항목 (q01~q04) |
| medium | 4 | 단년도 다항목·예외조항 (q05~q08) |
| hard | 3 | 표 추론·년도 모호 (q09~q11) |
| cross-year | 4 | 두 년도 비교 (q12~q15) |

---

## 4. Ragas 평가 파이프라인

### 4-1. 데이터 흐름

```
-> Step1
golden_dataset_v2.jsonl (각 문항 question 을 RAG 4 변형에 invoke)
-> Step2
RAG 변형별 출력 → SingleTurnSample(user_input, retrieved_contexts, response, reference, reference_contexts)
-> Step3
EvaluationDataset → ragas.evaluate(metrics=[5개], llm=evaluator_llm, embeddings=evaluator_emb)
-> Step4
ragas_scores.csv (변형별)  +  MEMO.md (변형별 분석)
```

### 4-2. 5 메트릭 선택 이유

| 메트릭 | 클래스 | 이유 |
|---|---|---|
| Context Recall | `ContextRecall()` | reference 기준 검색 재현율 — Pre-filter / Rerank 가 정답 청크를 떨어뜨리는지 직접 포착 |
| Context Precision | `LLMContextPrecisionWithReference()` | v0.2+ 표준, reference 가 있으므로 LLM 판정 기반 정밀도 사용 |
| Faithfulness | `Faithfulness()` | 환각·이탈 진단 (reference 불필요, claim 단위 LLM 판정) |
| Answer Relevancy | `ResponseRelevancy()` | 구 `answer_relevancy` — 답변→역질문 코사인 유사도 |
| Answer Correctness | `AnswerCorrectness()` | End-to-end 정확도 (사실 F1 + 의미 유사도 가중 평균) |

> 소문자 함수형(`faithfulness`, `answer_relevancy`)은 deprecation 대상이라 클래스형 사용.

### 4-3. 평가용 LLM 선택 이유

- **생성용** (gemini-3-flash-preview) ↔ **평가용** (gpt-4o-mini) **모델 패밀리 분리** — 자기 고양 편향(self-preference) 회피.
- gpt-4o-mini 는 비용/품질 균형이 좋고 한국어 판정 안정적. (단, "LLM returned 1 generations instead of 3" 경고가 Answer Relevancy 에서 자주 발생 → 노이즈 일부 존재)
- Ragas 내장 프롬프트는 영어이므로 `adapt_prompts(language="korean", llm=evaluator_llm)` → `set_prompts(**adapted)` 로 한국어 전환.

### 4-4. 비용·시간

- 15문항 × 5메트릭 × 4변형 = **300회 LLM 판정**
- 변형당 평가 시간 약 **4~5분** (Cohere Rerank 변형은 무료 rate limit 으로 추가 2분)

---

## 5. Step 2 결과 — 5 메트릭 측정

### 5-1. 전체 평균 (4 변형 진화 단계)

| 메트릭 | Basic<br>(Dense) | + BM25<br>= **Hybrid** | + Rerank<br>= **Rerank** | + Pre-filter<br>= **Metadata-Full** | 총 Δ(B→MF) |
|---|---|---|---|---|---|
| **Context Recall** | 1.000 | 1.000 | 0.933 ↓ | 0.933 | -0.067 |
| **Context Precision** | 0.778 | 0.879 ↑ | **0.941** ↑ | 0.922 ↓ | **+0.144** |
| **Faithfulness** | 0.554 | 0.780 ↑↑ | **0.837** ↑ | 0.714 ↓↓ | +0.160 |
| **Answer Relevancy** | 0.556 | 0.755 ↑↑ | **0.772** ↑ | 0.681 ↓ | +0.125 |
| **Answer Correctness** | 0.637 | **0.699** ↑ | 0.698 | 0.696 | +0.059 |

**요약**:
- **Hybrid 의 BM25 기여가 가장 크다** — Faith +0.225, Rel +0.200 단일 점프
- **Rerank 가 Precision·Faith 정점** — Precision 0.941 / Faith 0.837
- **Pre-filter 는 단조 개선이 아니다** — Faith·Rel 후퇴가 발생 (후보풀 축소 부작용)
- **Cor 평균은 Hybrid 이후 거의 동률** (0.699 / 0.698 / 0.696) — 비용 대비 추가 기법의 한계 효율 체감

### 5-2. 난이도별 평균 (Answer Correctness)

| 난이도 | N | Basic | Hybrid | Rerank | Metadata-Full |
|---|---|---|---|---|---|
| easy | 4 | 0.52 | **0.85** ↑ | 0.75 | 0.82 |
| medium | 4 | 0.75 | 0.76 | **0.83** ↑ | 0.75 |
| hard | 3 | 0.49 | 0.32 ↓ | 0.37 | 0.38 |
| cross-year | 4 | 0.75 | 0.78 | 0.76 | 0.75 |

- **easy**: BM25 가 "정보 없음" 폴백 4건을 회복 (q02/q03/q08/q10) → Basic 0.52 → Hybrid 0.85 급등
- **medium**: Rerank 의 cross-encoder 가 가장 강함
- **hard**: 모든 Advanced 가 Basic 보다 낮음 — q09 추나요법 케이스가 평균을 끌어내림 (Case A 참고)
- **cross-year**: 거의 동률 — BM25/Rerank 만으론 다년도 통합 답변 향상 못함

### 5-3. 문항별 상세 (Answer Correctness 중심)

| qid | diff | year | Basic | Hybrid | Rerank | MF | 비고 |
|---|---|---|---|---|---|---|---|
| q01 | easy | 2025 | 0.98 | 0.97 | 0.98 | 0.97 | 4 변형 모두 정답 |
| q02 | easy | 2024 | 0.06 | 1.00 🎯 | 0.99 | 0.98 | "정보 없음" → 회복 |
| q03 | easy | 2026 | 0.05 | 0.81 🎯 | 0.50 ⚠️ | 0.73 | Pre-filter 가 Rerank 후퇴 보완 |
| q04 | easy | 2023 | 1.00 | 0.60 ⚠️ | 0.53 | 0.60 | Advanced 모두 후퇴 |
| q05 | medium | 2024 | 0.95 | 0.63 | 0.54 | 0.35 ⚠️ | 단조 악화 (열거형 답변 압축 실패) |
| q06 | medium | 2025 | 0.99 | 0.72 | 0.99 | 0.98 | Hybrid 만 일시 후퇴 |
| q07 | medium | 2025 | 0.99 | 0.99 | 0.99 | 0.99 | 4 변형 모두 정답 |
| q08 | medium | 2024 | 0.06 | 0.67 🎯 | 0.79 | 0.69 | "정보 없음" → 회복 |
| q09 | hard | 2026 | **0.98** | 0.03 🔴 | 0.19 | 0.15 | **Case A — Advanced 가 Basic 파괴** |
| q10 | hard | 2024 | 0.05 | 0.52 🎯 | 0.52 | 0.47 | "정보 없음" → 회복 |
| q11 | hard | 2023 | 0.44 | 0.41 | 0.41 | 0.51 | MF 가 소폭 개선 |
| q12 | cross | 2025+26 | 0.95 | 0.79 | 0.95 | 0.95 | Hybrid 만 일시 후퇴 |
| q13 | cross | 2024+25 | 0.96 | 0.96 | 0.79 | 0.57 ⚠️ | MF 에서 큰 폭 악화 |
| q14 | cross | 2025+26 | 0.74 | 0.74 | 0.93 | 0.85 | Rerank 가 정점 |
| q15 | cross | 2018+26 | 0.37 | 0.63 | 0.37 | 0.64 | **Case B — Recall=0 인데 Cor 회복** |

> 🎯 = "정보 없음" → 실답 회복 / ⚠️ = Advanced 가 Basic 보다 후퇴 / 🔴 = 단일 메트릭 0 점에 가까운 충격

---

## 6. Step 3 — Advanced 진화 단계 비교 + 인사이트

### 6-1. 다차원 비교 — 어느 기법이 어느 메트릭을 움직였나

| 변형 (추가 기법) | 가장 크게 개선한 차원 | 부작용 발생 차원 |
|---|---|---|
| **Hybrid** (BM25 추가) | Faithfulness +0.225, Relevancy +0.200 — "정보 없음" 4건 회복으로 0→1 점프 | q09 년도 혼동 발생 (Cor 0.98→0.03) |
| **Rerank** (Cohere Cross-encoder) | Precision +0.062 → 0.941 정점, Faith +0.057 → 0.837 정점 | Recall -0.067 (q15 의 2018 청크 top-10 밖 탈락) |
| **Metadata-Full** (Year Pre-filter) | q03 회복 (+0.23 vs Rerank), q09 의 Faith 차원 회복 (0→0.67) | Faith -0.123, Rel -0.091 — 후보풀 축소로 보조 청크 소실 |

### 6-2. 년도 혼동 재진단

**가장 민감한 메트릭은 Faithfulness (단, 부분적으로만)**

- **q09 (2026 추나요법)** Basic Cor 0.98 → Hybrid Cor 0.03 / Faith 0.00
  - Hybrid 가 BM25 키워드 매칭으로 2020·2021·2022·...·2026 추나 표를 모두 끌어와 Gemini 가 "2026" 특정 못함 → "정보 없음"
  - **Faith 가 0 으로 떨어진 것이 년도 혼동의 직접 시그널**
- **q15 (2018+2026 cross-year)** Rerank Cor 0.37 / Recall **0.00**
  - Cohere cross-encoder 가 2018 청크를 top-10 밖으로 밀어냄 → Recall 0
  - **Recall 이 cross-year 누락의 직접 시그널**

→ **Ragas 기본 메트릭만으론 "년도 혼동" 을 단일 메트릭으로 포착 못함.** Faith·Recall·Cor 가 각각 다른 패턴을 보여서 종합 판단 필요.
→ **YearAccuracy 커스텀 메트릭 필요성 증명** (심화 A 후보).

### 6-3. 인사이트

**(1) "Advanced 가 더 좋다" 는 메트릭 차원에 따라 다르다**
-> 4주차에서 결과만을 가지고 채점을 했을 때는 Advanced 가 압도적으로 우위에 있었습니다.
하지만, Regas 5가지 메트릭으로 진단해보면 추가적으로 참고할만한 지표가 있었습니다.
- 성능 지표 차이 : 'Faithfulness(충실성)'와 'Precision(정밀도)은 개선버전으로 갈수록 좋아졌지만, 답변 정확도는 하이브리드 방식부터 정체되었습니다.
( 0.699 → 0.698 → 0.696 )
- 결론 : BM25 추가로도 충분히 전체 성능을 확보할 수 있는것이였으며 , Rerank 나 Pre-filter 기법이 정밀 지표를 높이기는 했으나, 시제 정확도에는 영향을 덜 줬습니다.
- 현재 테스트한 단계에서는 하이브리 방식이 최적의 기법이였습니다.


**(2) 도메인 임계값(예: Faithfulness ≥ 0.9)으로 보면 프로덕션 불가**
-> Faith 의 값이 Rerank에서 0.837 이였으므로, 프로덕션 레벨까지는 도달하지 못했습니다.
- 연도별 데이터의 정확성 매칭을 확인해야하며, 표 데이터 형식의 정보 추출의 세밀한 확인이 필요합니다.

**(3) 개선 우선순위 메트릭과 근거는?**
-> 개선 우선순위 메트릭은 Faithfulness(현재 정점 0.837, 프로덕션 임계값 0.9 미달)
개선 근거
- 수치적 한계: 4가지 변형 모델 중 Faithfulness만 도메인 목표치인 0.9를 넘지 못했습니다.
- 분산과 문제: q09(Faith 0.00), q15(Faith 0.50)와 같이 특정 난이도가 높은 문항이나 연도별 비교 문항이 전체 평균을 끌어내리고 있습니다.
- 근본 원인 : Faithfulness 저하의 주원인은 검색 기법의 문제가 아닌 Ingestion(PDF 파싱)의 한계입니다.

---

## 7. Step 4 — 실패 케이스 Deep Dive

### Case A: q09 — Advanced 가 Basic 을 파괴 (필수)

**질문**: 2026년 의료급여 1종 수급권자가 디스크·협착증 외 질환으로 단순추나 또는 특수추나 치료를 받을 때 본인부담률은 몇 퍼센트인가요?
**참고 정답**: 80%

| 변형 | Cor | Faith | Rel | 응답 요약 |
|---|---|---|---|---|
| Basic | **0.98** | 0.00 | 0.88 | "80%" (정답) |
| Hybrid | 0.03 🔴 | 0.00 | 0.00 | "정보 없음" |
| Rerank | 0.19 | 0.83 | 0.00 | 부분 답 |
| Metadata-Full | 0.15 | 0.67 | 0.00 | "복잡추나만 표에 명시 → 단순/특수추나는 정보 없음" |

**원인 분석**:
- **검색 단계** — Hybrid 의 BM25 가 "추나요법" 키워드로 2020·2021·...·2026 모든 년도의 동일 표를 상위로 끌어옴
- **생성 단계** — Gemini 가 다년도 청크 혼재 속에서 "2026" 특정 못해 보수적 폴백
- **Pre-filter (MF)** — 2026 만 남기는 데 성공 (Faith 0.67) 이지만 표 평탄화 문제로 "단순추나 행" 인식 실패
- **가장 잘 드러낸 메트릭** — Basic 의 Faith=0.00 / Cor=0.98 의 역설이 Ragas 한계 시그널 (표 기반 답변 과소평가). Advanced 에서 Cor 가 0 으로 떨어진 것이 진짜 실패 시그널

**조치 우선순위**:
1. (단기) Pre-filter 적용 → 년도 혼동만은 해소 ✓ (이미 적용)
2. (중기) PDF 표 파서 개선 — 행/열 구조 보존
3. (장기) YearAccuracy + TableAccuracy 커스텀 메트릭으로 자동 진단

### Case B: q15 — cross-year 한쪽 년도 누락 (필수)

**질문**: 2018년과 2026년 의료급여 정신질환 환자가 외래에서 처방받는 장기지속형 주사제의 본인부담률은 각각 얼마인가요?
**참고 정답**: 2018년 10%, 2026년 2%

| 변형 | Recall | Prec | Faith | Cor | 응답 요약 |
|---|---|---|---|---|---|
| Basic | 1.00 | 0.57 | 0.71 | 0.37 | 합성 답변, Rel=0 |
| Hybrid | 1.00 | 0.67 | 0.67 | 0.63 | 부분 답 |
| Rerank | **0.00** 🔴 | 0.79 | 0.50 | 0.37 | 2018 청크 top-10 밖 탈락 |
| Metadata-Full | 0.00 | 0.95 | 0.75 | **0.64** | 2018 "정보 없음", 2026 정확 |

**원인 분석**:
- **Rerank 단점** — Cohere cross-encoder 가 "2018년 장기지속형 10%" 청크와 질문 임베딩 거리를 2026 청크보다 낮게 매겨 top-10 밖으로 밀어냄
- **MF 의 Pre-filter 도 부족** — 후보엔 2018 을 포함시켰지만 Rerank 가 다시 떨어뜨림 → "두 년도 균등 보장 메커니즘" 부재
- **가장 잘 드러낸 메트릭** — Context Recall = 0.00 이 직접 시그널. 그럼에도 Cor 가 0.64 인 건 2026 답이 정확해서 부분 점수 받음

**조치 우선순위**:
1. cross-year 후처리 — 년도별 top-K/2 분할 보장 로직
2. Rerank candidates 확대 (20 → 40) 후 영향 측정

### Case C: q09 — Faith 와 Answer Correctness 충돌 (선택)

같은 q09 케이스에서 **Basic 의 Faith=0.00 / Cor=0.98 역설** 이 의미 있는 충돌:
- 답변 "80%" 가 표 형태 컨텍스트 ("단순추나·특수추나 → 디스크 외 → 1종 80%") 에서 추출한 정확한 값
- Ragas Faithfulness 가 표 기반 추론을 직접 인용으로 인식 못해 0 점 부여
- **Ragas 기본 메트릭이 표 답변을 과소평가** 하는 한계 → 도메인 특화 메트릭 필요

### 공통 교훈 (5개 bullet)
1. 어떤 질문 유형에서 메트릭이 실제 품질과 어긋났나
- **"정보 없음" 응답은 Faith=1.00 으로 평가됨** — Ragas 가 "근거에 기반한 응답" 으로 잘못 분류. 실제 사용자 가치는 0 인데 메트릭은 만점. → AnswerCorrectness 와 함께 봐야 진짜 품질 확인
- **표 기반 답변은 Faith 가 과소평가** — 직접 인용 매칭이 안 되면 0 점 (q09 Basic). LLM 응답이 표 형태 컨텍스트에서 값 추출한 경우 Ragas 기본 메트릭 한계
- **Hard 난이도 문제에서 극단적 점수 변동** — q09 에서 Basic 의 Cor=0.98 → HybridCor=0.03 처럼 작은 검색 변화에 전체 품질이 붕괴되는 현상

2. Ragas가 놓치는 품질 사각지대 (Failure Types)
- 이번에는 pdf 인덱싱 문제도 존재했기 때문에 검색 결과에 대한 신뢰도가 다소 떨어졌던 점도 파악할 수 있었습니다.
- Ragas는 검색 지표가 정상이어도 실제 답변이 틀리는 '품질 사각지대'는 진단할 수 없습니다. 
   - Ragas 지표를 보기전에 , 기본 검색 품질 및 인덱싱 등을 먼저 짚고 넘어가야 합니다.
- 메트릭 자체의 한계로,  표 추론을 인용으로 인식하지 못하거나, 답변을 포기해도 Faithfulness 점수가 높게 나타나기도 합니다.


3. 4주차 수동 채점 vs 5주차 Ragas 자동 평가 엄격성 비교
: Regas는 상황에 따라 더 엄격하거나, 더 관대해지거나 일관된 성향을 보이지는 않습니다. 그래서, 매트릭별로 엄격성이 뒤집히는 현상이 보여서 종합적으로 살피고 대조해보는 과정이 중요합니다.

| 비교 축 | 4주차 수동 채점 | 5주차 Ragas 평가 | 엄격성 비교 |
| :--- | :--- | :--- | :--- |
| **표 추론 정답** (q09 "80%") | 답이 맞으면 인정 | Faith=0 부여 | **Ragas가 더 엄격** (정답을 0점 처리) |
| **"정보 없음" 응답** | 실패로 채점 (0점) | Faith≈1.00 (만점) | **Ragas가 훨씬 관대** |
| **부분 정답** (cross-year 등) | 보통 0.5 부여 | Cor가 의미·사실 가중 평균으로 0.4~0.7 | **유사** |
| **메트릭 간 일관성** | 단일 점수로 균질함 | Faith·Cor가 ±1.0까지 차이 발생 | **수동이 더 일관됨** |


---

## 8. 가설 vs 실제 결과

| # | 가설 (실습 전) | 실제 결과 | 일치 여부 |
|---|---|---|---|
| H1 | 수동 vs Ragas 는 구조적으로 완전 일치 불가 | 4주차 수동 점수와의 직접 비교는 미수행이나, 단일 응답 안에서도 q09 Basic 처럼 **Faith=0.00 / Cor=0.98** 같은 ±1.0 진폭이 발생 → 완전 일치는 구조적으로 불가능함을 간접 확인 | △ 부분 |
| H2 | Advanced 개선의 본질은 Precision | **불일치** — Hybrid 단계에서 가장 크게 점프한 메트릭은 Precision 이 아니라 **Faithfulness (+0.225)** 와 Relevancy (+0.200). Precision 정점은 Rerank (0.941) 에서 도달하지만 단일 점프 폭은 Faith 가 더 큼 |  불일치 |
| H3 | Faithfulness 는 정답 여부를 반영하지 않음 | **양방향 입증** — (a) 정답인데 Faith=0: q09 Basic 응답 "80%" 가 정답인데 Faith=0.00 (표 기반 추론을 직접 인용으로 인식 못함). (b) 오답인데 Faith≈1: "정보 없음" 응답 4건 (q02/q03/q08/q10 의 Basic) 이 Faith≈1.00 — 빈 답변을 "근거에 충실" 로 잘못 분류 |  일치 |
| H4 | 검색이 좋아질수록 Faithfulness 는 오히려 떨어질 수 있음 | **일치** — Metadata-Full 에서 Rerank 대비 Faith -0.123, q09 의 Hybrid 에서 Faith 0.00 발생. Pre-filter 가 후보풀을 줄여 보조 청크가 소실되거나, BM25 가 다년도 동일 키워드를 끌어와 LLM 이 폴백하는 패턴 |  일치 |
---





