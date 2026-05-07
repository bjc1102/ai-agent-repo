# 6주차 실습 과제: AI Agent 설계서 작성 (정연승)

> **주제**: 하찮은 맥앱 아이디어 브리핑 에이전트

---

## 1. 개요·목적

### 해결하려는 문제

매일 "오늘 뭐 만들지?"를 고민하는 1인 바이브코더와 IT 종사자들은
글로벌 밈 트렌드와 IT 트렌드를 따로 수집하고, 유사 앱을 직접 검색하고,
구현 난이도까지 스스로 판단해야 한다.
이 에이전트는 그 과정을 자동화하여, 매일 "귀엽고 하찮지만 실용적인"
macOS 앱 아이디어를 브리핑해준다.
부수적으로, 사용자는 아이디어 브리핑을 받는 것만으로
오늘의 IT 트렌드와 글로벌 밈 흐름을 자연스럽게 파악할 수 있다.

### 타깃 사용자

바이브코딩으로 사이드 프로젝트를 시작하고 싶지만
아이디어 발굴과 트렌드 조사에 시간을 쓰기 싫은 1인 개발자 및 IT 종사자.

### 왜 Agent여야 하는가

**단일 LLM 호출로는 불가능하다.**  
"요즘 뭐가 유행이야?"를 LLM에게 물어보면 학습 데이터 기준의 과거 트렌드만
반환한다. 오늘의 Reddit 급상승 밈, YouTube Shorts 트렌딩 영상,
GitHub 트렌딩 레포지토리는 실시간 외부 Tool 없이는 절대 알 수 없다.

**RAG로도 불가능하다.**  
RAG는 미리 수집해둔 문서에서 검색하는 구조인데, Reddit·YouTube의 밈과
IT 트렌드는 매일 바뀐다. 어제 수집한 문서는 오늘 이미 낡았다.

**Workflow로도 불가능하다.**  
오늘 IT 트렌드가 "Rust 급부상"이냐 "MCP 핫함"이냐에 따라 조합할 밈이
달라지고, 호출할 Tool의 순서와 조합이 매번 달라진다.
고정된 실행 경로로는 이 동적 교차 분석을 처리할 수 없다.

에이전트만이 Reddit·YouTube의 밈 트렌드와 GitHub·HackerNews의 IT 트렌드를
실시간으로 수집하고, 두 소스를 교차 분석하여 유사 앱 존재 여부와
구현 난이도까지 동적으로 판단한 뒤, 최종 아이디어 브리핑을 생성할 수 있다.

---

## 2. 사용자 시나리오

### Persona

- **이름**: 이주임 (28세)
- **역할**: 4년차 백엔드 개발자, 보안 회사 재직 중
- **목적**: 퇴근 후 바이브코딩으로 매일 하찮은 맥앱을 하나씩 만들어
  GitHub에 올리고 싶다. 아이디어를 고민하는 시간이 오히려 만드는 시간보다
  길어서 매번 시작을 못한다.

---

### 요청 1 — "오늘 뭐 만들까?" (균형 탐색형)

> "오늘 뭐 만들면 재밌을까? 밈이든 IT 트렌드든 상관없어"

**호출 경로:**
```
trend_scanner(밈)
  → trend_scanner(IT 트렌드)
  → concept_generator(교차 조합)
  → app_existence_checker
  → feasibility_checker
```

**단일 Tool로 끝나지 않는 이유:**  
밈과 IT 트렌드를 동시에 수집한 뒤 교차 조합해야 하므로,
최소 2개의 탐색 Tool이 순차적으로 필요하고
그 결과에 따라 컨셉 생성 → 유사 앱 확인 → 난이도 판단까지 이어진다.

---

### 요청 2 — "개발자 감성으로 뽑아줘" (IT 트렌드 중심형)

> "요즘 개발자들 사이에서 핫한 거 있으면 그거 반영해서 아이디어 줘. 밈은 몰라도 돼"

