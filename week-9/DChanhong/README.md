# 8주차 AI Agent Observability

## 프로젝트 링크

- Repository: https://github.com/DChanHong/baseball-agent
  - Agent 본체 코드(`AgentExecutor` 설정, Tool 정의, prompt 등)와 observability 관련 모듈이 모두 이 외부 repo에 있습니다.
  - 본 README는 aiagent-repo 안의 제출용 요약본이고, 실제 실행 코드와 trace 샘플 JSON은 위 repository에서 확인합니다.
- 7주차 제출 README: https://github.com/DChanHong/baseball-agent/blob/main/README.md
  - 7주차 Agent 구성(Tool 목록, 실행 흐름, 설치 방법)이 그대로 유지돼 있어 본 README의 "Agent 실행 흐름" 섹션과 함께 보면 충분합니다.

## 구현한 Observability

- 사용한 방식: LangSmith managed tracing + `/chat` 응답 metadata 요약
- trace 저장 위치: LangSmith project `kbo-game-day-agent`
- trace 단위: `/chat` 요청 1건을 trace 1건으로 기록
- trace id: 서버에서 `kbo_{uuid}` 형식으로 생성하고 LangSmith metadata와 `/chat` 응답 metadata에 함께 저장
- prompt version: `kbo-game-day-agent-v1`
- LangSmith run name: `kbo_game_day_agent`
- LangSmith tags: `kbo-agent`, `week8-observability`, `prompt:kbo-game-day-agent-v1`

기록하는 항목:

| 영역 | 항목 |
|------|------|
| Request | 사용자 입력, session id, trace id, 시작/종료 시각 |
| Prompt | prompt version, LangChain prompt 실행 흐름 |
| Model | Gemini chat model, OpenAI embedding model |
| Tool | tool name, arguments, result, error, result_summary |
| Agent Step | step number, observation, step latency |
| Output | final answer, stop reason |
| Latency | 전체 elapsed_ms, tool별 latency_ms |

## Agent 실행 흐름

- Agent 이름: KBO 직관 가이드 Agent
- 실행 방식: LangChain `AgentExecutor` 기반 tool-calling agent
- 종료 조건: 최종 답변 생성, 최대 반복 횟수 8회, 최대 실행 시간 30초
- 주요 Tool:

| Tool | 역할 |
|------|------|
| `find_kbo_game` | 2026 KBO 일정 JSON에서 날짜, 팀, 구장 조건에 맞는 경기 조회 |
| `get_stadium_info` | 구장 위치, 돔 여부, 홈팀, 날씨 좌표 조회 |
| `get_weather_context` | Open-Meteo 또는 fallback 규칙으로 날씨 context 생성 |
| `search_baseball_knowledge` | FAISS RAG 기반 좌석, 예매, 동선 근거 문서 검색 |
| `score_seat_candidates` | 좌석 후보를 선호도, 날씨, 예산, 응원 기준으로 점수화 |
| `get_ticketing_guide` | 홈팀/구장 기준 예매처와 예매 팁 조회 |
| `get_logistics_guide` | 출발지/구장/경기 시간 기준 원정 동선 조회 |

## 정상 케이스 Trace 1: 일정 조회

LangSmith trace (public): https://smith.langchain.com/public/d2bffe6d-b4b7-4305-8c38-7d0911513571/r

> 위 링크는 별도 로그인 없이 열람 가능한 public share link입니다. 링크를 열면 좌측에 step tree(LLM call → `find_kbo_game` tool call → 최종 답변), 우측에 각 step의 input/output/latency가 표시됩니다. 아래 표는 그 trace를 요약한 것이므로 링크 접근이 어려운 경우 README만으로도 동일 정보를 확인할 수 있습니다.

입력:

```text
다음주 롯데 경기 알려줘
```

실행 요약:

| Step | Type | Name | 주요 입력 | 결과 |
|------|------|------|-----------|------|
| 1 | tool_call | `find_kbo_game` | `team_query=롯데`, `date_query=다음주` | `status=ambiguous_game`, 후보 6경기 |

Trace 정보:

| 항목 | 값 |
|------|----|
| session id | `local-observability-normal-schedule` |
| trace id | `kbo_14a9f81fe6684825b3dfb9cdf9d0dae6` |
| tool 호출 순서 | `find_kbo_game` |
| 전체 latency | 4624ms |
| stop reason | `final_answer` |

최종 답변 요약:

```text
다음주 롯데 후보 경기 6개를 제시하고, 어떤 경기를 더 자세히 볼지 추가 선택을 요청했습니다.
```

분석:

- 경기 일정은 RAG가 아니라 `find_kbo_game`의 deterministic lookup으로 처리됐습니다.
- 후보 경기 수가 6개로 반환됐습니다.
- 구장, 날씨, RAG, 좌석 점수화 Tool은 호출되지 않았습니다.

## 정상 케이스 Trace 2: 좌석 추천

LangSmith trace (public): https://smith.langchain.com/public/abc17a63-9c35-4f63-9f4b-0fca47a54342/r

> 5단계 tool 호출이 직렬로 이어지는 trace이므로, 링크에서는 step tree가 깊게 펼쳐집니다. 각 tool node를 클릭하면 argument와 observation 전문을 볼 수 있고, 우측 상단에서 전체 latency 23564ms와 token 사용량을 확인할 수 있습니다. 아래 표는 같은 정보를 한눈에 정리한 요약본입니다.

입력:

```text
2026년 5월 23일 롯데 경기 좌석 추천해줘. 가성비 좋고 응원하기 좋은 자리로 알려줘
```

실행 요약:

| Step | Type | Name | 주요 입력 | 결과 |
|------|------|------|-----------|------|
| 1 | tool_call | `find_kbo_game` | `team_query=롯데`, `date=2026년 5월 23일` | `status=found`, 2026-05-23 사직 경기 확정 |
| 2 | tool_call | `get_stadium_info` | `stadium_id=sajik` | 사직야구장, 비돔 구장 |
| 3 | tool_call | `get_weather_context` | `game_date=2026-05-23`, `game_time=17:00`, `stadium_id=sajik` | `status=weather_based`, `risk_flags=[]` |
| 4 | tool_call | `search_baseball_knowledge` | `purpose=seat_recommendation`, 사직 가성비/응원 좌석 query | 좌석 후보 문서 4개 반환 |
| 5 | tool_call | `score_seat_candidates` | 선호도, 날씨 context, 좌석 후보, 경기 정보 | 좌석 추천 3개 반환, 1순위 `1루내야상단석` |

Trace 정보:

| 항목 | 값 |
|------|----|
| session id | `local-observability-normal-seat` |
| trace id | `kbo_7e76285988b8438ba8a72a82c15fbf09` |
| tool 호출 순서 | `find_kbo_game` -> `get_stadium_info` -> `get_weather_context` -> `search_baseball_knowledge` -> `score_seat_candidates` |
| tool latency | 19ms -> 0ms -> 2123ms -> 999ms -> 0ms |
| 전체 latency | 23564ms |
| stop reason | `final_answer` |



최종 답변 요약:

```text
2026-05-23 사직 롯데-삼성 경기 기준으로 맑은 날씨와 비돔 구장 조건을 설명하고,
가성비와 롯데 응원 선호를 반영해 1루내야상단석을 우선 추천했습니다.
좌석 가격은 크롤링 시점 기준이며 실시간 잔여석을 반영하지 않는다는 한계를 함께 안내했습니다.
```

분석:

- 단일턴 입력에서 경기 확정, 구장 조회, 날씨 조회, RAG 검색, 좌석 점수화가 모두 실행됐습니다.
- 좌석 추천 답변은 `score_seat_candidates` observation 이후에 생성됐습니다.
- tool latency 기준 병목은 `get_weather_context` 2123ms였고, 전체 latency에는 LLM reasoning 시간이 크게 포함됐습니다.

## 실패 또는 예외 케이스 Trace

입력:

```text
2026년 2월 1일 롯데 좌석 추천해줘
```

LangSmith trace (public): https://smith.langchain.com/public/a02885f9-982f-410d-a7db-e7818dc1f042/r

> 링크를 열면 `find_kbo_game` tool node의 output에 `ok=false`, `status=not_found`, `error.code=GAME_NOT_FOUND`가 그대로 노출돼 있습니다. 후속 tool node가 존재하지 않고 곧바로 최종 답변 node로 이어지므로, Agent가 실패를 감지한 뒤 추가 호출 없이 종료했음을 trace tree에서 시각적으로 확인할 수 있습니다.

실행 요약:

| Step | Type | Name | 주요 입력 | 결과 |
|------|------|------|-----------|------|
| 1 | tool_call | `find_kbo_game` | `team_query=롯데`, `date_query=2026년 2월 1일` | `ok=false`, `status=not_found`, `error.code=GAME_NOT_FOUND` |

