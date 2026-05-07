Project: AI ETF 리밸런싱 코치 & 매매 일지 Agent

Author: Senior Software Architect & Technical Lead

Date: 2026-05-07

1. Executive Summary & Context
   Vision:

본 프로젝트의 기술적 비전은 이기종 데이터(포트폴리오 이미지, 외부 API 지표, 자연어 투심)를 결합하여 사용자에게 ‘실질 노출도(True Exposure)’를 정량적으로 계산하고, ReAct(Reasoning + Acting) 기반의 LLM 에이전트를 통해 데이터 기반의 리밸런싱 조언과 자동 매매 일지 기록을 제공하는 통합 아키텍처를 구축하는 것입니다.

User Personas:

Primary User: 기술주 및 관련 ETF를 혼합 보유하고 있으며, 변동성 장세에서 리스크 관리를 위해 정확한 포지션 파악과 기록이 필요한 개인 투자자.
Goals vs. Non-Goals:

Goals:
멀티모달 LLM을 활용한 95% 이상의 포트폴리오(Ticker, 수량) 인식률 달성.
ReAct 에이전트의 안정적 도구(Tool) 호출 및 P99 Latency 8초 이내(LLM 스트리밍 포함) 응답.
단일 테이블(Single-Table) 기반의 고성능 NoSQL(DynamoDB) 일지 저장소 구축.
Non-Goals:
증권사 API를 통한 실제 자동 매수/매도 주문 실행 (완전 배제).
HFT(High-Frequency Trading, 고빈도 매매) 수준의 실시간 틱 데이터 처리. 2. System Architecture & Flow
Architecture Rationale (Why):

에이전트의 워크플로우는 사용자의 프롬프트 의도에 따라 동적으로 변합니다. 따라서 정적인 파이프라인 대신, 중앙에 Orchestrator(LLM)를 두고 각 기능을 Tool (Micro-functions) 로 분리한 Event-driven & Agentic 아키텍처를 채택합니다. 상태 비저장(Stateless) API 백엔드와 Serverless DB를 조합하여 초기 인프라 유지보수 비용을 최소화합니다.

2.1 High-Level Architecture
코드 스니펫

graph TD
Client[Web/Mobile Client] -->|HTTPS| APIGW[API Gateway]
APIGW -->|Auth & Rate Limit| Auth[AWS Cognito]
APIGW -->|Route| AgentSvc[Agent Service Layer - ECS/Fargate]

    subgraph "Agent Core (ReAct)"
        AgentSvc -->|Prompt & Image| LLM[LLM Provider - GPT-4o / Claude 3.5]
        LLM -.->|Tool Call: Vision| Tool_Vision[Vision Extractor]
        LLM -.->|Tool Call: API| Tool_ETF[ETF Constituent Tool]
        LLM -.->|Tool Call: API| Tool_Macro[Market Macro Tool]
        LLM -.->|Tool Call: DB| Tool_DB[Journal DB Tool]
    end

    Tool_ETF -->|HTTP GET| FMP[FMP API]
    Tool_Macro -->|HTTP GET| Yahoo[Yahoo Finance API]
    Tool_DB <-->|Read/Write| DynamoDB[(Amazon DynamoDB)]

2.2 Sequence Diagram (Core Happy Path)
코드 스니펫

sequenceDiagram
participant U as User
participant A as Agent Service
participant L as LLM (ReAct)
participant E as External APIs (FMP/Yahoo)
participant D as DynamoDB

    U->>A: POST /api/chat (Image + "엔비디아 비중 및 VIX 확인 후 일지 저장")
    A->>L: Send Context + Task

    Note over L: Thought: 이미지에서 자산 추출 필요
    L->>A: Action: Vision_Extractor
    A-->>L: Observation: [NVDA: 50, QQQ: 100]

    Note over L: Thought: QQQ 내 NVDA 비중 확인
    L->>A: Action: ETF_Constituent(QQQ)
    A->>E: GET /etf-holdings/QQQ
    E-->>A: [NVDA: 8.5%]
    A-->>L: Observation: ETF data

    Note over L: Thought: VIX 지수 확인
    L->>A: Action: Market_Macro(^VIX)
    A->>E: GET /vix
    E-->>A: 25.4
    A-->>L: Observation: VIX 25.4

    Note over L: Thought: 분석 완료, DB에 저장
    L->>A: Action: Journal_DB(write, content)
    A->>D: PutItem
    D-->>A: Success
    A-->>L: Observation: Saved

    Note over L: Final Answer 생성
    L-->>A: Markdown Response + Chart JSON
    A-->>U: Stream Response to UI

3. Functional Requirements (User Stories to Tech Spec)
   User Story / Feature Logic & Implementation Success Metrics Edge Cases & Fallbacks
   Vision Extraction (이미지 자산 파악) Multimodal LLM 파싱. Base64 인코딩 후 프롬프트(Zero-shot JSON schema)와 함께 전송. OCR 정확도 > 98%, Ticker 맵핑 실패율 < 2%. 흐린 이미지/인식 불가: 빈 JSON 반환 및 LLM이 "텍스트로 입력해 주세요"로 Fallback 유도.
   True Exposure Math (실질 비중 연산) $W_{true} = \sum (Direct) + \sum (ETF \times Weight_{etf})$. 내부 Math Tool 또는 Python REPL 활용. 연산 에러율 0% (LLM 자체 계산 방지, 코드 실행기 위임). API 미지원 ETF: 지원 불가 안내 후 개별주만으로 부분 계산.
   ReAct Orchestration (동적 툴 호출) LangChain/LlamaIndex 기반 ReAct 프레임워크 구현. Max iterations = 7 설정. 쿼리 당 Tool 호출 P95 Latency < 6.5s. 무한 루프(Hallucination): Max Step 도달 시 Force Stop 후 계산된 부분까지만 반환.
   Journaling (CRUD) (매매 일지 기록) DynamoDB PutItem, Query API. Timestamp 기반 정렬. DB Write P99 Latency < 50ms. DB Throttling: Exponential Backoff 및 AWS SQS 기반 비동기 재시도 큐 구축.
