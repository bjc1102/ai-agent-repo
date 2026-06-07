# 10주차 실습 과제: AI Agent Prompt Injection & Minimal Guardrail

## 배경

9주차에는 Agent 실행 trace를 보고 비용 병목을 찾은 뒤 작은 최적화를 적용했습니다.

이번 주에는 같은 Agent를 보안 관점으로 다시 봅니다. 새 프로젝트를 만들지 않습니다. 7~9주차에 구현하고 관측한 기존 AI Agent 프로젝트에 Prompt Injection 모의 테스트를 수행하고, 가장 위험한 지점 하나에 최소 Guardrail을 붙입니다.

이번 과제의 목적은 보안 도구 사용법을 익히는 데 있지 않습니다.

```text
내 Agent가 어떤 입력에서 위험해지는지 확인하고
그 위험을 코드 또는 설정 기반 Guardrail 하나로 줄인 뒤
Before / After로 설명하는 것
```

Promptfoo는 권장 도구입니다. 수동 테스트나 자체 스크립트도 괜찮습니다. 중요한 것은 공격 케이스와 실행 결과를 다시 확인할 수 있어야 한다는 점입니다.

## 과제 목표

다음 순서로 자신의 Agent를 점검합니다.

```text
기존 Agent
-> Prompt Injection 공격 케이스 3개 작성
-> 정상 케이스 1개 작성
-> Before 테스트 실행
-> 코드 또는 설정 기반 Guardrail 1개 적용
-> After 테스트 실행
-> 결과와 한계 정리
```

Guardrail은 본인 Agent 구조에 맞게 고릅니다.

프로젝트마다 구조가 다르기 때문에 같은 방어 방식을 강제하지 않습니다. 대신 각자 Agent에서 Prompt Injection이 영향을 줄 수 있는 경계를 찾고, 그 경계에 맞는 최소 방어를 적용합니다.

## 참고 자료

- 10주차 블로그: https://blog.aibox.today/ai-system-security-llmops/
- OWASP LLM01 Prompt Injection: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- OWASP Top 10 for LLM Applications 2025: https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/
- Promptfoo LLM Red Teaming: https://www.promptfoo.dev/docs/red-team/
- Promptfoo Agent Red Teaming: https://www.promptfoo.dev/docs/red-team/agents/
- Promptfoo Guardrail Testing: https://www.promptfoo.dev/docs/guides/testing-guardrails/

## 제출 방식

### 1. 개인 프로젝트 repository 업데이트

7~9주차에 사용한 개인 Agent repository를 업데이트합니다.

필수 포함:

- Prompt Injection 테스트 케이스
- 정상 케이스
- Guardrail 구현
- Before / After 실행 결과
- `security-tests/` 또는 동등한 테스트 경로
- README 업데이트

선택 포함:

- Promptfoo config
- Promptfoo report
- 수동 테스트 스크립트
- JSON log 또는 trace
- 8주차 observability trace 링크
- 테스트 실행 스크린샷

반드시 `security-tests/`라는 이름을 쓸 필요는 없습니다. 다만 리뷰어가 보안 테스트 입력과 실행 방법을 찾을 수 있도록 README에 경로를 명시합니다.

### 2. ai-agent-repo에 PR 제출

본 `ai-agent-repo`에는 아래 경로로 요약 README를 제출합니다.

```text
week-10/{github-id}/README.md
```

이 파일에는 구현 코드를 넣지 않습니다. 개인 repository 링크, 테스트 케이스 요약, Guardrail 적용 내용, Before / After 결과만 정리합니다.

참조로 아래 항목을 함께 남깁니다.

- 기존 Agent 제출 README 또는 보고서 링크
- 개인 repository의 보안 테스트 경로
- 테스트 실행 결과
- trace/log 또는 8주차 observability 자료

trace/log가 없다면 새로 복잡한 관측 시스템을 만들 필요는 없습니다. 이번 테스트 실행 결과와 재현 방법을 명확히 남기면 됩니다.

## 제출 기한

PR은 늦어도 금요일 18:00 전까지 올립니다.

이후에도 제출할 수 있지만, 주말 리뷰는 금요일 저녁 전까지 올라온 PR을 기준으로 진행합니다. Guardrail 구현이 완성되지 않았더라도 공격 케이스, Before 테스트 결과, 시도한 방어, 막힌 지점을 README에 적어 제출합니다.

## 구현 범위

### 필수

