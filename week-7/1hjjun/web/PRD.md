Product Requirements Document (PRD) Product Name: AI ETF 리밸런싱 코치 & 매매 일지 Agent

Document Owner: Senior Product Manager / Solution Architect

Date: 2026-05-07

1. Executive Summary & Context
   The 'Why' (제품 존재 이유): 현재 개인 투자자들은 QQQ와 같은 기술주 ETF와 NVDA, AAPL 등 개별 주식을 혼합하여 포트폴리오를 구성합니다. 이 경우 자신이 특정 종목(예: 엔비디아)에 실제로 얼마만큼 노출되어 있는지(True Exposure)를 정확히 인지하지 못해, 시장 변동성 확대 시 리스크 관리에 실패하는 페인 포인트(Pain Point)가 존재합니다. 또한, 매매 결정을 내릴 때 거시 경제 지표와 투심을 파악하고 이를 일지로 기록하는 과정이 파편화되어 있어 지속적인 복기(Retrospective)가 불가능합니다.

Business Justification (비즈니스 정당성 확보): 이 Agent는 단순한 챗봇이 아닙니다. 비전(Vision) 기술로 진입 장벽을 낮추고, ETF 편입비 기반의 정확한 수치 연산을 제공하며, 매매 일지(Trade Journal) DB와 연동하여 사용자 락인(Lock-in) 효과를 극대화합니다. 사용자는 데이터에 기반한 의사결정을 내릴 수 있으며, 프로덕트는 '포트폴리오 분석 -> 실행 제안 -> 기록 및 복기'라는 완벽한 투자 사이클을 소유하게 됩니다.

2. Goals & Guardrail Metrics
   성공적인 에이전트의 동작은 '얼마나 정확하게', '얼마나 끝까지' 임무를 완수하느냐에 달려있습니다.

Key Performance Indicators (KPIs):

Task Success Rate: 사용자의 복합 요청(계산+분석+저장)에 대해 Agent가 에러 없이 최종 응답(Final Answer)에 도달한 비율 (목표: 90% 이상).
Journaling Engagement: 주간 활성 일지 작성자(WAJ: Weekly Active Journalers) 수 및 인당 주평균 일지 저장 횟수.
Tool Utilization Balance: 단일 세션 내 다중 툴(Vision + ETF + DB 등) 호출 비율.
Guardrail Metrics (Counter-metrics):

Agent Loop Timeout Rate: ReAct 패턴 특성상 환각(Hallucination)으로 인한 무한 루프 위험이 있습니다. Max Steps(7회) 도달로 인한 강제 종료 비율 (목표: 3% 미만).
Math Hallucination Rate: 개별주와 ETF 합산 실질 비중 계산 시 수학적 오류 발생률. (LLM의 약점이므로, 연산 전담 Tool 호출 실패율 모니터링).
Journal Deletion/Edit Rate: Agent가 자동 기록한 일지를 사용자가 직후에 삭제하거나 대폭 수정하는 비율 (이해력 오류 검증). 3. User Stories with Acceptance Criteria (AC)
Story 1: 실질 노출도 계산 (True Exposure)

"사용자로서 내 증권사 앱 잔고 이미지를 올리면, 개별주와 ETF 간의 중복을 계산해 특정 종목의 '실질 비중'을 파악할 수 있다."

AC 1: Vision_Extractor가 이미지에서 Ticker, 수량, 평가액을 JSON으로 정확히 추출해야 한다.
AC 2: ETF_Constituent API를 호출하여 ETF 내부 편입 비중을 가져오고, 개별주 합산 수치를 수학적으로 오류 없이 도출해야 한다.
AC 3: 최종 응답 스키마에 웹 UI 렌더링용 chart_data JSON이 포함되어야 한다.
Story 2: 시장 투심 반영 리밸런싱 및 기록

"사용자로서 나스닥 불안 시 유튜브 투심과 VIX 지수를 확인하고, 조언을 얻은 뒤 그 맥락을 일지에 바로 저장할 수 있다."

AC 1: YouTube_Sentiment와 Market_Macro 툴을 병렬 또는 순차적으로 호출하여 현재 시장 컨텍스트를 수집해야 한다.
AC 2: 수집된 데이터(Bull/Bear, VIX 지수 등)를 근거로 한 자연어 리밸런싱 권고안이 출력되어야 한다.
AC 3: 사용자의 '저장해 줘'라는 의도를 파악하여 Journal_DB 툴을 mode="write"로 반드시 호출해야 한다.
Story 3: 과거 매매 기록 복기

"사용자로서 과거 특정 이벤트(예: FOMC) 때 내가 왜 매도했었는지 기록을 찾아보고 현재 상황과 비교할 수 있다."

AC 1: Journal_DB 툴을 mode="read"로 호출하여 관련 과거 기록을 성공적으로 조회해야 한다.
AC 2: 과거 결정을 내렸던 컨텍스트와 현재가를 비교 분석하는 로직이 응답에 포함되어야 한다. 4. Functional & Data Requirements
Logic & Rules
True Exposure Calculation Logic: Total Ticker Weight = (Direct Ticker Value / Total Portfolio Value) + (ETF Value \* Ticker Weight inside ETF / Total Portfolio Value) (LLM이 직접 텍스트로 계산하지 않도록 내부적으로 Python/Math 실행 환경 혹은 엄격한 Step-by-step 프롬프팅 적용 필수)
MoSCoW Prioritization
Must Have:
잔고 이미지 텍스트/데이터 추출 (Vision).
ETF 편입종목 조회 및 실질 비중 연산.
ReAct 기반의 동적 Tool 호출 및 로직 분기.
AWS DynamoDB 기반 매매일지 Read/Write.
Should Have:
VIX 등 주요 거시 지표 API 연동 (Yahoo Finance).
웹 프론트엔드 차트 렌더링을 위한 정형 JSON Output.
Could Have:
유튜브 영상 자막 추출 기반의 투심 분석 (현재는 API 비용 및 Latency 리스크가 있으므로 후순위 혹은 Mock/경량화 모델 사용 고려).
Won't Have:
실제 증권사 API를 통한 '매수/매도 자동 주문 실행' (인가되지 않은 파괴적 액션 제한). 5. User Experience & Edge Cases
Happy Path (Core Flow):

