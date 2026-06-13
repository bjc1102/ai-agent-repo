# 9주차 LLM Cost Optimization

## 프로젝트 링크

- Repository: https://github.com/jasonpark112/finance-coach-agent
- 8주차 제출 README: [README2.md](./README2.md)

---

## Baseline Trace

분석 대상으로 삼은 정상 케이스:

```text
입력: "삼성전자 지금 살 만해 최근 뉴스랑 주가 흐름 같이 분석해줘"
run_id: 20260607_155709 / 모델: claude-sonnet-4-6
```

분석 대상으로 삼은 실패 또는 예외 케이스:

```text
입력: "KODEX 국내채권 주가 알려줘"
run_id: 20260607_155803 / 모델: claude-sonnet-4-6
결과: get_stock_price → SYMBOL_NOT_FOUND (ok: false), fallback_occurred: true
```

현재 구조:

- Agent 이름: 개인 재무 코치 Agent
- 주요 Tool: `get_transactions`, `analyze_spending`, `get_stock_price`, `get_news_summary`, `generate_recommendation`
- 사용 모델: claude-sonnet-4-6
- LLM 호출 횟수: step 수와 동일 — 정상 케이스 2회, 실패 케이스 2회
- latency 또는 전체 실행 시간: 정상 19,235ms / 실패 9,331ms
- 확인 가능한 token 사용량:

| 케이스 | input tokens | output tokens | total | 비용 |
|--------|-------------|--------------|-------|------|
| 정상 (삼성전자) | 4,801 | 1,142 | 5,943 | $0.031533 |
| 실패 (KODEX 국내채권) | 4,231 | 433 | 4,664 | $0.019188 |
| 소비 분석 | 16,005 | 3,833 | 19,838 | $0.105510 |
| ETF 투자 추천 | 27,870 | 4,894 | 32,764 | $0.157020 |
| **전체 합계** | **52,907** | **10,302** | **63,209** | **$0.313251** |

---

## 비용 병목 분석

비용이 커진 원인:

- **ETF 투자 추천이 전체 비용의 50%** — 4 steps, 6개 tool 호출로 가장 많은 API 호출 발생
- **매 step마다 전체 messages 히스토리가 input으로 재전송** — ReAct 패턴 특성상 step이 늘수록 input token이 누적 증가
- **output token 단가가 input의 5배** ($3 vs $15/MTok) — output이 적어도 단가 차이로 비용 비중이 큼
- **모델 단가 자체가 높음** — Sonnet 4.6 기준 input $3/MTok, output $15/MTok

근거:

- 4건 baseline 비교 시 step 수와 비용이 비례: 2 steps($0.02~0.03) < 3 steps($0.11) < 4 steps($0.16)
- input token 비중이 전체의 84% (52,907 / 63,209) — output보다 input 절감이 효과적
- 동일한 SYSTEM_PROMPT가 매 step마다 반복 전송되어 불필요한 input token 낭비 발생

---

## 적용한 최적화

선택한 최적화:

1. **모델 교체**: `claude-sonnet-4-6` → `claude-haiku-4-5-20251001`
2. **Prompt Caching 활성화**: `cache_control={"type": "ephemeral"}` 추가

선택 이유:

- 모델 교체: 단가 자체를 낮춰 모든 요청에서 즉각적으로 비용 절감 (input $3→$1, output $15→$5, 약 67% 절감)
- Prompt Caching: SYSTEM_PROMPT가 매 step 동일하게 반복 전송되는 구조에서 step 2부터 cache read($0.10/MTok)로 90% 절감 가능

변경 내용:

```python
# agent_loop.py 변경 사항

# 1. 모델 교체
MODEL_ID = "claude-haiku-4-5-20251001"   # 기존: "claude-sonnet-4-6"

# 2. cache_control 추가
response = client.messages.create(
    model=MODEL_ID,
    max_tokens=8192,
    cache_control={"type": "ephemeral"},  # 추가
    system=SYSTEM_PROMPT,
    ...
)

# 3. 단가 업데이트 (input $1, cache_write $1.25, cache_read $0.10, output $5)
"estimated_cost_usd": round(
    total_input_tokens          * 1    / 1_000_000 +
    total_cache_creation_tokens * 1.25 / 1_000_000 +
    total_cache_read_tokens     * 0.10 / 1_000_000 +
    total_output_tokens         * 5    / 1_000_000,
    6
)
```

---

## Before / After 비교

### 정상 케이스 (삼성전자 분석)

