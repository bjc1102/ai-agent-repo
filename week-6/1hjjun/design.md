
# design.md

## 1. 개요·목적
*   **해결하려는 문제**: 투자자가 보유한 ETF(예: QQQ)와 개별주(예: NVDA) 간의 '실질 종목 노출도(True Exposure)'를 정확히 파악하고, 거시 경제 지표 및 유튜브 투심을 종합해 리밸런싱 결정을 내리며 이를 매매 일지에 자동 기록한다.
*   **타깃 사용자**: 기술주 ETF와 개별주 혼합 포트폴리오를 운영하며, 데이터 기반의 체계적인 매매 일지 관리를 원하는 개인 투자자.
*   **왜 Agent여야 하는가**: 사용자의 요청이 "종목 비중만 계산해 줘"일 수도 있고, "시장 상황 보고 리밸런싱 제안 후 일지에 저장해 줘", 혹은 "과거 매매 기록 찾아줘"일 수도 있습니다. 요청의 의도에 따라 이미지 인식(Vision), ETF API 연동, 유튜브 검색, 복잡한 수치 연산, DB 읽기/쓰기 등 Tool 호출 순서와 조합이 매번 달라집니다. 고정된 순서로 실행되는 Workflow나 단순한 단일 LLM 호출로는 이 동적인 경로 분기를 처리할 수 없습니다.

## 2. 사용자 시나리오
*   **Persona**: 이수익 (30대 직장인, 기술주/반도체 중심 투자, 리스크 관리에 관심 많음)
*   **대표 요청**:
    1.  *(앱 화면 이미지 첨부)* "내 자산 중에 엔비디아의 실질 비중이 총 몇 %인지 계산하고 웹에서 볼 수 있게 차트 데이터로 줘."
    2.  "요즘 나스닥 불안한데 주요 유튜브 경제 채널 요약해서 참고하고, 내 QLD 비중을 어떻게 줄일지 제안한 다음 오늘 매매 일지에 저장해 줘."
    3.  "지난달 FOMC 때 내가 왜 QQQ를 팔았었는지 일지 검색해 보고, 지금 주가랑 비교해서 복기해 줘."
*   **각 요청이 단일 Tool 한 번으로 끝나지 않는 이유**:
    *   요청 1: Vision(자산 추출) → ETF 분석(편입비 조회) → 수치 연산 Tool이 순차적으로 필요함.
    *   요청 2: 유튜브 검색(투심 분석) → 시장 지표(VIX 조회) → DB 쓰기(일지 저장) 등 판단과 액션이 복합적으로 얽혀 있음.
    *   요청 3: DB 읽기(과거 기록) → 시장 지표(현재가 조회) Tool을 조합해 비교 분석해야 함.

## 3. 기능 요구사항
*   **Must-have**:
    *   사용자의 포트폴리오 이미지를 입력받아 종목(Ticker), 수량, 평가액을 JSON 형태로 추출한다.
    *   특정 ETF의 내부 편입 비율을 조회하여 개별주와의 합산 '실질 노출 비중(True Exposure)'을 계산하고 시각화용 데이터를 출력한다.
    *   거시 경제 지표와 투심 데이터를 입력받아 리밸런싱 권고안을 자연어로 출력하고, 이 논리를 DB(매매 일지)에 기록한다.
*   **Nice-to-have**:
    *   유튜브 키워드 검색을 통해 최신 영상 대본을 요약하여 투심(Bull/Bear) 지표를 도출한다.
    *   과거 특정 기간의 매매 일지를 조회하여 현재 내리는 결정과의 일관성을 점검한다.

## 4. Agent 패턴 선택과 근거
*   **선택한 패턴**: ReAct (Reasoning + Acting)
*   **선택 근거**: 사용자의 요청 범위가 매우 넓습니다. Agent가 관찰(Observation)된 중간 결과물(예: 'Vision으로 추출한 QQQ 보유량', '현재 VIX 지수')을 바탕으로 다음 행동(ETF 분석을 할지, DB 저장을 할지)을 스스로 추론하고 결정해야 하므로 ReAct 패턴이 가장 적합합니다.
*   **루프 구조도**:
    1. 사용자 입력 분석 (Thought)
    2. 자산 파악 필요 시 Vision Tool 호출 (Action → Observation)
    3. 세부 비중 파악 필요 시 ETF Tool 호출 (Action → Observation)
    4. 시장 분석 필요 시 Macro Tool 또는 YouTube Tool 호출 (Action → Observation)
    5. 모든 데이터 수집 후 실질 비중 및 리밸런싱 계산 (Thought)
    6. 기록 필요 시 DB 쓰기 Tool 호출 (Action → Observation)
    7. 최종 응답 및 웹 UI 렌더링용 JSON 반환 (Final Answer)

## 5. 동작 명세
*   **입력 스키마**: `{"image_url": "string (optional)", "user_query": "string"}`
*   **출력 스키마**: `{"answer_text": "string", "chart_data": "json (optional)", "is_saved": "boolean"}`
*   **정상 흐름 (요청 2 기준)**:
    *   Thought: 사용자가 QLD 리밸런싱과 일지 저장을 요청했다. 유튜브 투심과 거시 시장 지표를 확인하자.
    *   Action: `YouTube_Sentiment(query="나스닥 전망")`
    *   Observation: `{"sentiment": "Bearish", "summary": "단기 조정 우려 심화"}`
    *   Action: `Market_Macro(ticker="^VIX")`
    *   Observation: `{"current": 25.4}`
    *   Thought: VIX가 25 이상으로 높고 유튜브 투심이 부정적이므로 레버리지 비중 축소를 제안하고 이를 일지에 저장해야겠다.
    *   Action: `Journal_DB(mode="write", content="VIX 25.4, 투심 Bearish. QLD 비중 15% 축소 제안")`
    *   Observation: `{"status": "success"}`
    *   Final Answer: "현재 변동성 증가와 하락 투심을 고려해 QLD 15% 축소를 제안하며, 이 내용을 매매 일지에 기록했습니다."
