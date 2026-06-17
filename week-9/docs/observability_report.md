# Observability Report - 9주차 LLM Cost Optimization

## 1. Baseline Trace 선택

### 정상 케이스
- Run ID: `20260527_141502`
- Model: `gemini-3.1-flash-lite`
- Processed files: `3`
- Route counts: `{'llm_review': 3}`
- LLM calls: `3`
- Tool/action result events: `3`
- Total latency: `16128 ms`
- Sum of LLM latency: `15951 ms`
- Sum of tool/action latency: `101 ms`

| Case | Decision | Tool | Completion | LLM ms | Action ms | Total ms |
|---|---:|---:|---:|---:|---:|---:|
| `data\strategy\01_sample_packet_ldap-basic-auth-ev1_strategy.pending.json` | `retry_same_tool` | `noise_cleanup_tool` | `decoded_with_failed_artifacts` | 2537 | 101 | 2649 |
| `data\strategy\04_sample_log4shell-ldaps-port-1399-dsb_strategy.pending.json` | `stop_with_exclusion` | `None` | `partial_excluded` | 1710 | 0 | 1719 |
| `data\strategy\05_sample_log4shell-ldaps-port-443-dsb_strategy.pending.json` | `stop_with_exclusion` | `None` | `partial_excluded` | 11704 | 0 | 11714 |


### 실패/예외 케이스
- Run ID: `20260527_141308`
- Model: `gemini-3.1-flash-lite-preview`
- Processed files: `3`
- Route counts: `{'llm_review': 3}`
- Total latency: `16716 ms`
- Exception: deprecated preview model returned `404 NOT_FOUND` for all 3 LLM review cases.

## 2. 확인 가능한 baseline 항목

| 항목 | 확인 여부 | 값 / 설명 |
|---|---:|---|
| LLM 호출 횟수 | 가능 | 정상 run 기준 3회 |
| Input token | 부분 가능 | provider usage 미저장. `llm_review_prompt` 문자 수를 proxy로 사용 |
| Output token | 부분 가능 | provider usage 미저장. raw response preview/LLM review JSON 길이로만 추정 가능 |
| Latency | 가능 | run log의 `llm_duration_ms`, `action_duration_ms`, `duration_ms` 사용 |
| Tool call | 가능 | action_result 및 recommended_tool 사용 |
| Retrieval context | 해당 없음 | RAG retrieval 대신 strategy preview context 사용 |
| Retry | 부분 가능 | error run에서는 내부 retry 후 `process_file_error`; retry attempt count는 상세 미저장 |

## 3. 비용 병목 분석

가장 큰 비용 병목은 LLM 호출 자체와 LLM에 전달되는 strategy preview payload 크기였다. 특히 ZeroAccess 케이스는 HTTP URI/header/query 값에서 encoded artifact가 다수 추출되면서 `decoded_candidates`, `residue_candidates`, `url_encoded_candidates_preview`가 커졌고, binary-like preview가 LLM prompt에 포함되어 input-side 비용을 키웠다.

## 4. 적용한 최적화

선택한 최적화: `compact strategy preview`

변경 내용:
- preview 후보 중복 제거
- `success_compressed` 후보를 최상단에 우선 배치
- binary/obfuscated decoded preview를 `[BINARY_OR_OBFUSCATED_REDACTED]`로 마스킹
- 긴 raw/decoded preview를 truncate하고 길이/hash만 남김
- 후속 tool 실행용 full raw는 `tool_input_candidates`에 분리 보존

## 5. Before / After 비교

| 항목 | Before | After | 변화 |
|---|---:|---:|---|
| Completion status | `url_encoded_candidate_detected` | `url_encoded_candidate_detected` | 유지 |
| Decoded status | `decode_success_with_residue` | `decode_success_with_residue` | 유지 |
| LLM 호출 횟수 | 1회 예상 | 1회 예상 | 유지 |
| Input token | 약 8908 tokens proxy | 약 3160 tokens proxy | 약 5748 감소 |
| Output token | 측정 불가 | 측정 불가 | usage 미저장 |
| LLM prompt chars | 35634 | 12641 | 22993 chars 감소 |
| decoded_candidates | 161 | 161 | 유지 |
| residue_candidates | 157 | 157 | 유지 |
| url_encoded_candidates | 11 | 3 | 중복 제거 |
| recommended_tool_hint | `url_decode_tool` | `url_decode_tool` | 유지 |
| first preview candidate | `success_binary` / `http_request.uri.path_segment` | `success_compressed` / `http_header.response_line.embedded_url[0].query_param.s` | 중요 후보 우선 정렬 |

## 6. 동작 유지 확인

최적화 후에도 기존 Agent 동작 기준은 유지되었다.

- ZeroAccess strategy는 여전히 `needs_llm_review=true`이다.
- `completion_status=url_encoded_candidate_detected`가 유지되었다.
- `recommended_tool_hint=url_decode_tool`이 유지되었다.
- 단순히 prompt를 줄인 것이 아니라, 후속 tool이 쓸 raw 값은 `tool_input_candidates`에 보존했다.

## 7. 다음 최적화 계획

1. provider `usage` 필드 저장
   - `prompt_tokens`, `completion_tokens`, `total_tokens`를 log에 남긴다.
2. LLM review prompt에 들어가는 tool description 축소
   - 현재 tool spec과 strategy preview가 반복될 수 있으므로 cache 가능한 고정 prefix와 case-specific context를 분리한다.
3. deterministic routing 확대
   - `partial_excluded`처럼 LLM 판단 없이 종료 가능한 케이스는 strategy 단계에서 done 처리하여 LLM 호출을 줄인다.
4. retry attempt count 기록
   - LLM API error의 내부 retry 횟수와 지연 시간을 별도 필드로 남긴다.
