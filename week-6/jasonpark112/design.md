# AI Agent 설계서: 개인 재무 코치 Agent

> 6주차 실습 과제 설계서

---

## 1. 개요·목적

### 해결하려는 문제

현대인은 가계 지출 데이터와 투자 정보가 완전히 분리된 채 관리되어, 내가 얼마를 어디에 쓰고 있는지와 내 자산을 어떻게 불려야 하는지를 연결해서 파악하기 어렵다. 개인 재무 코치 Agent는 실제 소비 내역을 분석하고, 여유 자금을 기반으로 투자 방향(종목·ETF)까지 연결해주는 통합 재무 어시스턴트를 목표로 한다.

### 타깃 사용자

재테크에 관심은 있지만 가계부 분석과 투자 판단을 따로 해야 해서 귀찮아 미루는 20~30대 직장인.

### 왜 Agent여야 하는가

사용자 요청에 따라 실행 경로가 완전히 달라지기 때문이다. 예를 들어 "이번 달 지출 요약해줘"는 지출 조회 Tool 하나로 끝나지만, "내 소비 패턴 보고 투자 추천해줘"는 지출 조회 → 카테고리 분석 → 여유 자금 계산 → 종목 시세 조회 → 뉴스 요약 → 추천 생성 순서로 동적으로 Tool을 조합해야 한다. 또한 "삼성전자 지금 살 만해?"처럼 지출과 무관한 종목 리서치 요청은 시세·뉴스 Tool만 사용하는 전혀 다른 경로를 탄다.

이처럼 요청마다 실행 경로와 호출되는 Tool 조합이 다르기 때문에 고정된 Workflow로는 구현이 불가능하고, 상황에 따라 다음 행동을 스스로 결정하는 Agent 패턴이 필수적이다.

---

## 2. 사용자 시나리오

### Persona

| 항목 | 내용 |
|------|------|
| 이름 | 김지수 |
| 역할 | 27세 IT 회사 개발자 (3년차) |
| 목적 | 월급을 받고 있지만 어디에 쓰는지 파악이 안 되고, 투자도 해보고 싶지만 어디서 시작할지 모름 |

### 대표 요청

**요청 1: 소비 분석**

> "이번 달 내가 어디에 제일 많이 썼어? 카테고리별로 정리해줘"

→ 지출 조회 Tool → 카테고리 분석 Tool 순서로 호출해야 하며, 단순 DB 조회 한 번으로 끝나지 않음

**요청 2: 소비 기반 투자 추천**

> "내 소비 패턴 보고 투자할 수 있는 여유 자금이랑 맞는 ETF 추천해줘"

→ 지출 조회 → 카테고리 분석 → 여유 자금 계산 → 종목 시세 조회 → 뉴스 요약 → 추천 생성까지 6단계 이상 Tool 조합 필요

**요청 3: 특정 종목 리서치**

> "삼성전자 지금 살 만해? 최근 뉴스랑 주가 흐름 같이 분석해줘"

→ 지출 데이터 불필요. 시세 조회 → 뉴스 검색 → 분석 생성으로 전혀 다른 경로를 탐

---

## 3. 기능 요구사항

### Must-have

- 카드·계좌 지출 내역(Mock)을 입력받아 월별·카테고리별 지출 요약을 출력한다
- 지출 내역을 기반으로 고정비·변동비를 구분하고 여유 자금 추정액을 계산하여 반환한다
- 사용자가 지정한 종목 또는 ETF의 현재 시세와 등락률을 조회하여 반환한다
- 종목 관련 최신 뉴스 3~5건을 요약하여 투자 판단 참고 정보로 제공한다
- 위 Tool 결과를 종합하여 사용자 여유 자금과 리스크 성향에 맞는 투자 추천 텍스트를 생성한다

### Nice-to-have

- 전월 대비 지출 증감률을 계산하여 소비 패턴 변화를 알려준다
- Tool 호출 실패 시 재시도 또는 다른 데이터 소스로 fallback 처리한다
- 추천 결과를 JSON 포맷으로도 반환하여 외부 앱 연동을 지원한다