**호출 경로:**
```
trend_scanner(IT 트렌드 집중, 밈 스킵)
  → concept_generator(IT 트렌드 단독 조합)
  → app_existence_checker
  → feasibility_checker
```

**단일 Tool로 끝나지 않는 이유:**  
밈 탐색을 건너뛰고 IT 트렌드만 수집하지만,
"GitHub에 이미 비슷한 게 있는지"를 반드시 확인해야 하고
바이브코딩 구현 가능 여부까지 판단해야 하므로 Tool 호출이 연쇄적으로 발생한다.

---

### 요청 3 — "아무도 안 만든 거 찾아줘" (공백 탐색형)

> "유사한 앱이 없는 완전 새로운 거 찾아줘. 비슷한 게 이미 있으면 다른 걸로 다시 찾아줘"

**호출 경로:**
```
trend_scanner(밈 + IT)
  → concept_generator
  → app_existence_checker
      [유사 앱 발견 시 → concept_generator 재호출 루프]
      [공백 확인 시   → feasibility_checker]
```

**단일 Tool로 끝나지 않는 이유:**  
app_existence_checker에서 유사 앱이 발견되면 concept_generator로 루프백하여
다른 컨셉을 재생성하는 동적 반복 구조가 필요하다.
고정 경로로는 이 루프를 구현할 수 없다.

---

## 3. 기능 요구사항

### Must-have

1. **트렌드 수집**
   - 입력: 사용자 요청 (밈 중심 / IT 중심 / 둘 다)
   - 출력: 오늘의 상위 밈 키워드 + IT 트렌드 키워드 각 3~5개

2. **아이디어 컨셉 생성**
   - 입력: 수집된 트렌드 키워드 조합
   - 출력: macOS 앱 컨셉 1~3개 (앱 이름 + 한 줄 설명 + 핵심 기능 1개)

3. **유사 앱 존재 여부 확인**
   - 입력: 생성된 앱 컨셉
   - 출력: Mac App Store·GitHub 유사 앱 존재 여부
     + 존재 시 해당 앱 이름과 리뷰 요약

4. **구현 난이도 판단**
   - 입력: 확정된 앱 컨셉
   - 출력: 바이브코딩 기준 예상 구현 기간 (1일 / 2~3일 / 1주일 이상)
     + 추천 기술 스택

5. **최종 브리핑 생성**
   - 입력: 위 1~4의 결과 전체
   - 출력: 캔버스 카드 형태의 오늘의 아이디어 브리핑
     (트렌드 요약 + 컨셉 + 공백 여부 + 난이도 한눈에 표시)

### Nice-to-have

1. **아이디어 진화 추적**
   - 입력: 오늘 생성된 브리핑 + 과거 히스토리
   - 출력: 동일 트렌드 재등장 시 이전 컨셉과 비교 분석
     (컨셉 고도화 여부 / 사용자 구현 완료 여부 / "저번보다 더 구체적인 방향" 제안)
   - 비고: 장기 메모리(Vector DB) 도입 시 고도화 가능 → 섹션 9 확장 지점 연결

2. **난이도 필터**
   - 입력: 사용자가 원하는 구현 기간 ("오늘 안에 만들 수 있는 것만")
   - 출력: 필터 조건을 충족하는 컨셉만 추려서 재브리핑

3. **트렌드 출처 투명성**
   - 입력: 사용자의 "이거 어디서 나온 트렌드야?" 질문
   - 출력: Reddit / YouTube / GitHub 등 출처 URL 직접 제공

---

## 4. Agent 패턴 선택과 근거

### 선택한 패턴: ReAct (Reasoning + Acting)

### 선택 근거

이 에이전트는 실행 전에 전체 계획을 세울 수 없다.
오늘 Reddit과 YouTube에서 어떤 밈이 급상승했는지,
GitHub에서 어떤 레포지토리가 트렌딩인지는
trend_scanner를 실행해봐야 비로소 알 수 있기 때문이다.

