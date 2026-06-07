# 8주차 AI Agent Observability

## 프로젝트 링크

- Repository: https://github.com/jasonpark112/finance-coach-agent
- 7주차 제출 README: [README1.md](./README1.md)

## 구현한 Observability

- 사용한 방식: JSON log (직접 구현)
- trace 저장 위치: `logs/{run_id}_trace.json`
- 기록하는 항목:

| 영역 | 항목 | trace 필드 |
|------|------|-----------|
| Request | user input / session id / timestamp | `user_message`, `run_id`, `started_at` |
| Prompt | prompt version (SYSTEM_PROMPT MD5 앞 8자리) | `prompt.version` |
| Model | provider / model name | `model.provider`, `model.name` |
| Latency | 전체 / tool별 | `total_latency_ms`, `steps[].tool_calls[].latency_ms` |
| Tool | 이름 / 인자 / 결과 / 에러 | `tool`, `input`, `result`, `error` |
| Agent Step | step 번호 / action / observation | `steps[].step`, `steps[].tool_calls` |
| Output | 최종 답변 / 종료 이유 | `final_answer`, `stop_reason` |
| Token / Cost | 입력·출력 token 수, 추정 비용 | `usage.input_tokens`, `usage.output_tokens`, `usage.estimated_cost_usd` |
| Safety | 마스킹 필드 / 제외 필드 | `safety.masked_fields`, `safety.excluded_fields` |

---

## Agent 실행 흐름

- Agent 이름: 개인 재무 코치 Agent
- 주요 Tool: `get_transactions`, `analyze_spending`, `get_stock_price`, `get_news_summary`, `generate_recommendation`
- 종료 조건: `end_turn` (정상) / `max_tokens` / `loop_detected` (동일 Tool 3회 반복) / `max_steps` (15 step 초과)

---

## 정상 케이스 Trace

> 전체 파일: [examples/trace_normal.json](./examples/trace_normal.json)

입력:

```text
삼성전자 지금 살 만해 최근 뉴스랑 주가 흐름 같이 분석해줘
```

실행 요약:

| Step | Type | Name | 주요 입력 | 결과 |
|------|------|------|-----------|------|
| 1 | tool_call | `get_stock_price` | `symbol: "005930"` | `ok: true` / 현재가 72,400원, 등락률 -0.55% |
| 1 | tool_call | `get_news_summary` | `query: "삼성전자"` | `ok: true` / 뉴스 3건 반환 |

> Step 1에서 두 Tool이 병렬 호출됨 (Claude가 자율적으로 병렬 처리 선택)

최종 답변:

```text
현재가: 72,400원 | 등락률: -0.55%

긍정 신호: HBM3E·AI 수혜 기대, 외국인 5거래일 연속 순매수, 2분기 실적 반등 전망
주의 신호: 당일 소폭 하락, 73,200원 고가 돌파 여부가 단기 분기점

→ 72,000~72,400원 구간 분할 매수 관점에서 긍정적
```

---

## 실패 또는 예외 케이스 Trace

> 전체 파일: [examples/trace_failure.json](./examples/trace_failure.json)

입력:

```text
KODEX 국내채권 주가 알려줘
```

실행 요약:

| Step | Type | Name | 주요 입력 | 결과 |
|------|------|------|-----------|------|
| 1 | tool_call | `get_stock_price` | `symbol: "KODEX 국내채권"` | `ok: false` / `SYMBOL_NOT_FOUND` |

실패 처리:

- `get_stock_price` 가 `ok: false`, 에러 코드 `SYMBOL_NOT_FOUND` 반환
- `fallback_occurred: true` 로 기록
- Claude가 에러 내용을 읽고 지원 종목 목록을 안내하는 답변 생성
- Agent는 `end_turn` 으로 정상 종료 (프로그램 중단 없음)

---

## Trace 분석

- 예상한 흐름: `get_stock_price` → `get_news_summary` 순차 호출 → 답변
- 실제 흐름: `get_stock_price` + `get_news_summary` **동시 병렬 호출** → 답변 (1 step으로 단축)
- 잘 동작한 부분:
  - Claude가 독립적인 Tool을 자율적으로 병렬 처리해 응답 속도 개선
  - Tool 실패(`ok: false`) 시 프로그램이 중단되지 않고 에러를 읽어 자연스러운 안내 답변 생성
  - 모든 종료 경로(`end_turn` / `max_tokens` / `loop_detected` / `max_steps`)에서 trace 저장 보장
- 문제 또는 개선할 부분:
  - mock 함수가 즉시 반환하므로 `latency_ms: 0` — 실제 API 연동 후에야 step latency가 의미 있는 값이 됨
  - `prompt.version` 이 SYSTEM_PROMPT 내용 변경 시 자동 갱신되지만, 버전 히스토리를 별도 관리하지는 않음