| 항목 | Before (Sonnet) | After (Haiku+Cache) | 변화 |
|------|----------------|---------------------|------|
| LLM 호출 횟수 | 2회 | 2회 | 유지 |
| Input token | 4,801 | 6,745 | +40.5% (토크나이저 차이) |
| Output token | 1,142 | 882 | -22.8% |
| Cache write token | — | 0 | — |
| Cache read token | — | 0 | — |
| Latency | 19,235 ms | 7,697 ms | **-60.0%** |
| Tool 호출 횟수 | 2건 | 2건 | 유지 |
| Retrieval context 수 | 측정 불가 | 측정 불가 | — |
| 비용 | $0.031533 | $0.011155 | **-64.6%** |

> Input token이 증가한 이유: Haiku와 Sonnet은 토크나이저가 달라 같은 텍스트도 token 수가 다르게 계산됨. 단가 절감 효과가 커서 비용은 감소.
> 2 step 쿼리는 캐시 생성·읽기 없음 — step이 적어 캐싱 효과 미발생.

### 실패 케이스 (KODEX 국내채권)

| 항목 | Before (Sonnet) | After (Haiku+Cache) | 변화 |
|------|----------------|---------------------|------|
| LLM 호출 횟수 | 2회 | 2회 | 유지 |
| Input token | 4,231 | 6,195 | +46.5% (토크나이저 차이) |
| Output token | 433 | 229 | -47.1% |
| Cache write token | — | 0 | — |
| Cache read token | — | 0 | — |
| Latency | 9,331 ms | 3,017 ms | **-67.7%** |
| Tool 호출 횟수 | 1건 | 1건 | 유지 |
| Retrieval context 수 | 측정 불가 | 측정 불가 | — |
| 비용 | $0.019188 | $0.007340 | **-61.7%** |

### 전체 4건 집계

| 항목 | Before (Sonnet) | After (Haiku+Cache) | 변화 |
|------|----------------|---------------------|------|
| 총 비용 | $0.313251 | $0.100819 | **-67.8%** |
| 평균 latency | 35,393 ms | 15,871 ms | **-55.2%** |
| Cache write token | — | 22,364 | — |
| Cache read token | — | 44,167 | — |

---

## 동작 유지 확인

6~8주차에서 사용한 성공 기준 중 이번 비교에 사용할 항목:

- 소비 분석 요청 시 `get_transactions` → `analyze_spending` 순서로 호출
- 투자 추천 시 `get_stock_price`, `get_news_summary`, `generate_recommendation` 모두 호출
- Tool 실패 시 fallback 처리 후 정상 답변 생성
- 모든 요청 15 step 이내 종료

최적화 전후에 동일하게 유지된 동작:

- `stop_reason: end_turn` 정상 종료 4건 모두 유지
- 실패 케이스 `fallback_occurred: true` 및 SYMBOL_NOT_FOUND 처리 유지
- 소비 분석 tool 호출 순서 (`get_transactions` → `analyze_spending`) 유지
- 15 step 이내 종료 (최대 6 step)

달라진 동작:

- ETF 투자 추천: steps **4 → 6** 증가, `fallback_occurred: false → true` 발생
- Haiku가 Sonnet 대비 한 번에 판단하는 능력이 낮아 동일 요청에서 더 많은 step 필요
- Output token 감소 → 답변 길이·상세도가 다소 줄어드는 경향

문제가 된다면 되돌릴 변경:

- ETF 추천에서 step 증가 및 fallback이 지속 발생할 경우 `MODEL_ID`를 다시 `claude-sonnet-4-6`으로 복원
- 또는 system prompt에 ETF 추천 시 병렬 호출 명시 지침을 추가해 step 수를 줄이는 방향으로 조정

---

## 다음 최적화 계획

다음에 시도할 최적화:

1. **System Prompt 축소**
   - 현재 SYSTEM_PROMPT에 상세한 지침이 포함되어 매 step input token에 포함됨
   - 핵심 규칙만 남기고 나머지는 tool description에 위임하면 input token 절감 가능

2. **명시적 Prompt Cache 중단점 설정**
   - 현재 자동 캐싱(`cache_control` at request level) 사용 중
   - SYSTEM_PROMPT 블록에 직접 `cache_control: {"type": "ephemeral"}` 명시하면 2 step 쿼리에서도 캐시 발동 가능

3. **max_tokens 축소**
   - 현재 `max_tokens=8192`로 설정되어 있으나 실제 output은 평균 1,000~5,000 token 수준
   - 4,096으로 줄여도 동작에 문제없으며 불필요한 토큰 예비 비용 제거 가능

이유:

- System Prompt 축소는 구현 비용이 낮고 모든 요청에 즉각 반영됨
- 명시적 캐시 중단점은 현재 2 step 단순 쿼리에서 캐싱이 미발동되는 문제를 해소할 수 있음
- 위 두 가지를 적용하면 모델 교체·캐싱에 이어 추가 20~30% 절감 가능할 것으로 예상