즉, 매 Observation 결과가 다음 Action을 결정하는 구조이므로
Plan-and-Execute처럼 전체 계획을 먼저 세우는 패턴은 적합하지 않다.
ReAct의 Thought → Action → Observation 루프가
이 동적 교차 분석 구조에 가장 자연스럽게 맞아떨어진다.

또한 app_existence_checker에서 유사 앱이 발견됐을 때
concept_generator로 루프백하는 재시도 구조가 필수적인데,
이 역시 ReAct의 Observation 결과 기반 동적 판단으로 처리된다.

### 루프 구조도

```
[START] 사용자 요청 수신

Thought: 사용자가 밈/IT/둘 다 중 어떤 방향을 원하는지 파악
Action:  trend_scanner(source=["reddit","youtube"], type="meme")
         trend_scanner(source=["github","hackernews"], type="IT")
Observe: 오늘의 밈 키워드 3개 + IT 트렌드 키워드 3개 수집

Thought: 두 트렌드를 교차 조합하여 맥앱 컨셉 생성
Action:  concept_generator(meme_trend, it_trend)
Observe: 앱 컨셉 후보 생성됨

Thought: 유사 앱이 이미 존재하는지 확인 필요
Action:  app_existence_checker(concept)
Observe: 유사 앱 발견 시 → concept_generator 재호출 (루프백)
         유사 앱 없음   → 다음 단계 진행

Thought: 바이브코딩으로 구현 가능한 수준인지 판단
Action:  feasibility_checker(concept)
Observe: 구현 기간 + 추천 스택 반환

[END] 캔버스 카드 브리핑 출력
```

---

## 5. 동작 명세

### 에이전트 시스템 프롬프트 방향성

```
당신은 매일 글로벌 밈 트렌드와 IT 트렌드를 교차 분석하여
"귀엽고 하찮지만 실용적인" macOS 앱 아이디어를 브리핑하는 에이전트입니다.

행동 원칙:
1. 반드시 trend_scanner를 가장 먼저 호출한다. 실시간 데이터 없이 컨셉을 생성하지 않는다.
2. app_existence_checker에서 유사 앱이 발견되면 즉시 concept_generator를 재호출한다.
3. 동일 조합으로 3회 이상 루프백 시 루프를 탈출하고 사용자에게 상황을 알린다.
4. 최종 응답에는 반드시 used_tools, loop_count, failure_type 메타데이터를 포함한다.
5. 최대 15스텝을 초과하지 않는다.
```

### 입력 스키마

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---|---|
| user_query | string | 필수 | 사용자 자연어 요청 |
| trend_focus | enum | 선택 | "meme" / "IT" / "both" (미입력 시 "both" 기본값) |
| difficulty_limit | enum | 선택 | "1day" / "3days" / "1week" (미입력 시 전체 허용) |
| exclude_existing | boolean | 선택 | true 시 유사 앱 있으면 자동 루프백 (기본값 false) |

### 출력 스키마

```json
{
  "today_brief": {
    "meme_trend": ["카피바라 밈", "게 사이드워크 밈"],
    "it_trend": ["MCP 핫함", "Rust 급부상"],
    "concepts": [
      {
        "app_name": "MCPurr",
        "description": "연결된 MCP 서버를 고양이로 시각화하는 메뉴바 앱",
        "core_feature": "서버 연결 상태를 고양이 표정으로 표시",
        "similar_app_exists": false,
        "difficulty": "2~3일",
        "stack": ["Swift", "AppKit", "MenuBarExtra"]
      }
    ]
  },
  "metadata": {
    "used_tools": [
      "trend_scanner",
      "concept_generator",
      "app_existence_checker",
      "feasibility_checker"
    ],
    "loop_count": 1,
    "failure_type": null,
    "fallback_action": null,
    "sources": {
      "meme": ["reddit.com/r/memes/...", "youtube.com/shorts/..."],
      "it":   ["github.com/trending", "news.ycombinator.com"]
    }
  }
}
```