---

## 4. Agent 패턴 선택과 근거

### 선택한 패턴

**ReAct (Reasoning + Acting)**

### 선택 근거

- 사용자 요청의 스텝 수가 매번 다르고(1~6스텝), 다음 Tool을 선택하기 전에 이전 Observation 결과를 보고 판단해야 하므로 매 스텝 Thought → Action → Observation 루프가 적합하다.
- 자기검증(Reflection)이나 역할 분업(Multi-Agent)이 반드시 필요한 복잡도는 아니며, 단일 Agent가 순차적으로 판단하면서 Tool을 호출하는 구조로 충분하다.
- ReAct는 Thought에서 LLM이 현재 상황을 언어로 추론하기 때문에 디버깅과 trajectory 평가가 용이하다.

### 루프 구조

```
1. 사용자 입력 수신
2. Thought: 요청을 분석하고 필요한 Tool과 순서를 추론
3. Action: Tool 호출 (get_transactions / analyze_spending / get_stock_price / get_news_summary / generate_recommendation)
4. Observation: Tool 결과 수신 및 파싱
5. Thought: 결과가 충분한지 판단. 부족하면 3번으로 돌아감
6. 종료 조건 도달 시 최종 응답 생성 → 사용자에게 반환
```

---

## 5. 동작 명세

### 입력 스키마

자연어 문자열 (예: "이번 달 지출 분석해줘"). 선택적으로 아래 구조화 파라미터를 포함 가능.

```json
{
  "user_id": "string",
  "period": "YYYY-MM",
  "risk": "low | mid | high"
}
```

### 출력 스키마

- 기본: 자연어 응답 텍스트
- 투자 추천 요청 시: 자연어 + JSON 블록 함께 반환

```json
{
  "recommendation": "string",
  "picks": [
    { "symbol": "string", "reason": "string", "weight_pct": 30 }
  ]
}
```

### 정상 흐름 예시 (요청 2: 소비 기반 투자 추천)

| 스텝 | 구분 | 내용 |
|------|------|------|
| 1 | Thought | 사용자가 소비 패턴 기반 ETF 추천을 원한다. 먼저 이번 달 지출 내역을 조회해야 한다. |
| 2 | Action | `get_transactions({ user_id: "u001", period: "2026-04" })` 호출 |
| 3 | Observation | 식비 42만원, 교통 8만원, 구독 3만원, 쇼핑 15만원 등 총 지출 97만원 반환 |
| 4 | Thought | 지출 카테고리 분석 및 여유 자금 계산이 필요하다. |
| 5 | Action | `analyze_spending({ transactions: [...] })` 호출 |
| 6 | Observation | 고정비 55만원, 변동비 42만원, 추정 여유 자금 53만원 반환 |
| 7 | Thought | 여유 자금 53만원 기준 ETF를 추천해야 한다. 시세 조회 후 뉴스 확인. |
| 8 | Action | `get_stock_price({ symbol: "TIGER 미국S&P500" })` 호출 |
| 9 | Observation | 현재가 12,450원, 전일 대비 +0.8% 반환 |
| 10 | Action | `get_news_summary({ query: "S&P500 ETF 전망" })` 호출 |
| 11 | Observation | 최근 뉴스 3건 요약: 미 증시 강세, 환율 영향 유의 등 |
| 12 | Thought | 충분한 정보 수집 완료. 최종 추천 생성. |
| 13 | Final | 여유 자금 53만원, TIGER 미국S&P500 추천, 근거 포함 자연어 + JSON 응답 반환 |

### 예외 흐름

- **Tool 실패**: `{ error: "API_UNAVAILABLE", detail: "..." }` 반환 → Thought에서 재시도 또는 다른 종목으로 대체
- **답변 불가**: 필요 데이터 부족 시 사용자에게 추가 정보 요청 메시지 반환
- **권한 부족**: 인증 오류 시 Mock 데이터로 fallback 후 "실제 데이터 연동 필요" 안내

