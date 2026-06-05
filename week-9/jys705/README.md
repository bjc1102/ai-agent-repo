# 9주차 실습 과제: LLM Cost Optimization (정연승)

## 프로젝트 링크

- Repository: https://github.com/jys705/mac-idea-agent
- 8주차 제출 README: https://github.com/jys705/aiagent-repo/blob/main/week-8/jys705/README.md

---

## Baseline Trace

### 정상 케이스 (8주차 baseline)

```text
trace_id:         run_20260529_101629_f35152
query:            "오늘 뭐 만들까" (--focus IT)
total_latency_ms: 63,279ms
total_tokens:     27,748
input_tokens:     24,911
output_tokens:    2,837
estimated_cost:   $0.1173
step_count:       7
stop_reason:      final_answer
```

### 실패/예외 케이스 (loop_overflow)

```text
trace_id:         run_20260602_064313_10b9c1
query:            "아무도 안 만든 거 찾아줘" (--exclude-existing)
total_latency_ms: 99,606ms
total_tokens:     49,119
step_count:       19
stop_reason:      loop_overflow
```

### 현재 구조

- Agent 이름: mac-idea-agent (하찮은 맥앱 아이디어 브리핑 에이전트)
- 주요 Tool: trend_scanner, concept_generator, app_existence_checker, feasibility_checker
- 사용 모델: claude-sonnet-4-6 (agent·concept), claude-haiku-4-5-20251001 (feasibility)
- LLM 호출 횟수: 5회 (1회 실행 기준)
- 전체 실행 시간: ~63초
- 토큰 사용량: 27,748 (input 24,911 / output 2,837)

---

## 비용 병목 분석

### 원인 1) messages 누적으로 input token 증가

LangGraph의 ReAct 루프는 매 step마다 이전 messages 전체를 context로 전달한다.
step이 뒤로 갈수록 이전 tool output이 쌓여 input token이 증가한다.

```
step 1: trend_scanner         input 3,393
step 2: concept_generator     input 4,206  (+813)
step 4: app_existence_checker input 5,065  (+859)
step 6: feasibility_checker   input 5,793  (+728)
```

tool output에 포함된 `source_provenance` (endpoint, fetched_at, items_returned 등)는
LLM 판단에 불필요한 Observability 메타데이터이지만 매 step마다 누적된다.

### 원인 2) system_prompt 반복 비용

system_prompt(1,532 tokens)가 5회 LLM 호출마다 전달된다.
8주차 baseline에서 `cache_read_input_tokens: 0` — 캐싱 미적용 상태.

```
system_prompt 반복 비용: 1,532 × 5 = 7,660 tokens → 전체의 약 28%
```

---

## 적용한 최적화

### 최적화 ①: Tool result 축소 (tool result budget)

**선택 이유**: 멘토님의 "tool result 전체 JSON을 그대로 observation에 넣는 것이 나쁜 방식" 참고.
source_provenance는 Observability용이며 LLM 판단에 불필요하다.

**변경 내용**: `agent.py`에 `_slim_tool_observations()` 추가.
LLM 호출 전 ToolMessage에서 `source_provenance`를 제거한다.
`accumulated_messages`(원본)에는 보존되어 trace 무결성 유지.

```python
def _slim_tool_observations(messages: list) -> list:
    for msg in messages:
        if isinstance(msg, ToolMessage):
            content = json.loads(msg.content)
            slim_data = {k: v for k, v in content["data"].items()
                        if k != "source_provenance"}
            # slim 버전만 LLM에 전달
```

### 최적화 ②: Prompt Caching

**선택 이유**: system_prompt 1,532 tokens가 5회 반복. 하나의 실행 내 5회 LLM 호출이
5분 TTL 안에 발생하므로 caching 조건 충족.
8주차 baseline에서 `cache_read_input_tokens: 0` 미적용 상태였음.

**변경 내용**: `_build_prompt()`에서 SystemMessage를 content block 형식으로 교체,
`cache_control: ephemeral` 추가.