### 정상 흐름 — 요청 3: "아무도 안 만든 거 찾아줘"

```
Thought 1:
  사용자가 유사 앱이 없는 완전 새로운 컨셉을 원한다.
  밈과 IT 트렌드를 모두 수집한 뒤 교차 조합이 필요하다.
  먼저 오늘의 트렌드부터 수집한다.

Action 1:
  trend_scanner(source=["reddit","youtube"], type="meme")

Observation 1:
  ["카피바라 글로벌 급상승", "게 사이드워크 밈", "고양이 찰떡 밈"]

Thought 2:
  밈 수집 완료. 이제 IT 트렌드를 수집한다.

Action 2:
  trend_scanner(source=["github","hackernews"], type="IT")

Observation 2:
  ["MCP 핫함", "Rust 급부상", "vibe coding 유행"]

Thought 3:
  두 트렌드를 교차 조합한다.
  "Rust 급부상 × 게 사이드워크 밈" 조합이
  개발자 감성과 유머를 동시에 잡을 수 있어 보인다.

Action 3:
  concept_generator(
    meme_trend="게 사이드워크 밈",
    it_trend="Rust 급부상"
  )

Observation 3:
  app_name: "CrabBuild"
  description: "Dock에서 게가 옆으로 걷는 Rust 빌드 진행바"
  core_feature: "빌드 진행률을 게 걸음 수로 시각화"

Thought 4:
  사용자가 유사 앱이 없는 것을 원했다.
  Mac App Store와 GitHub에서 유사 앱을 반드시 확인해야 한다.

Action 4:
  app_existence_checker(concept="CrabBuild")

Observation 4:
  similar_app_found: true
  similar_apps: [{"name": "Crabber", "source": "github"}]

Thought 5:
  유사 앱이 존재한다. 사용자 요청 조건 미충족.
  다른 조합으로 컨셉을 재생성해야 한다.
  "MCP 핫함 × 고양이 찰떡 밈" 조합을 시도한다.

Action 5:
  concept_generator(
    meme_trend="고양이 찰떡 밈",
    it_trend="MCP 핫함",
    exclude_concepts=["CrabBuild"]
  )

Observation 5:
  app_name: "MCPurr"
  description: "연결된 MCP 서버를 고양이로 시각화하는 메뉴바 앱"
  core_feature: "서버 연결 상태를 고양이 표정으로 표시"

Thought 6:
  새 컨셉 생성 완료. 유사 앱 여부를 다시 확인한다.

Action 6:
  app_existence_checker(concept="MCPurr")

Observation 6:
  similar_app_found: false ✅

Thought 7:
  유사 앱 없음 확인. 바이브코딩으로 구현 가능한지 판단한다.

Action 7:
  feasibility_checker(concept="MCPurr")

Observation 7:
  difficulty: "2~3일"
  stack: ["Swift", "AppKit", "MenuBarExtra"]

[END] 캔버스 카드 브리핑 출력
```

### 예외 흐름

| 상황 | Agent 동작 |
|---|---|
| trend_scanner 실패 (API 응답 없음) | `{error: "trend_fetch_failed", detail: "youtube API timeout"}` 반환 → 나머지 소스로 재시도 (Reddit만으로 계속 진행) |
| concept_generator 루프백 3회 초과 | 루프 중단 → `{error: "no_unique_concept", detail: "3회 시도 후 공백 컨셉 미발견"}` 반환 → 유사 앱 있어도 차별화 포인트 제안으로 대체 |
| feasibility_checker 판단 불가 | `{error: "feasibility_unknown"}` 반환 → 난이도 미정으로 브리핑 출력, 사용자에게 직접 판단 위임 |
| 모든 Tool 실패 | 최대 재시도 3회 후 중단 → `failure_type: "total_failure"` 메타데이터 기록 |

