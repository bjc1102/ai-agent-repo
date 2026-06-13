# 7주차 AI Agent 구현 프로젝트

## 프로젝트 링크

- Repository: https://github.com/1hjjun/AIagentService
- 구현 위치: `week-7/1hjjun/`
- 6주차 설계서: [`design.md`](../design.md)
- 아키텍처 문서: [`architecture.md`](../architecture.md)

## 구현한 Agent

- Agent 이름: AI ETF 리밸런싱 코치
- 해결하려는 문제: 포트폴리오 이미지, ETF 구성 종목, 유튜브 영상 자막, 거시경제 지표, 매매 일지를 함께 사용해 현재 자산 비중과 섹터 쏠림을 분석하고 리밸런싱 의견을 저장한다.
- 타깃 사용자: 미국 주식과 ETF를 함께 보유하고, 매매 판단을 데이터와 일지로 관리하고 싶은 개인 투자자.

## 6주차 설계와의 연결

- 유지한 설계:
  - ReAct 패턴: `decide -> tool call -> observe -> decide -> final`
  - 입력 스키마: `{ "image_url"?: string, "user_query": string }`
  - 출력 스키마: `{ "answer_text": string, "chart_data"?: json, "is_saved": boolean }`
  - 이미지 분석, ETF 구성 조회, 시장 지표 분석, 유튜브 분석, 일지 저장 Tool 구조
  - 종료 조건: 최대 Tool 호출 수, 반복 호출 감지, 연속 실패 제한

- 변경한 설계:
  - FMP API 대신 `yfinance`로 ETF 구성 종목을 조회한다.
  - YouTube Data API 키 대신 `youtube-transcript-api`로 영상 자막을 직접 가져온다.
  - `market_macro`를 단일 VIX 조회에서 글로벌 매크로 분석 Tool로 확장했다.
  - `true_exposure_calculator`, `portfolio_allocation_calculator`를 추가해 LLM이 비중을 직접 계산하지 않도록 했다.
  - DynamoDB 대신 로컬 JSON 파일(`data/journal.json`)에 매매 일지를 저장한다.
  - 반복 실행 비용을 줄이기 위해 이미지 분석과 유튜브 요약은 cache를 사용한다. ETF와 매크로 지표는 최신성이 중요해 캐시하지 않는다.

- 변경 이유:
  - 별도 유료 API 키 없이 실행 가능하게 만들기 위해 FMP/Youtube API 의존성을 제거했다.
  - 투자 비중 계산은 LLM이 아니라 deterministic Tool이 담당해야 수치 환각을 줄일 수 있다.
  - 과제 환경에서 실제 동작과 검증을 쉽게 확인하도록 로컬 JSON 일지와 `result/` 스냅샷을 사용했다.

## 사용한 Tool

| Tool 이름 | 실제/API/mock | 역할 |
|---|---|---|
| `vision_extractor` | OpenAI GPT-4o Vision + cache + optional mock fallback | 포트폴리오 이미지에서 ticker, 수량, 현재가, 평가액 추출 |
| `youtube_sentiment` | `youtube-transcript-api` + OpenAI LLM + cache + optional mock fallback | 영상 전체 자막을 10줄 요약하고 5줄 투자 판단 생성 |
| `market_macro` | `yfinance` + `fear-greed` + OpenAI LLM + heuristic fallback | DXY, 원/달러, 미국채 10Y/2Y, 원자재, VIX, Fear & Greed 기반 ETF 영향 분석 |
| `etf_constituent` | `yfinance` + optional mock fallback | ETF 구성 종목과 편입 비중 조회 |
| `portfolio_allocation_calculator` | local deterministic | 자산별 비중과 S&P500 GICS 기준 섹터별 비중 계산 |
| `true_exposure_calculator` | local deterministic | 직접 보유분과 ETF 간접 보유분을 합산해 특정 종목 실질 노출도 계산 |
| `journal_db` | local JSON | 매매 일지 읽기/쓰기 |

모든 Tool은 공통적으로 아래 형태의 구조화된 결과를 반환한다.

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "source": "api | cache | mock | local",
  "fallback_used": false,
  "fallback_reason": null,
  "original_error": null
}
```

## 실행 패턴

- 선택한 패턴: ReAct
- 이유: 사용자의 요청에 따라 필요한 Tool 조합이 달라진다. 예를 들어 이미지가 있으면 먼저 자산을 추출해야 하고, ETF가 있으면 구성 종목을 확인해야 하며, 리밸런싱과 저장 요청이 있으면 유튜브/매크로 분석 후 일지를 써야 한다.
- 간단한 흐름:

```text
사용자 입력
-> LLM이 필요한 정보 판단
-> Tool 하나 호출
-> Tool 결과 Observation 확인
-> 다음 Tool 또는 최종 답변 판단
-> 필요 시 journal_db(write)
-> 최종 답변
```

현재 통합 예시의 실제 흐름은 다음과 같다.

```text
vision_extractor
-> youtube_sentiment
-> etf_constituent
-> portfolio_allocation_calculator
-> journal_db
```

거시경제 분석 요청이 포함되면 다음 Tool이 추가된다.

```text
market_macro("GLOBAL_MACRO")
```

## 실행 방법

```bash
# 설치
cd week-7/1hjjun
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 환경 변수
cp .env.example .env
# .env 안에 OPENAI_API_KEY=<your_key> 입력
# 선택: ALLOW_MOCK_FALLBACK=true