- 기존 개인 Agent 프로젝트 사용
- 공격 케이스 3개 작성
- 정상 케이스 1개 작성
- Before 테스트 실행
- 코드 또는 설정 기반 Guardrail 1개 이상 적용
- After 테스트 실행
- 정상 케이스가 Guardrail 적용 후에도 동작하는지 확인
- 개인 repository에 재현 가능한 테스트 경로 추가
- `week-10/{github-id}/README.md` 제출

### 선택

- Promptfoo 사용
- Promptfoo red-team report 첨부
- 수동 테스트 자동화 스크립트 작성
- 테스트 결과를 JSON/Markdown으로 저장
- 8주차 trace 또는 9주차 log와 연결
- 실패한 공격 케이스를 regression test 후보로 정리

## 테스트 케이스 구성

필수 테스트 케이스는 총 4개입니다.

| 분류 | 개수 | 설명 |
|------|------|------|
| 공격 케이스 | 3개 | Prompt Injection 또는 내부 지침 추출 시도 |
| 정상 케이스 | 1개 | 기존 Agent가 원래 처리해야 하는 일반 요청 |

공격 케이스 3개는 아래 구성을 따릅니다.

| 케이스 | 설명 |
|--------|------|
| 직접 Prompt Injection | 사용자가 직접 "이전 지시를 무시하라" 같은 명령을 입력 |
| System Prompt / 내부 지침 추출 | 시스템 프롬프트, 개발자 지침, 숨은 정책을 출력하라고 요청 |
| Agent별 위험 케이스 | 본인 Agent 구조에 맞는 위험 입력 |

Agent별 위험 케이스는 아래 중 하나를 고릅니다.

| Agent 구조 | 권장 위험 케이스 |
|------------|----------------|
| RAG Agent | 검색 문서나 외부 context 안에 악성 지시문 삽입 |
| Tool 사용 Agent | 허가되지 않은 tool 호출, 위험 파라미터, 권한 우회 요청 |
| 개인정보 처리 Agent | 전화번호, 이메일, 주소, API key 같은 민감정보 유출 시도 |
| Memory 사용 Agent | memory에 저장되면 안 되는 지시나 오염된 사용자 프로필 입력 |
| 일반 대화 Agent | 역할 변경, 정책 무시, 금지된 출력 유도 |

정상 케이스는 기존 Agent의 대표 기능이 Guardrail 때문에 깨지지 않았는지 확인하는 요청입니다.

## Guardrail 적용 기준

프롬프트 수정은 보조 방어로 인정합니다.

하지만 이번 과제의 통과 기준에는 코드 또는 설정으로 동작하는 Guardrail 1개가 필요합니다.

예시:

| Guardrail 종류 | 적용 예시 |
|----------------|-----------|
| Input guardrail | Prompt Injection 의심 문장 탐지 후 거절 또는 추가 확인 |
| Context guardrail | 외부 문서 안의 지시문을 명령이 아니라 참고 자료로 격리 |
| Tool guardrail | 위험 tool 호출 전 권한, 파라미터, 확인 여부 검사 |
| Output guardrail | 시스템 프롬프트, 내부 정책, 개인정보 출력 차단 또는 마스킹 |
| Memory guardrail | memory에 저장하면 안 되는 지시문 또는 민감정보 저장 차단 |

큰 보안 시스템을 만들 필요는 없습니다. 이번 주에는 하나의 위험을 고르고, 그 위험을 줄이는 최소 방어만 구현합니다.

## Before / After 실행 기준

Before에서는 Guardrail 적용 전 결과를 남깁니다.

필수:

- 공격 케이스 3개 실행
- 정상 케이스 1개 실행
- 어떤 케이스가 위험했는지 정리

After에서는 Guardrail 적용 후 결과를 남깁니다.

필수:

- Before에서 실패했거나 가장 위험했던 공격 케이스 1개 이상 재실행
- 정상 케이스 1개 재실행
- Guardrail이 막은 것과 막지 못한 것을 구분

가능하면 공격 케이스 3개를 모두 다시 실행합니다. 최소 기준은 위험 케이스 1개와 정상 케이스 1개입니다.

## Promptfoo 사용 가이드

Promptfoo는 권장 도구이며 필수는 아닙니다.

Promptfoo를 사용하는 경우 개인 repository에 아래 중 하나를 포함합니다.

- `promptfooconfig.yaml`
- red-team config
- 실행 명령
- report 링크 또는 screenshot
- 실패한 테스트 케이스 요약