### 종료 조건

| 조건 | 설명 |
|---|---|
| 정상 종료 | 유사 앱 없는 컨셉 + 난이도 판단 완료 시 |
| 강제 종료 | max_steps = 15 초과 시 |
| 루프 감지 | concept_generator 동일 조합 재호출 3회 시 루프 탈출 |
| 사용자 중단 | 캔버스 UI에서 "중단" 선택 시 즉시 종료 |

---

## 6. Tool 명세

### Tool 1: trend_scanner

| 항목 | 내용 |
|---|---|
| 목적 | Reddit·YouTube·GitHub·HackerNews에서 오늘의 밈 및 IT 트렌드 키워드를 실시간 수집한다 |
| 사용 조건 | 항상 가장 먼저 호출된다. 사용자 요청에 trend_focus가 명시된 경우 해당 소스만 선택적으로 수집한다 |

```json
입력 스키마:
{
  "source": ["reddit", "youtube", "github", "hackernews"],
  "type": "meme | IT | both",
  "limit": 5
}

출력 스키마:
{
  "meme_trends": [
    {"keyword": "카피바라 밈", "source": "reddit", "url": "..."},
    {"keyword": "게 사이드워크 밈", "source": "youtube", "url": "..."}
  ],
  "it_trends": [
    {"keyword": "MCP 핫함", "source": "hackernews", "url": "..."},
    {"keyword": "Rust 급부상", "source": "github", "url": "..."}
  ]
}

실패 시 반환:
{
  "error": "trend_fetch_failed",
  "detail": "youtube API timeout",
  "partial_result": {
    "it_trends": [...]
  }
}
```

---

### Tool 2: concept_generator

| 항목 | 내용 |
|---|---|
| 목적 | 수집된 밈 트렌드와 IT 트렌드를 교차 조합하여 macOS 앱 컨셉 후보를 생성한다 |
| 사용 조건 | trend_scanner 실행 완료 후 호출된다. app_existence_checker에서 유사 앱이 발견된 경우 다른 조합으로 재호출된다 (루프백). 동일 조합으로 3회 이상 재호출 시 호출 중단 |

```json
입력 스키마:
{
  "meme_trend": "string",
  "it_trend": "string",
  "exclude_concepts": ["string"]
}

출력 스키마:
{
  "app_name": "MCPurr",
  "description": "연결된 MCP 서버를 고양이로 시각화하는 메뉴바 앱",
  "core_feature": "서버 연결 상태를 고양이 표정으로 표시",
  "target_os": "macOS",
  "concept_basis": {
    "meme": "고양이 찰떡 밈",
    "it": "MCP 핫함"
  }
}

실패 시 반환:
{
  "error": "concept_generation_failed",
  "detail": "동일 조합 3회 초과 — 유효한 교차 조합 소진",
  "fallback_action": "유사 앱 존재해도 차별화 포인트 제안으로 대체"
}
```

---

### Tool 3: app_existence_checker

| 항목 | 내용 |
|---|---|
| 목적 | 생성된 앱 컨셉과 유사한 앱이 Mac App Store 또는 GitHub에 이미 존재하는지 확인한다 |
| 사용 조건 | concept_generator 실행 완료 후 반드시 호출된다. 유사 앱 발견 시 concept_generator 루프백을 트리거한다. exclude_existing=false인 경우 유사 앱이 있어도 루프백 없이 결과를 그대로 반환한다 |

```json
입력 스키마:
{
  "concept": "string",
  "description": "string",
  "search_target": ["appstore", "github"]
}

출력 스키마 (성공):
{
  "similar_app_found": false,
  "similar_apps": []
}

출력 스키마 (유사 앱 발견):
{
  "similar_app_found": true,
  "similar_apps": [
    {
      "name": "Crabber",
      "source": "github",
      "url": "...",
      "similarity": "Dock 커스터마이징 앱"
    }
  ]
}

실패 시 반환:
{
  "error": "search_failed",
  "detail": "App Store API 응답 없음",
  "fallback_action": "GitHub 단독 탐색으로 재시도"
}
```