---

## Metrics

> `python src/analyze_traces.py` 로 `logs/` 전체 trace를 집계한 결과 (4건 기준)

### 전체 집계

| 항목 | 값 | 설명 |
|------|----|------|
| 총 실행 건수 | 4건 | |
| 종료 이유 | end_turn 4건 | 모든 실행 정상 종료 |
| 평균 step 수 | 2.8 | 최소 2 / 최대 4 |
| 평균 latency | 35,393 ms | 최소 9,331 / 최대 65,584 ms |
| 전체 tool 호출 | 11건 | |
| tool 실패 수 | 1건 (9.1%) | `get_stock_price` SYMBOL_NOT_FOUND |
| 누적 token 수 | 63,209 | input 52,907 / output 10,302 |
| 누적 비용 | $0.313251 | |
| 건당 평균 token | 15,802 | |
| 건당 평균 비용 | $0.078313 | |

### Tool별 성공/실패

| Tool | 호출 수 | 실패 수 | 실패율 |
|------|---------|---------|--------|
| `get_transactions` | 2건 | 0건 | 0% |
| `analyze_spending` | 2건 | 0건 | 0% |
| `get_stock_price` | 4건 | 1건 | 25% |
| `get_news_summary` | 2건 | 0건 | 0% |
| `generate_recommendation` | 1건 | 0건 | 0% |

### 케이스별 비교

| 케이스 | latency | step 수 | token | 비용 | tool 에러 |
|--------|---------|---------|-------|------|-----------|
| 소비 분석 (정상) | 47,421 ms | 3 | 19,838 | $0.105510 | 0건 |
| ETF 투자 추천 (정상) | 65,584 ms | 4 | 32,764 | $0.157020 | 0건 |
| 삼성전자 분석 (정상) | 19,235 ms | 2 | 5,943 | $0.031533 | 0건 |
| KODEX 국내채권 (실패) | 9,331 ms | 2 | 4,664 | $0.019188 | 1건 |

---

## 민감정보 처리

- 저장하지 않은 정보: 계좌 잔액(`resAfterTranBalance`, `resAccountBalance`), 출금 금액(`resWithdrawalAmt`)
- masking한 정보: `user_id` (`u001` → `u***`), 거래 내역 배열(`resTrHistoryList` → `[30 items omitted]`), `analyze_spending` 입력의 `transactions` 배열(`[30 items omitted]`)
- trace 공유 시 주의할 점: `_run.txt` 는 마스킹이 적용되지 않은 raw 출력이므로 외부 공유 시 `_trace.json` 만 사용할 것

---

## 고도화 평가

| 평가 항목 | 구현 여부 | 결과 |
|-----------|-----------|------|
| correctness | 미구현 | — |
| groundedness | 미구현 | — |
| tool completeness | 구현 | `tool_sequence` 로 요청 유형별 필요 Tool 호출 여부 확인 가능. 소비 분석 시 `get_transactions` -> `analyze_spending` 순서 보장, 투자 추천 시 5개 Tool 모두 호출 확인 |
| token / cost 집계 | 구현 | `usage.input_tokens`, `usage.output_tokens`, `usage.estimated_cost_usd` 를 trace에 기록. `analyze_traces.py` 로 전체 누적 집계 가능 |
| tool 실패율 집계 | 구현 | `analyze_traces.py` 로 tool별 호출 수·실패 수·실패율 자동 집계 |

---

## 배운 점

- **구조화 로그의 가치**: `_run.txt` 는 즉각적인 디버깅에 유용하지만, `_trace.json` 처럼 JSON으로 저장해야 나중에 코드로 집계·분석하거나 모니터링 툴에 연동할 수 있다. `analyze_traces.py` 한 줄로 전체 실행 이력을 집계할 수 있는 것이 그 결과다.
- **마스킹은 저장 직전에 적용**: 원본 데이터는 그대로 Claude에게 전달하고, trace 기록 시점에만 마스킹 함수를 거치도록 분리하면 Agent 동작에 영향 없이 안전하게 처리할 수 있다.
- **Tool 반환 스키마 일관성**: `{ ok, data, error }` 구조를 통일하면 Claude가 실패 여부를 명확히 파악하고 다음 행동을 판단하기 쉬워진다. 실패 케이스에서 Claude가 에러 메시지를 읽고 자동으로 안내 답변을 생성한 것이 이를 증명한다.
- **종료 경로 통합 처리**: 종료 경로가 4개일 때 각각 trace 저장 로직을 넣으면 중복·누락이 생긴다. `_finish()` 내부 함수로 묶어 어떤 경로로 끝나든 항상 저장되도록 보장하는 것이 효과적이다.