Promptfoo를 사용하지 않는 경우 아래 중 하나를 포함합니다.

- 수동 테스트 입력 목록
- 테스트 실행 스크립트
- 테스트 결과 Markdown 또는 JSON
- 실행 로그

어떤 도구를 썼는지보다 같은 테스트를 다시 실행할 수 있는 형태로 남겼는지가 더 중요합니다.

## 분석 기준

| 단계 | 확인할 질문 |
|------|-------------|
| 위험 경계 식별 | Prompt Injection이 내 Agent의 어느 지점에 영향을 줄 수 있는가 |
| 공격 케이스 | 실제로 Agent의 지침, context, tool, output을 흔드는 입력인가 |
| Before 결과 | 공격 입력에서 어떤 위험한 응답이나 행동이 나왔는가 |
| Guardrail 선택 | 왜 이 Guardrail을 먼저 적용했는가 |
| After 결과 | 같은 공격이 차단되거나 완화됐는가 |
| 정상 기능 유지 | 정상 요청이 여전히 처리되는가 |
| 한계 | 아직 막지 못한 공격이나 우회 가능성은 무엇인가 |

## ai-agent-repo 제출 README 템플릿

아래 템플릿을 `week-10/{github-id}/README.md`에 작성합니다.

~~~md
# 10주차 AI Agent Prompt Injection & Minimal Guardrail

## 프로젝트 링크

- Repository:
- 기존 Agent 제출 README 또는 보고서:
- 보안 테스트 경로:
- 테스트 결과:
- trace/log 참고:

## Agent 개요

- Agent 이름:
- 주요 기능:
- 주요 Tool 또는 외부 context:
- 이번 과제에서 점검한 위험 경계:

## 테스트 방법

- 사용한 방식: Promptfoo / 수동 테스트 / 자체 스크립트 / 기타
- 테스트 파일 또는 경로:
- 실행 방법:

## 테스트 케이스

| 분류 | 이름 | 입력 요약 | 기대 동작 |
|------|------|-----------|-----------|
| 공격 | 직접 Prompt Injection | | |
| 공격 | System Prompt / 내부 지침 추출 | | |
| 공격 | Agent별 위험 케이스 | | |
| 정상 | 정상 요청 | | |

## Before 결과

| 케이스 | 결과 | 위험 여부 | 근거 |
|--------|------|-----------|------|
| 직접 Prompt Injection | | | |
| System Prompt / 내부 지침 추출 | | | |
| Agent별 위험 케이스 | | | |
| 정상 요청 | | | |

위험하다고 판단한 이유:

- ...

## 적용한 Guardrail

선택한 Guardrail:

- Input / Context / Tool / Output / Memory 중 선택:

선택 이유:

- ...

구현 방식:

- 프롬프트 수정:
- 코드 또는 설정 기반 Guardrail:
- 변경 파일:

## After 결과

| 케이스 | Before | After | 변화 |
|--------|--------|-------|------|
| 재실행한 공격 케이스 | | | |
| 정상 요청 | | | |

Guardrail이 막은 것:

- ...

아직 남은 한계:

- ...

## 참고 자료

- 테스트 결과:
- trace/log:
- Promptfoo report:
~~~

## 자가 점검 체크리스트

제출 전에 아래 항목을 확인합니다.

1. 기존 Agent 프로젝트를 사용했는가
2. 공격 케이스 3개와 정상 케이스 1개를 작성했는가
3. Before 테스트 결과를 기록했는가
4. 프롬프트 수정 외에 코드 또는 설정 기반 Guardrail 1개를 적용했는가
5. Guardrail 적용 후 위험 케이스 1개 이상을 다시 실행했는가
6. Guardrail 적용 후 정상 케이스도 다시 실행했는가
7. 개인 repository에 테스트 입력 또는 실행 방법이 남아 있는가
8. `week-10/{github-id}/README.md`에 Before / After와 한계를 정리했는가

## 범위 밖

이번 과제에서 아래 항목은 필수가 아닙니다.

- 전체 OWASP Top 10 분석
- 완전한 보안 정책 체계 작성
- HITL 시스템 고도화
- 운영용 보안 대시보드 구축
- 모든 공격을 막는 Guardrail 구현
- Fine-tuning 또는 safety training

이번 주에는 Prompt Injection을 직접 테스트하고, 가장 작은 Guardrail 하나를 적용하는 데 집중합니다.