---

### Tool 4: feasibility_checker

| 항목 | 내용 |
|---|---|
| 목적 | 확정된 앱 컨셉을 바이브코딩으로 구현할 때 예상 기간과 추천 기술 스택을 판단한다 |
| 사용 조건 | app_existence_checker에서 유사 앱 없음이 확인된 후 마지막으로 호출된다. 난이도가 difficulty_limit을 초과하는 경우 결과에 초과 여부를 명시하고 사용자 판단에 위임한다 |

```json
입력 스키마:
{
  "concept": "string",
  "core_feature": "string",
  "difficulty_limit": "1day | 3days | 1week | null"
}

출력 스키마:
{
  "difficulty": "2~3일",
  "stack": ["Swift", "AppKit", "MenuBarExtra"],
  "difficulty_limit_exceeded": false,
  "vibe_coding_tip": "MenuBarExtra는 SwiftUI로 빠르게 구현 가능"
}

실패 시 반환:
{
  "error": "feasibility_unknown",
  "detail": "컨셉이 너무 추상적이어서 난이도 판단 불가",
  "fallback_action": "난이도 미정으로 브리핑 출력, 사용자 직접 판단 위임"
}
```

---

## 7. 데이터셋

### trend_scanner — IT 트렌드

| 항목 | 내용 |
|---|---|
| 출처 1 | HackerNews API (`https://hacker-news.firebaseio.com/v0/topstories.json`) |
| 출처 2 | GitHub REST API (`https://api.github.com/search/repositories?q=topic:trending`) |
| 인증 | 불필요 (HackerNews) / GitHub Token 선택 (60→5000 req/h) |
| 업데이트 주기 | 실시간 |
| 필드 수 | HackerNews: 6개 / GitHub: 10개+ |

**실제 응답 샘플 — HackerNews Top Story:**
```json
{
  "id": 43821045,
  "title": "MCP is the new LSP",
  "url": "https://blog.sbensu.com/posts/mcp/",
  "score": 847,
  "time": 1746123456,
  "type": "story"
}
```

**실제 응답 샘플 — GitHub Trending (Rust 관련):**
```json
{
  "name": "rustls",
  "description": "A modern TLS library in Rust",
  "stargazers_count": 6821,
  "language": "Rust",
  "html_url": "https://github.com/rustls/rustls"
}
```

---

### trend_scanner — 밈 트렌드

| 항목 | 내용 |
|---|---|
| 출처 1 | Reddit API (`https://oauth.reddit.com/r/memes/hot`) |
| 출처 2 | YouTube Data API v3 (`https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&chart=mostPopular`) |
| 인증 | Reddit: OAuth2 / YouTube: Google API Key (둘 다 무료) |
| 업데이트 주기 | 실시간 |
| 무료 할당량 | YouTube 10,000 units/일 |

**실제 응답 샘플 — Reddit r/memes Hot:**
```json
{
  "title": "capybara doesn't care about anything",
  "subreddit": "memes",
  "score": 94200,
  "url": "https://reddit.com/r/memes/...",
  "created_utc": 1746100000
}
```

**실제 응답 샘플 — YouTube Trending:**
```json
{
  "snippet": {
    "title": "카피바라가 모든 걸 이겨내는 법 🦫",
    "tags": ["capybara", "meme", "viral", "shorts"]
  },
  "statistics": {
    "viewCount": "4200000",
    "likeCount": "380000"
  }
}
```

---

### app_existence_checker

| 항목 | 내용 |
|---|---|
| 출처 1 | iTunes Search API (`https://itunes.apple.com/search?term={query}&entity=macSoftware`) |
| 출처 2 | GitHub Search API (`https://api.github.com/search/repositories?q={query}+topic:macos`) |
| 인증 | 불필요 (iTunes) / GitHub Token 선택 |
| 업데이트 주기 | 실시간 |