### 종료 조건

- 최종 응답 생성 완료 (stop signal: LLM이 `Final Answer` 태그 출력)
- `max_steps = 15` 초과 시 강제 종료 후 부분 결과 반환
- 동일 Tool을 동일 파라미터로 3회 이상 반복 호출 시 루프 탐지 → 강제 종료

---

## 6. Tool 명세

| Tool 이름 | 목적 | 입력 스키마 | 출력 스키마 | 실패 시 반환 | 사용 조건 |
|----------|------|------------|------------|------------|----------|
| `get_transactions` | 지정 기간의 지출 내역 조회 | `user_id: str`, `period: YYYY-MM` | `[{ date, category, amount, merchant }]` | `{ error: "FETCH_FAILED", detail: str }` | 소비 분석 또는 투자 추천 요청 시 최초 호출 |
| `analyze_spending` | 지출 내역을 카테고리별로 분류하고 여유 자금 계산 | `transactions: list` | `{ fixed, variable, surplus, breakdown }` | `{ error: "PARSE_ERROR", detail: str }` | `get_transactions` 결과가 존재할 때 |
| `get_stock_price` | 종목·ETF 현재 시세 및 등락률 조회 | `symbol: str` | `{ symbol, price, change_pct, updated_at }` | `{ error: "SYMBOL_NOT_FOUND", detail: str }` | 종목 리서치 또는 투자 추천 시 |
| `get_news_summary` | 종목·키워드 관련 최신 뉴스 3~5건 요약 | `query: str`, `limit: int` | `[{ title, summary, source, published_at }]` | `{ error: "NEWS_UNAVAILABLE", detail: str }` | 종목 판단 보조 정보가 필요할 때 |
| `generate_recommendation` | 수집된 데이터를 기반으로 투자 추천 생성 | `surplus: int`, `risk: str`, `market_data: dict` | `{ recommendation: str, picks: [...] }` | `{ error: "INSUFFICIENT_DATA", detail: str }` | 지출 분석과 시세 조회가 모두 완료된 후 |

---

## 7. 데이터셋

### Tool별 데이터 출처

| Tool | 데이터 출처 | 인증 필요 | 업데이트 주기 |
|------|------------|----------|-------------|
| `get_transactions` | 오픈뱅킹 API (금융결제원) — 실습 환경에서는 Mock JSON 사용 | O (OAuth2) → Mock 대체 | 실시간 |
| `analyze_spending` | 내부 계산 로직 (외부 API 없음) | X | 요청 시 |
| `get_stock_price` | 한국투자증권 Open API 또는 Alpha Vantage — Mock 대체 | O (API Key) → Mock 대체 | 실시간 |
| `get_news_summary` | 네이버 뉴스 검색 API — Mock 대체 | O (API Key) → Mock 대체 | 실시간 |
| `generate_recommendation` | 내부 LLM 호출 (외부 API 없음) | X | 요청 시 |

> 모든 Mock 데이터는 실제 오픈뱅킹·증권사 API 스키마와 동일하게 설계하여, 추후 실제 연동 시 데이터 소스만 교체하면 Agent 로직은 그대로 동작한다.

### Mock 데이터 샘플

**get_transactions 응답 샘플**

```json
[
  { "date": "2026-04-03", "category": "식비", "amount": 12500, "merchant": "스타벅스 강남점" },
  { "date": "2026-04-07", "category": "교통", "amount": 1500, "merchant": "서울시 교통공사" },
  { "date": "2026-04-15", "category": "쇼핑", "amount": 67000, "merchant": "쿠팡" }
]
```

**get_stock_price 응답 샘플**

```json
{
  "symbol": "005930",
  "name": "삼성전자",
  "price": 72400,
  "change_pct": -0.55,
  "updated_at": "2026-05-06T09:35:00Z"
}
```

**get_news_summary 응답 샘플**