Trace 정보:

| 항목 | 값 |
|------|----|
| session id | `local-observability-failure-game-not-found` |
| trace id | `kbo_a14f471470094ad79b513a81a23bf337` |
| tool 호출 순서 | `find_kbo_game` |
| 전체 latency | 3729ms |
| stop reason | `final_answer` |

실패 처리:

- 경기 확정에 실패한 뒤 `get_stadium_info`, `get_weather_context`, `search_baseball_knowledge`, `score_seat_candidates`를 호출하지 않았습니다.
- Agent 실행 자체는 실패하지 않고 정상 종료됐습니다.
- 최종 답변은 해당 날짜에 롯데 경기를 찾을 수 없으니 다른 날짜나 조건을 입력해 달라는 fallback 성격으로 생성됐습니다.

## Trace 분석

- 예상한 흐름: 일정 조회는 `find_kbo_game`만 호출하고, 좌석 추천은 경기 확정 후 구장 정보, 날씨, RAG 검색, 좌석 점수화 순서로 진행해야 합니다.
- 실제 흐름: 일정 조회, 좌석 추천, 실패 케이스 모두 예상 흐름과 일치했습니다.
- 누락된 Tool: 세 trace 모두에서 예상 흐름 대비 누락된 Tool은 없었습니다. 일정 조회와 실패 케이스는 단일 Tool만 필요한 흐름이라 후속 Tool 미호출이 정상 동작이고, 좌석 추천은 구장→날씨→RAG→점수화 5개 Tool이 모두 호출됐습니다.
- Tool argument 구체성: `find_kbo_game`은 `team_query=롯데`, `date_query=다음주`처럼 사용자 발화의 모호한 표현도 그대로 인자로 전달돼 Tool 내부에서 날짜 범위로 정규화됐습니다. 좌석 추천 trace에서는 `score_seat_candidates`가 선호도, 날씨 context, 좌석 후보, 경기 정보를 모두 받아 점수화에 필요한 인자가 빠짐없이 전달됐습니다. 인자 부족으로 인한 재호출이나 빈 인자 호출은 관측되지 않았습니다.
- 반복 호출 여부: 세 trace 모두에서 동일 Tool을 동일 인자로 다시 호출하는 불필요한 반복은 없었습니다. 좌석 추천 trace의 5단계도 각 Tool이 정확히 1회씩만 호출됐습니다.
- Fallback 동작: 실패 케이스에서 `find_kbo_game`이 `status=not_found`, `error.code=GAME_NOT_FOUND`를 반환하자 Agent는 후속 Tool을 호출하지 않고 사용자에게 다른 날짜를 요청하는 답변으로 정상 종료(`stop reason=final_answer`)했습니다.
- Latency 병목: 좌석 추천 trace의 tool latency 합계는 약 3141ms인데 전체 latency는 23564ms로, 차이의 대부분이 LLM reasoning 시간입니다. Tool 단위로는 `get_weather_context` 2123ms와 `search_baseball_knowledge` 999ms가 컸습니다.
- 답변 groundedness: 세 trace 모두 최종 답변이 직전 Tool observation 범위 내 정보로만 구성됐습니다. 좌석 추천 답변의 경기/구장/날씨/좌석 1순위는 각각 `find_kbo_game`, `get_stadium_info`, `get_weather_context`, `score_seat_candidates` observation에서 그대로 가져왔고, 가격이 크롤링 시점 기준이라는 한계 안내도 RAG 문서 근거 범위 안에 있습니다. Tool 결과를 벗어난 hallucination은 관측되지 않았습니다.
- 개선할 부분: 좌석 추천 trace의 전체 latency 23564ms 중 tool latency 합계보다 LLM reasoning 시간이 더 크므로, prompt 축약이나 deterministic pre-routing으로 지연을 줄일 수 있습니다.

## Metrics

| 항목 | 정상 일정 조회 | 정상 좌석 추천 | 실패 케이스 |
|------|----------------|----------------|-------------|
| total latency | 4624ms | 23564ms | 3729ms |
| step count | 1 | 5 | 1 |
| tool error count | 0 | 0 | 1 structured not_found |
| stop reason | `final_answer` | `final_answer` | `final_answer` |

## 실제 관측 로그 샘플

LangSmith trace와 별도로, 리뷰어가 repository 안에서 바로 확인할 수 있도록 실제 `/chat` 실행 결과를 JSON 샘플로 저장했습니다.