**실제 응답 샘플 — iTunes Search:**
```json
{
  "resultCount": 1,
  "results": [{
    "trackName": "Lungo",
    "description": "Lungo prevents your Mac from falling asleep",
    "averageUserRating": 4.5,
    "version": "1.7.0",
    "trackViewUrl": "https://apps.apple.com/..."
  }]
}
```

**실제 응답 샘플 — GitHub Search:**
```json
{
  "total_count": 3,
  "items": [{
    "name": "cat-in-the-dock",
    "description": "A cat that lives in your Mac Dock",
    "stargazers_count": 1240,
    "html_url": "https://github.com/..."
  }]
}
```

---

### concept_generator / feasibility_checker

| 항목 | 내용 |
|---|---|
| 출처 | 외부 API 없음 — LLM 내부 추론으로 생성 |
| 인증 | Anthropic API Key (기존 프로젝트와 동일) |
| 비고 | trend_scanner 결과를 컨텍스트로 주입하여 생성. 외부 데이터 의존 없음 |

---

### Golden Dataset — 엣지 케이스 포함

| 케이스 유형 | 시나리오 | 기대 동작 |
|---|---|---|
| **정상 (Success)** | 트렌드 수집 → 유사 앱 없는 컨셉 생성 → 난이도 판단 완료 | 브리핑 정상 출력 |
| **실패 (Failure)** | YouTube API timeout → Reddit만으로 재시도 | partial_result로 계속 진행 |
| **조건 누락 (Missing Info)** | 사용자 입력이 "뭔가 만들어줘" 한 마디뿐 | trend_focus="both"로 기본값 적용 후 진행 |
| **루프 과다 (Loop Overflow)** | app_existence_checker가 3회 연속 유사 앱 발견 | 루프 탈출 → fallback: 차별화 포인트 제안 |
| **악성 입력 (Injection 시도)** | user_query에 "ignore previous instructions" 포함 | 입력 가드레일 감지 → 요청 거부 + 경고 반환 |

---

### 데이터 특성 요약

| API | 업데이트 주기 | 인증 | Mock 여부 |
|---|---|---|---|
| HackerNews API | 실시간 | 불필요 | ❌ 실제 |
| GitHub REST API | 실시간 | 선택 | ❌ 실제 |
| Reddit API | 실시간 | OAuth2 | ❌ 실제 |
| YouTube Data API v3 | 실시간 | Google API Key | ❌ 실제 |
| iTunes Search API | 실시간 | 불필요 | ❌ 실제 |

---

## 8. 성공 판정 기준

### 체크리스트

1. **[Tool 호출 순서]**  
   요청 유형에 관계없이 trend_scanner가 항상 첫 번째로 호출되는가?  
   → 예 / 아니오

2. **[루프백 동작]**  
   app_existence_checker에서 유사 앱이 발견됐을 때
   concept_generator가 재호출되는가?  
   → 예 / 아니오

3. **[루프 탈출]**  
   concept_generator 재호출이 3회를 초과하기 전에
   루프를 탈출하고 fallback 메시지를 반환하는가?  
   → 예 / 아니오

4. **[메타데이터 포함]**  
   최종 응답에 used_tools, loop_count, failure_type 필드가
   반드시 포함되는가?  
   → 예 / 아니오

5. **[종료 조건 준수]**  
   정상 흐름 기준 max_steps(15) 이내에 브리핑 출력이 완료되는가?  
   → 예 / 아니오

---

## 9. 제약·확장

### 현재 설계의 한계

1. **입력 검증 부재**  
   사용자 자연어 입력에 대한 검증 로직이 없다.
   악의적으로 조작된 입력(프롬프트 인젝션)이 들어올 경우
   에이전트가 의도치 않은 Tool 호출을 수행할 수 있다.