```python
SystemMessage(content=[{
    "type": "text",
    "text": SYSTEM_PROMPT,
    "cache_control": {"type": "ephemeral"}   # ← 추가
}])
```

**캐싱 효과**: 1회 실행 내 call 1이 write, call 2~5가 read (0.1x 비용).
별도 실행 간(5분 이상 간격)에는 TTL 만료로 재write 발생 — 매일 한 번 실행하는
CLI 도구 특성상 하나의 실행 내 5회 호출에서만 유효.

---

## Before / After 비교

| 항목 | Before (8주차) | After ① tool result 축소 | After ② + prompt caching |
|------|----------------|--------------------------|--------------------------|
| total_tokens | 27,748 | 26,119 | **25,419** |
| input_tokens | 24,911 | 23,552 | 23,636 |
| output_tokens | 2,837 | 2,567 | 2,309 |
| cache_read_tokens | 0 | 0 | **14,557** |
| estimated_cost | $0.1173 | $0.1092 | **$0.0946** |
| total_latency_ms | 63,279ms | 52,601ms | 59,365ms |
| LLM 호출 횟수 | 5회 | 5회 | 5회 |
| Tool 호출 횟수 | 7회 | 7회 | 7회 |
| stop_reason | final_answer | final_answer | final_answer |

### step별 input token 변화 (Before vs After ①)

| Step | Tool | Before | After ① | 절감 |
|------|------|--------|---------|------|
| 1 | trend_scanner | 3,393 | 3,462 | +69 (헤드라인 길이 차이) |
| 2 | concept_generator | 4,206 | 4,104 | **-102** |
| 3 | concept_generator | 4,206 | 4,104 | **-102** |
| 4 | app_existence_checker | 5,065 | 4,817 | **-248** |
| 5 | app_existence_checker | 5,065 | 4,817 | **-248** |
| 6 | feasibility_checker | 5,793 | 5,292 | **-501** |
| 7 | feasibility_checker | 5,793 | 5,292 | **-501** |

step이 뒤로 갈수록 절감 폭이 커지는 패턴: source_provenance 누적 제거 효과.

### 누적 절감 요약

```
① tool result 축소:   -1,629 tokens (-5.9%) / -$0.0081 (-6.9%)
② + prompt caching:   -2,329 tokens (-8.4%) / -$0.0227 (-19.4%)
```

---

## 동작 유지 확인

6~8주차 성공 기준과 비교:

| 항목 | Before | After | 유지 여부 |
|------|--------|-------|-----------|
| Tool 4개 정상 호출 | ✅ | ✅ | ✅ |
| Tool 호출 순서 (design §4 WORKFLOW) | ✅ | ✅ | ✅ |
| today_brief + metadata 구조 | ✅ | ✅ | ✅ |
| stop_reason: final_answer | ✅ | ✅ | ✅ |
| source_provenance trace 보존 | ✅ | ✅ (원본 유지) | ✅ |
| guardrail 차단 | ✅ | ✅ | ✅ |
| loop_overflow fallback | ✅ | ✅ | ✅ |

**달라진 동작**: 없음. Agent 출력 품질, 흐름, 종료 조건 모두 동일하게 유지됨.

---

## 다음 최적화 계획

| 후보 | 예상 효과 | 이유 |
|------|-----------|------|
| **History trimming** | input token 추가 감소 | step이 많아질수록 오래된 messages 제거로 누적 억제 가능 |
| **loop_overflow 케이스 token 절감** | 49,119 → 대폭 감소 | 현재 recursion_limit 발동 전 loop_count 카운터 주입으로 불필요한 반복 차단 가능 |
| **concept_generator model routing** | output token 비용 감소 | haiku로 교체 후 컨셉 품질 비교 필요 (품질-비용 트레이드오프 확인 필요) |

history trimming이 다음 순서인 이유: loop_overflow 케이스(49,119 tokens)가 정상 케이스(27,748 tokens)의 1.8배이며, messages 누적을 step 기준으로 trim하면 loop 내 반복 비용을 추가로 줄일 수 있음.