# 예시 실행
python -m src.main --example 1
python -m src.main --example 2
python -m src.main --example 3

# 커스텀 입력
python -m src.main --input examples/input_1.json

# 반복 호출 종료 조건 확인
python -m src.main --example 1 --force-loop

# 테스트
python -m pytest tests -q
```

필요한 환경 변수:

| 이름 | 필수 여부 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | 필수 | Vision 분석, 유튜브 자막 요약, 매크로 LLM 판단에 사용 |
| `ALLOW_MOCK_FALLBACK` | 선택 | `true`일 때 일부 외부 API 실패를 mock 데이터로 대체 |
| `YOUTUBE_SUMMARY_MODEL` | 선택 | 유튜브 요약 모델 override, 기본값 `gpt-4o-mini` |
| `MARKET_MACRO_MODEL` | 선택 | 매크로 분석 모델 override, 기본값 `gpt-4o-mini` |

별도 API 키가 필요 없는 데이터 소스:

- ETF/가격/거시 지표: `yfinance`
- YouTube 자막: `youtube-transcript-api`
- Fear & Greed: `fear-greed`

## 예시 실행

### 예시 1: 포트폴리오 이미지 + 유튜브 영상 + 섹터 쏠림 분석 + 일지 저장

입력 (`examples/input_1.json`):

```json
{
  "image_url": "examples/real_portfolio_kakaotalk.png",
  "user_query": "이 포트폴리오 사진에서 현재 투자자산과 자산별 비중을 정리해 줘. 그리고 이 유튜브 영상(https://www.youtube.com/watch?v=webDqOfjx8E)의 전체 자막을 요약한 뒤, S&P500 GICS 섹터 기준으로 내 포트폴리오가 어느 섹터에 너무 몰려 있는지 판단하고 리밸런싱 의견을 줘. 투자 섹터 분류는 네가 종목과 ETF 구성을 보고 판단해 줘. 마지막에 오늘 매매 일지에 현재 자산 비중, 유튜브 요약, 섹터 쏠림 판단, 리밸런싱 의견을 저장해 줘."
}
```

실행 결과 파일:

```text
result/20260508T051053Z/001_vision_extractor.json
result/20260508T051053Z/002_youtube_sentiment.json
result/20260508T051053Z/003_etf_constituent.json
result/20260508T051053Z/004_portfolio_allocation_calculator.json
result/20260508T051053Z/005_journal_db.json
```

출력 요약:

```text
- 이미지에서 QQQM, GOOGL, 6965, GEV, RKLB, TSLA, ETN, HOOD 등 보유 자산을 추출했다.
- 유튜브 영상 전체 자막을 10줄로 요약하고, 투자자가 참고할 판단을 5줄로 생성했다.
- ETF(QQQM)는 yfinance로 구성 종목을 조회했다.
- LLM이 종목별 섹터를 분류하고 portfolio_allocation_calculator가 자산별/섹터별 비중을 계산했다.
- 분석 결과와 리밸런싱 의견을 journal_db로 저장했다.
```

### 예시 2: 글로벌 매크로 분석

입력 개념:

```text
현재 글로벌 매크로 상황을 보고 SPY, QQQ, XLK, XLE, XLF, GLD, TLT에 어떤 영향이 있는지 분석해 줘.
```

실행 결과 파일:

```text
result/manual_market_macro_final_check/001_market_macro.json
```

출력 요약:

```text
- source: api+fear_greed+llm
- fallback_used: false
- 미국채 10Y: 4.392
- 미국채 2Y: 3.8
- 10Y-2Y 금리차: 0.592
- Fear & Greed: 67.6 / greed
- Fear & Greed 세부 지표: market_momentum_sp500, stock_price_strength, stock_price_breadth,
  put_call_options, market_volatility_vix, safe_haven_demand, junk_bond_demand