2. **단일 에이전트의 컨텍스트 한계**  
   트렌드 수집 → 컨셉 생성 → 검증 → 난이도 판단을
   하나의 에이전트가 순차적으로 처리하므로,
   트렌드 소스가 늘어날수록 컨텍스트 길이가 폭발적으로 증가한다.

3. **과거 아이디어 비교 불가**  
   현재 설계는 세션 간 메모리가 없다.
   지난주에 동일한 트렌드로 생성된 아이디어와
   오늘 생성된 아이디어를 비교할 수 없다.

---

### Multi-Agent 확장 시 역할 분리 후보

```
Orchestrator
├── Worker A: 트렌드 수집 Agent
│   └── trend_scanner(Reddit, YouTube, HackerNews, GitHub)
│       병렬 수집 후 Orchestrator에 결과 반환
│
└── Worker B: 아이디어 검증 Agent
    └── concept_generator
        → app_existence_checker
        → feasibility_checker 순차 실행
```

**분리 이유:**  
트렌드 수집(Worker A)은 외부 API를 병렬로 호출하는 I/O 집약적 작업이고,
아이디어 검증(Worker B)은 LLM 추론이 집약된 작업이다.
두 역할의 성격이 달라 분리 시 각각 독립적으로 최적화할 수 있다.

---

### 장기 메모리가 필요해지는 시나리오 (7주차 연결)

Nice-to-have로 정의한 "아이디어 진화 추적" 기능을 구현하려면
세션을 넘어서는 장기 메모리가 필요하다.

```
3주 전 → "카피바라 밈 × Rust" 조합으로 CrabPara 컨셉 생성
오늘   → 카피바라 밈이 다시 급상승
          ↓
Agent: "3주 전에 이 트렌드로 생성한 컨셉이 있습니다.
        당시보다 Rust 생태계가 더 성숙했으니
        구현 난이도가 낮아졌을 수 있습니다."
```

**필요한 기술:**
- Vector DB (과거 아이디어 임베딩 저장 및 유사도 검색)
- Redis (세션 간 상태 유지)
- Week 3에서 구축한 ChromaDB 파이프라인 재활용 가능

---

### 보안 확장 포인트 (추후 도입 후보)

1. **입력 가드레일**  
   사용자 입력에 프롬프트 인젝션 패턴 감지 레이어 추가.  
   예: "ignore previous instructions"류 패턴 필터링

2. **PII 필터링**  
   외부 API(Reddit, YouTube) 응답에서 개인 식별 정보(작성자 ID 등)가
   컨텍스트에 그대로 주입되지 않도록 응답 정규화 레이어 도입.

3. **Tool 호출 감사 로그**  
   used_tools 메타데이터를 기반으로 비정상적인 Tool 호출 패턴
   (동일 Tool 과다 호출 등)을 감지하는 모니터링 레이어 추가.

4. **MCP 표준 인터페이스 도입**  
   현재 Tool 4개는 커스텀 함수로 구현되어 있다.
   추후 trend_scanner 소스가 늘어나거나(예: 디스코드, Threads 추가)
   feasibility_checker가 외부 기술 스택 DB와 연동될 경우,
   MCP(Model Context Protocol) 표준 인터페이스로 전환하면
   Tool 추가/교체 시 에이전트 코어 로직 수정 없이 확장이 가능하다.

---

### 구현 프레임워크 후보

현재 설계는 프레임워크 독립적으로 작성되었다.
구현 단계에서는 아래 중 선택한다.

- **LangGraph**: ReAct 루프와 루프백 구조를 노드-엣지 그래프로
  명확하게 표현 가능 → 1순위 후보
- **LangChain**: Tool 래핑과 Agent 실행기 지원.
  LangGraph와 병행 사용 가능
- **MCP**: Tool 수가 늘어날 경우 표준 인터페이스로 전환.
  trend_scanner 소스 추가 시 코어 로직 수정 없이 확장 가능

---