*   **예외 흐름**: Vision 도구가 이미지를 인식하지 못하거나 화질이 낮을 경우 `{"error": "VISION_FAIL"}` 반환. Agent는 임의로 비중을 지어내지 않고 사용자에게 "이미지 화질이 낮아 종목 인식이 어렵습니다. 텍스트로 보유 종목을 입력해 주세요."라고 재요청.
*   **종료 조건**: 최대 스텝 수(max steps = 7) 도달 시, 또는 사용자의 모든 요청(계산 및 저장 등)을 완료하고 최종 응답(Final Answer)을 생성했을 때 종료.

## 6. Tool 명세
| Tool 이름 | 목적(1줄) | 입력 스키마 | 출력 스키마 | 실패 시 반환 | 사용 조건 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Vision_Extractor` | 잔고 이미지에서 자산 추출 | `{"image_url": str}` | `{"assets": [{"ticker": str, "amount": float}]}` | `{"error": "UNREADABLE_IMAGE"}` | 이미지가 입력되었을 때 |
| `ETF_Constituent` | ETF 내 개별 주식 편입 비중 조회 | `{"etf_ticker": str}`| `{"holdings": [{"ticker": str, "weight": float}]}`| `{"error": "ETF_NOT_FOUND"}` | 포트폴리오에 ETF가 포함되어 있을 때 |
| `Market_Macro` | 주가, VIX 등 시장 지표 조회 | `{"ticker": str}` | `{"current_price": float, "trend": str}` | `{"error": "API_TIMEOUT"}` | 시장 상황 판단이 필요할 때 |
| `YouTube_Sentiment` | 영상 대본 요약 기반 투심 분석 | `{"keyword": str}` | `{"sentiment": str, "summary": str}` | `{"error": "NO_VIDEOS"}` | 전문가 의견 등 정성적 평가 요구 시 |
| `Journal_DB` | 매매 일지 DB 기록 및 과거 조회 | `{"mode": "read"\|"write", "date": str, "text": str}` | `{"status": "ok", "data": str}` | `{"error": "DB_ERROR"}` | 기록을 저장하거나 복기해야 할 때 (파괴적 동작 방지 위해 write 시 confirm=True 내부 처리) |

## 7. 데이터셋
*   **ETF_Constituent**: FMP (Financial Modeling Prep) API의 ETF Holdings 엔드포인트 활용.
    *   *응답 샘플*: `[{"symbol": "NVDA", "weightPercentage": 8.54}, {"symbol": "AAPL", "weightPercentage": 8.01}]`
*   **Market_Macro**: Yahoo Finance API (RapidAPI 경유). 실시간 지수 제공, 인증 필요(API Key).
    *   *응답 샘플*: `{"symbol": "^VIX", "regularMarketPrice": 25.4}`
*   **Journal_DB**: AWS DynamoDB 연동 (설계/평가 시에는 JSON 파일로 Mocking).
    *   *Mock 읽기 응답 샘플*: `{"date": "2025-08-15", "decision": "QQQ 10% 매도", "reason": "잭슨홀 미팅 매파적 발언 동조"}`
*   **YouTube_Sentiment**: YouTube Data API v3로 영상 ID 획득 후 `youtube-transcript-api`로 자막 추출. (실시간 변환 대신 LLM 프롬프팅으로 Mock 처리 가능)

## 8. 성공 판정 기준
1.  "이미지 + 실질 비중 계산" 복합 요청에 대해 `Vision_Extractor` → `ETF_Constituent` 순서로 Tool을 호출하는가. (예/아니오)
2.  개별주(NVDA)와 ETF(QQQ) 동시 보유 시, 두 데이터를 더하여 '실질 비중'을 수학적으로 정확히 연산해내는가. (예/아니오)
3.  최종 응답(출력 스키마)에 웹 UI 렌더링을 위한 `chart_data` JSON이 누락 없이 포함되어 있는가. (예/아니오)
4.  "저장해 줘"라는 요청이 있을 때 반드시 `Journal_DB` Tool을 'write' 모드로 호출한 뒤 종료하는가. (예/아니오)
5.  7 step 이내에 무한 루프에 빠지지 않고 정상적으로 종료하는가. (예/아니오)

## 9. 제약·확장
*   **현재 설계의 한계**: 단일 Agent가 Vision 처리(멀티모달), 유튜브 긴 대본 요약(긴 컨텍스트), 복잡한 수치 계산, DB 연동을 모두 수행하므로 프롬프트가 매우 무거워지고 실행 속도(Latency)가 지연될 수 있습니다.
*   **Multi Agent로 확장 시 역할 분리 지점**:
    *   `Orchestrator Agent`: 사용자의 입력을 받아 목표를 분배하고 최종 웹 UI용 응답(JSON)을 조립.
    *   `Data & Math Worker`: Vision 추출 결과물과 ETF API를 조합해 실질 비중을 산출하는 정량 계산 전담.
    *   `Research Worker`: 유튜브 대본 추출 및 거시 지표를 분석하여 투심(Bull/Bear)을 판별하는 정성 분석 전담.
*   **장기 상태 메모리 (7주차 심화 연결)**: 현재는 사용자가 명시적으로 "저장해 줘" 할 때만 DB를 쓰지만, 향후에는 Agent 스스로 사용자의 과거 '투자 성향(예: 손실 회피 성향 강함)'이나 '반복적인 매매 실수'를 프로파일링하여 메모리에 담아두고 선제적으로 조언하는 구조로 확장할 수 있습니다.