사용자가 포트폴리오 스크린샷과 프롬프트를 입력 ("엔비디아 비중 계산하고, VIX 확인해서 일지에 저장해").
Agent가 Vision_Extractor 실행 -> 잔고 파악.
Agent가 ETF_Constituent 실행 -> QQQ 내 NVDA 비중 파악.
Agent가 실질 비중 연산 (Thought).
Agent가 Market_Macro 실행 -> VIX 25.4 파악.
Agent가 분석 결과 도출 및 Journal_DB Write 실행.
UI에 분석 텍스트, 차트(JSON 렌더링), "일지 저장 완료" 배지 노출.
Edge Cases & Error Handling:

Edge Case 1: Unreadable Image (VISION_FAIL)
대응: 이미지 해상도가 낮거나 증권사 UI가 아닌 경우. Agent는 환각을 일으키지 않고 {"error": "UNREADABLE_IMAGE"}를 인식하여, 사용자에게 "이미지 화질이 낮거나 포트폴리오를 인식할 수 없습니다. 보유 종목과 수량을 텍스트로 입력해 주시겠어요?"라고 정중하게 fallback 응답을 제공한다.
Edge Case 2: API Timeout / Rate Limit (API_TIMEOUT)
대응: Yahoo Finance나 FMP API 지연 시, ReAct 루프가 갇히지 않도록 Tool 자체에서 5초 TTL을 설정한다. 실패 시 "현재 시장 지표 데이터를 불러오는 데 지연이 발생하고 있습니다. 지표를 제외하고 비중 계산만 먼저 진행할까요?"로 응답.
Edge Case 3: 모호한 DB 기록 요청
대응: 파괴적 동작(DB 수정/삭제)이나 중요한 쓰기 시, Agent가 컨텍스트를 잘못 요약해 저장하는 것을 방지하기 위해, 사용자에게 "다음 내용으로 일지에 저장할까요?" 하고 1-Depth 컨펌 버튼을 UI로 제공하는 것을 권장. 6. Technical Considerations
API & Data Structure:
Agent Input Schema: {"image_url": "string (optional)", "user_query": "string"}
Agent Output Schema: {"answer_text": "string", "chart_data": "json (optional)", "is_saved": "boolean"}
DB Schema 제안 (DynamoDB - Single Table Design):
PK: USER#{user_id}
SK: JOURNAL#{YYYY-MM-DD}#{timestamp}
Attributes: portfolio_snapshot (JSON), market_context (JSON), decision_text (String).
Latency & Performance:
ReAct 패턴은 LLM을 여러 번 호출(Thought -> Action -> Observation 루프)하므로 응답 지연이 심할 수 있습니다.
완화 전략: Streaming 방식을 적용하여 Agent의 Thought와 Action 과정을 UI에 노출(예: "ETF 편입 비중을 확인하는 중...", "거시 경제 지표를 불러오는 중...")하여 체감 대기 시간(Perceived Latency)을 줄여야 합니다. 최대 실행 루프는 시스템 레벨에서 7회로 Hard-limit을 겁니다. 7. Go-To-Market (GTM) & Analytics
온보딩(Onboarding) 전략:

Zero State / Empty State: 처음 진입한 유저에게는 샘플 프롬프트(Chip)와 가상의 포트폴리오 이미지를 제공하여, 에이전트가 어떻게 복합적인 추론을 수행하는지 1 클릭으로 체험(Aha Moment)하게 합니다.
필수 트래킹 이벤트 (Event Logs):

agent_session_started: 쿼리 인입.
tool_invoked: 속성값으로 tool_name(예: Vision_Extractor, Journal_DB) 포함. 이를 통해 어떤 기능이 가장 많이 쓰이는지 파악.
journal_saved_success: 최종 DB 저장 완료 여부.
agent_max_step_reached: ReAct 루프가 7번 이상 돌아 강제 종료된 실패 케이스 (모니터링 알럿 연결 필수). 8. Open Questions & Risks
Technical Debt / Risk: 단일 LLM(Single Agent)이 멀티모달(Vision), 긴 컨텍스트 요약(YouTube), 복잡한 수치 연산, DB 오케스트레이션을 모두 담당하게 되면 컨텍스트 오염(Context overflow)이나 인스트럭션 무시 현상이 발생할 확률이 높습니다.
Open Question: 초기 PoC 이후, 사용량이 증가하면 Multi-Agent 구조(Supervisor Agent가 로우레벨 Worker Agent에게 Task를 분배)로 마이크로서비스화 할 것인가? (참고: 7주차 심화 확장 모델).
Data Reliability: FMP API에서 제공하는 ETF 편입 비중 데이터가 실시간이 아닐 수 있습니다(보통 1일 지연). 사용자가 당일 리밸런싱된 아주 정확한 소수점 단위의 수치를 요구할 경우 어떻게 안내할지 정책적 결정이 필요합니다. (예: "본 데이터는 전영업일 기준 편입비입니다" 면책 조항 추가).