4. Data & API Design
   4.1 Data Model (Amazon DynamoDB - Single Table Design)
   다양한 접근 패턴(사용자별 전체 일지 조회, 특정 기간 조회, 특정 종목 검색)을 효율적으로 처리하기 위해 GSI(Global Secondary Index)를 활용합니다.

Attribute Name Type Description / Key Role
PK (Partition Key) String USER#{user_id}
SK (Sort Key) String JOURNAL#{YYYY-MM-DD}#{unix_timestamp}
GSI1_PK String USER#{user_id}#TICKER#{ticker} (특정 종목 일지 검색용)
GSI1_SK String JOURNAL#{YYYY-MM-DD}
portfolio_state Map(JSON) 추출된 포트폴리오 스냅샷 (Ticker, 수량 등)
market_context Map(JSON) 저장 당시 VIX, 투심 지표 스냅샷
decision_text String Agent의 리밸런싱 제안 및 사용자의 결정 내용
4.2 API Specification (RESTful)

1. Chat Interaction Endpoint (Agent 연동)

POST /api/v1/agent/chat
Content-Type: multipart/form-data (이미지 처리 위해)
Request Body:
user_query (String, Required)
session_id (String, Required for conversational memory)
portfolio_image (File, Optional)
Response (Server-Sent Events - SSE 권장): 스트리밍으로 Thought, Action, Final Answer 및 UI 렌더링용 chart_data (JSON) 전달. 2. Journal Retrieval Endpoint

GET /api/v1/journal
Query Params: start_date, end_date, ticker (Optional)
Response (200 OK): {"items": [{"date": "...", "decision_text": "...", "portfolio_state": {...}}]} 5. Non-Functional Requirements (The 'Quality' Specs)

1. Performance (성능 및 확장성)

Latency: ReAct 에이전트의 특성상 동기식 최종 응답은 느립니다. 체감 지연 시간을 줄이기 위해 첫 번째 토큰 도달 시간(TTFT: Time To First Token) < 1.5s, 전체 응답 P99 < 8.0s를 목표로 합니다.
Throughput: 초기 목표 Max TPS 50. ECS Fargate 자동 스케일링을 통해 CPU 사용률 70% 초과 시 컨테이너 증설. 2. Observability (관측 가능성)

Logging & Tracing: LLM 호출 비용과 디버깅을 위해 LangSmith 또는 Helicone을 도입하여 ReAct의 매 Step(Thought/Action/Observation)을 로깅합니다.
Metrics: AWS CloudWatch를 통해 API Latency, HTTP 5xx 에러율, Tool별 호출 실패율(예: FMP API 타임아웃)을 모니터링 및 알람(Slack/PagerDuty) 연동. 3. Security (보안 및 규정 준수)

Data in Transit / Rest: 모든 API 통신은 TLS 1.3 암호화. DynamoDB는 AWS KMS Managed Key를 통해 Data-at-rest 암호화 적용.
Rate Limiting: 악의적인 외부 API 및 LLM 비용 폭탄(Cost Overrun) 방지를 위해 API Gateway 레벨에서 사용자당 분당 10회(10 RPM), 일 50회 호출 제한 적용. 6. Risks & Infrastructure

1. Technical Risks (기술 부채 및 위험 요소)

LLM Hallucination on Math: LLM은 수치 연산에 취약합니다. Mitigation: 절대 LLM이 텍스트 내에서 직접 비율을 계산하지 않도록 프롬프트를 강제하며, Python 기반의 Calculator_Tool을 Action으로 제공하여 결과를 Observation으로 받도록 설계합니다.
Prompt Weight Limit: 다중 툴 명세(Vision, ETF, Macro, DB)와 과거 대화 이력이 누적되면 Context Window 한계 및 처리 속도 저하가 발생합니다. Mitigation: Semantic Search(Vector DB)를 통해 관련된 과거 일지만 주입하는 RAG(Retrieval-Augmented Generation) 패턴으로 전환을 준비합니다. 2. External Dependencies & Circuit Breaking

FMP / Yahoo Finance API 의존성: 서드파티 API 장애 시 에이전트 전체가 마비될 수 있습니다. Resilience Strategy: Resilience4j 또는 서비스 메시를 활용하여 Circuit Breaker 패턴을 적용. API 연속 3회 실패 시 Circuit을 Open하고, 에이전트에게 "시장 데이터 API 장애"라는 내부 Status를 주입하여, 지표 없이 비중 계산만 수행하도록 Fallback 로직을 구현합니다. 3. Deployment (CI/CD)

Pipeline: GitHub Actions를 활용한 자동화. Lint/Test -> Docker Build -> ECR Push -> ECS Update.
Strategy: 사용자 경험 저하를 막기 위해 Blue-Green Deployment 방식을 채택하며, 새 프롬프트나 에이전트 로직 배포 시 내부 섀도우(Shadow) 테스트를 통해 프롬프트 회귀(Prompt Regression) 여부를 자동 평가(LLM-as-a-Judge)합니다.