> 아래 경로들은 모두 외부 repository(`https://github.com/DChanHong/baseball-agent`) 기준입니다. 본 aiagent-repo에는 포함돼 있지 않으므로, 파일을 직접 열어보려면 외부 repo의 `docs/observability/examples/` 디렉터리로 이동해야 합니다. 다만 각 파일의 핵심 내용은 본 README의 trace 표에 이미 요약돼 있어, 외부 파일을 열지 않아도 평가에 필요한 정보는 확인할 수 있습니다.

| 항목 | 파일 | 포함 내용 요약 |
|------|------|----------------|
| 인덱싱 상태 | `docs/observability/examples/index_status.json` | FAISS index 준비 상태, document count(239), 카테고리별 문서 수, embedding 모델 이름 |
| 정상 일정 조회 run | `docs/observability/examples/normal_schedule_run.json` | Trace 1의 session id, trace id, 입력, 최종 답변, 전체 latency, stop reason 등 run 단위 요약 |
| 정상 일정 조회 Tool 호출 | `docs/observability/examples/normal_schedule_tool_calls.json` | Trace 1의 `find_kbo_game` 호출 argument, observation, latency raw 데이터 |
| 정상 좌석 추천 run | `docs/observability/examples/normal_seat_recommendation_run.json` | Trace 2의 run 메타데이터 + 좌석 추천 최종 답변 본문 |
| 정상 좌석 추천 Tool 호출 | `docs/observability/examples/normal_seat_recommendation_tool_calls.json` | Trace 2의 5개 Tool(`find_kbo_game`→`get_stadium_info`→`get_weather_context`→`search_baseball_knowledge`→`score_seat_candidates`) 각각의 argument와 observation 전문 |
| 실패 케이스 run | `docs/observability/examples/failure_game_not_found_run.json` | 실패 trace의 run 메타데이터와 fallback 답변 |
| 실패 케이스 Tool 호출 | `docs/observability/examples/failure_game_not_found_tool_calls.json` | `find_kbo_game`의 `status=not_found`, `error.code=GAME_NOT_FOUND` 응답 원본 |
| 실행 요약 | `docs/observability/examples/summary.md` | 세 trace의 정량 지표(latency, step count, tool error count)를 표 형태로 요약 |
| 전체 흐름 다이어그램 | `docs/observability/examples/flow.mmd` | Mermaid 형식의 Agent 실행 흐름도(입력 → Tool 분기 → 최종 답변) |

인덱싱 결과:

```text
FAISS index status: ready
document count: 239
stadium_seat: 213
stadium_metadata: 9
ticketing_guide: 10
logistics_guide: 7
embedding model: text-embedding-3-small
```

## 민감정보 처리

- `.env`, API key, LangSmith API key는 commit하지 않습니다.
- LangSmith metadata에는 전체 `user_context`를 저장하지 않고 `selected_game_id`, `selected_stadium_id`, 후보 경기 수처럼 재현에 필요한 요약값만 남깁니다.
- Tool argument masking 규칙에서 `api_key`, `token`, `password`, `secret`, `payment_info`, `phone`, `email`, `address`는 `[excluded]`로 기록합니다.
- `origin` 값이 긴 문자열이면 앞 2글자만 남기고 나머지는 마스킹합니다.
- 제출용 trace에는 개인정보가 없는 예시 입력만 사용합니다.
- RAG 문서 전문, API key, 로컬 `.env` 값은 README에 붙이지 않습니다.

## 배운 점

1. 최종 답변만 저장하면 Agent의 판단 근거를 알기 어렵고, Tool argument와 observation을 같이 남겨야 문제 원인까지 역추적할 수 있었습니다.
2. step별 latency를 따로 기록하니 전체 latency 중 LLM reasoning과 tool I/O 중 어느 쪽이 병목인지 한눈에 구분됐습니다(예: 좌석 추천 trace는 tool 합계 3141ms vs 전체 23564ms).
3. 정상 케이스만 보면 멀쩡해 보이는 흐름도 실패 케이스 trace를 함께 두니 "어디서 멈춰야 하는가"를 더 정확히 검증할 수 있었습니다.
4. prompt version을 trace에 함께 기록해두니 답변 품질이 흔들렸을 때 "prompt가 바뀌었는지 / 모델이 흔들렸는지"를 빠르게 가를 수 있었습니다.