```json
[
  {
    "title": "삼성전자, 2분기 실적 회복 기대감",
    "summary": "반도체 업황 개선으로 영업이익 반등 전망",
    "source": "한국경제",
    "published_at": "2026-05-05"
  }
]
```

### 데이터 특성 요약

- `get_transactions`: 필드 4개, 월 평균 50~200건, 실제 연동 시 OAuth2 토큰 필요
- `get_stock_price`: 필드 5개, 장중 실시간 갱신, API Key 필요 (일 500회 무료 쿼터)
- `get_news_summary`: 필드 4개, 최신 뉴스 기준, API Key 필요

---

## 8. 성공 판정 기준

| # | 판정 기준 | 판정 방법 |
|---|----------|----------|
| 1 | 소비 분석 요청 시 `get_transactions` → `analyze_spending` 순서로 호출한다 | trajectory에서 Tool 호출 순서 확인 |
| 2 | 투자 추천 요청 시 `get_stock_price`와 `get_news_summary`를 모두 호출한다 | trajectory에서 두 Tool 호출 여부 확인 |
| 3 | Tool 호출 실패 시 재시도 또는 fallback Tool로 전환한다 | 에러 응답 주입 후 다음 Action 확인 |
| 4 | 최종 응답에 여유 자금 금액과 추천 종목명이 포함된다 | 응답 텍스트에서 필드 존재 여부 확인 |
| 5 | 모든 요청이 15 step 이내에 종료된다 | trajectory step 수 카운트 |

---

## 9. 제약·확장

### 현재 설계의 한계

- 단일 Agent 구조이므로 지출 분석과 종목 리서치를 병렬로 처리하지 못하고 순차 실행만 가능 → 응답 지연 발생 가능
- 사용자의 리스크 성향을 한 번만 입력받으며, 대화 중 동적으로 업데이트하는 메모리 구조가 없음
- Mock 데이터 사용으로 인해 실제 금융 환경의 인증·보안·쿼터 이슈를 반영하지 못함

### Multi-Agent 확장 시 역할 분리 후보

- **Orchestrator Agent**: 사용자 의도 파악 → 하위 Agent에 태스크 분배
- **Finance Analyst Agent**: 지출 분석·여유 자금 계산 전담
- **Market Research Agent**: 시세 조회·뉴스 요약·종목 분석 전담

분리 시 Finance Analyst와 Market Research Agent를 병렬 실행할 수 있어 응답 속도가 개선된다.

### 장기 상태·메모리가 필요해지는 시나리오 (7주차 연결)

- 매달 소비 패턴 변화를 추적하여 "지난 3개월 대비 식비가 증가했어요" 같은 장기 인사이트 제공
- 사용자가 관심 종목 리스트를 등록해두면 다음 대화에서도 기억하여 정기 리포트 생성
- 투자 추천 히스토리를 저장하여 "지난번에 추천한 ETF 수익률이 어떻게 됐어?" 질의 지원

---

## 자가 점검 체크리스트

| # | 점검 항목 | 결과 |
|---|----------|------|
| 1 | RAG만으로 풀 수 있는 문제가 아닌가 (경로가 매 요청마다 달라지는가) |  요청 3가지가 각각 다른 Tool 조합과 경로를 사용함 |
| 2 | Tool 설명이 LLM 관점에서 "언제 쓸지"를 결정할 수 있을 만큼 구체적인가 |  입력·출력·사용 조건을 명시함 |
| 3 | 종료 조건과 실패 흐름이 둘 다 명시됐는가 |  max_steps=15, 루프 탐지, fallback 모두 명시 |
| 4 | 데이터셋이 실재하거나 Mock 규격이 스키마 수준으로 뚜렷한가 |  Mock 샘플과 필드 구조 명시, 실제 API 출처 병기 |
| 5 | 제약·확장 섹션에 Multi-Agent로 쪼갤 지점이 최소 한 개 식별됐는가 |  Finance Analyst / Market Research Agent 분리 후보 명시 |