- LLM이 금리, 달러, 원자재, 심리 지표의 상관관계와 ETF별 영향을 판단했다.
```

### 예시 3: 과거 매매 일지 복기

입력 (`examples/input_3.json`):

```json
{
  "user_query": "지난달 FOMC 때 내가 왜 QQQ를 팔았었는지 일지 검색해 보고 지금 주가랑 비교해 줘"
}
```

출력 요약:

```text
- journal_db(read)로 FOMC 관련 과거 매매 기록을 검색한다.
- market_macro("QQQ")로 현재 QQQ 가격과 추세를 확인한다.
- 과거 판단 이유와 현재 시장 상황을 비교해 복기 답변을 생성한다.
```

## 실행 로그 분석

`result/` 폴더에는 각 Tool 호출마다 입력과 결과가 JSON으로 저장된다.

예시 1의 예상 흐름:

```text
vision_extractor -> youtube_sentiment -> etf_constituent -> portfolio_allocation_calculator -> journal_db(write)
```

예시 1의 실제 저장 결과:

```text
001_vision_extractor.json
002_youtube_sentiment.json
003_etf_constituent.json
004_portfolio_allocation_calculator.json
005_journal_db.json
```

분석:

- 설계에서 예상한 것처럼 이미지 분석 결과를 Observation으로 받은 뒤 ETF 구성과 섹터 비중 계산이 이어졌다.
- 같은 이미지/영상 재실행 시 `vision_extractor`, `youtube_sentiment`는 cache source를 사용해 불필요한 API 호출을 줄인다.
- ETF 구성 종목과 매크로 지표는 최신성이 중요해 캐시하지 않는다.
- `market_macro`는 `fear-greed` 라이브러리와 OpenAI LLM까지 실제 호출했으며, mock 없이 `fallback_used=false`로 성공했다.
- Tool 결과는 `ok`, `source`, `fallback_used`, `original_error`를 포함해 실패/대체 여부를 눈으로 확인할 수 있다.

## 성공 판정 기준 확인

6주차 성공 판정 기준 5개와 추가 검증 2개를 테스트와 실제 실행 결과로 확인했다.

| 기준 | 결과 | 근거 |
|---|---|---|
| 이미지 입력 후 자산 추출 Tool을 먼저 호출하는가 | 통과 | `vision_extractor` 결과가 `result/.../001_vision_extractor.json`으로 저장됨 |
| ETF 구성 정보를 사용해 개별 종목/ETF 노출을 계산하는가 | 통과 | `etf_constituent`, `true_exposure_calculator` 테스트 통과 |
| 최종 응답에 차트/비중 데이터가 포함되는가 | 통과 | `portfolio_allocation_calculator`가 `chart_data`와 allocation 결과 생성 |
| "저장해 줘" 요청 시 일지 write가 호출되는가 | 통과 | `result/20260508T051053Z/005_journal_db.json` |
| 7회 이내 종료 조건과 반복 호출 방지가 있는가 | 통과 | `GuardrailState.MAX_TOOL_CALLS=7`, repeated tool call 테스트 통과 |
| Tool 실패 처리가 구조화되어 있는가 | 통과 | `ok=false`, `fallback_used`, `original_error` 단위 테스트 통과 |
| mock이 아닌 실제 API 실행이 가능한가 | 통과 | `market_macro` 실제 실행 결과 `source=api+fear_greed+llm`, `fallback_used=false` |

테스트 결과:

```text
88 passed in 0.75s
```

## 구현하며 배운 점

- 프롬프트가 너무 친절하면 LLM이 실제 데이터를 보지 않고 맞춘 척할 수 있다. 그래서 각 Tool의 input/output을 `result/`에 저장해 실제로 무엇을 봤는지 확인하게 만들었다.
- 이미지 분석과 유튜브 요약은 비용이 커서 cache가 유용했다. 반면 ETF 구성과 매크로 지표는 최신성이 중요해 cache 대상에서 제외했다.
- LLM은 비중 계산을 자주 틀릴 수 있으므로 `true_exposure_calculator`, `portfolio_allocation_calculator`처럼 계산 전용 Tool을 분리하는 편이 안전했다.
- 거시경제 분석은 숫자 나열만으로는 부족했다. `market_macro("GLOBAL_MACRO")`가 지표 수집 후 LLM 판단을 만들도록 확장하니 리밸런싱 의견의 근거가 더 분명해졌다.

## 자가 점검 체크리스트

1. [x] 개인 repository 링크가 있는가
2. [x] 6주차 설계 `design.md` 링크가 있는가
3. [x] Tool 2개 이상이 구현됐는가
4. [x] Tool 실패 처리가 있는가
5. [x] 종료 조건이 있는가
6. [x] 예시 입력 2개 이상이 있는가
7. [x] 성공 판정 기준 3개 이상을 확인했는가
8. [x] API key나 `.env`가 commit되지 않았는가
