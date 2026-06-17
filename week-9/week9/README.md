# Personal Agent Repository - 9주차 LLM Cost Optimization Update

## 프로젝트 링크

- Repository: `<개인 Agent Repository URL로 교체>`
- 8주차 제출 README: `<8주차 README URL로 교체>`

## Baseline Trace

분석 대상으로 삼은 정상 케이스:

```text
Run ID: 20260527_141502
Model: gemini-3.1-flash-lite
Processed files: 3
Route counts: {'llm_review': 3}
LLM calls: 3
Total latency: 16128 ms
```

분석 대상으로 삼은 실패 또는 예외 케이스:

```text
Run ID: 20260527_141308
Model: gemini-3.1-flash-lite-preview
Failure: deprecated preview model returned 404 NOT_FOUND.
Processed files: 3
Total latency: 16716 ms
```

현재 구조:

- Agent 이름: Packet Decoding LLM Agent
- 주요 Tool: `noise_cleanup_tool`, `url_decode_tool`, `retry_encoding`
- 사용 모델: `gemini-3.1-flash-lite`
- LLM 호출 횟수: 정상 baseline 기준 3회
- latency 또는 전체 실행 시간: 16128 ms
- 확인 가능한 token 사용량: provider usage metadata 미저장. `llm_review_prompt` 문자 수 기반 proxy 사용

## 비용 병목 분석

비용이 커진 원인:

- LLM 호출 구간이 전체 latency 대부분을 차지했다.
- strategy preview에 긴 encoded/binary 후보가 포함되면서 input-side prompt 크기가 증가했다.
- 같은 HTTP query value가 서로 다른 위치에서 반복 추출되어 preview 중복이 발생했다.

근거:

- 정상 baseline의 총 latency는 16128 ms이고, LLM latency 합은 15951 ms이다.
- ZeroAccess before strategy의 `llm_review_prompt`는 35634 characters였다.
- before 기준 `url_encoded_candidates`는 11개였으며, 중복과 binary preview가 prompt에 포함되었다.

## 적용한 최적화

선택한 최적화:

- compact strategy preview

선택 이유:

- Agent 판단에 필요한 정보는 후보 전체 원문이 아니라 후보 종류, 위치, decode status, residue signal, hash/length 정보다.
- 긴 binary-like decoded preview는 LLM 판단 품질을 높이지 못하면서 input token 비용만 증가시킨다.

변경 내용:

- preview candidate deduplication 적용
- `success_compressed` 후보를 preview 최상단으로 우선 정렬
- binary/obfuscated decoded preview를 redaction 처리
- 긴 raw/decoded preview를 truncate하고 length/hash 기록
- 후속 tool 실행용 원본은 `tool_input_candidates`에 분리 보존

## Before / After 비교

| 항목 | Before | After | 변화 |
|------|--------|-------|------|
| LLM 호출 횟수 | 1회 예상 | 1회 예상 | 유지 |
| Input token | 약 8908 tokens proxy | 약 3160 tokens proxy | 약 5748 감소 |
| Output token | 측정 불가 | 측정 불가 | provider usage 미저장 |
| Latency 또는 전체 실행 시간 | 직접 after run 미측정 | 직접 after run 미측정 | prompt size 감소로 입력 비용 감소 예상 |
| Tool 호출 횟수 | `url_decode_tool` 라우팅 대상 | `url_decode_tool` 라우팅 대상 | 유지 |
| Retrieval context 수 | 해당 없음 | 해당 없음 | strategy preview context 사용 |
| `llm_review_prompt` chars | 35634 | 12641 | 22993 감소 |
| `url_encoded_candidates` | 11 | 3 | 중복 제거 |
| 첫 preview 후보 | `success_binary` | `success_compressed` | 중요 후보 우선 정렬 |

## 동작 유지 확인

6~8주차에서 사용한 성공 기준 중 이번 비교에 사용할 항목:

- pending strategy를 읽고 필요한 경우 LLM review 대상으로 분류한다.
- URL/percent encoded 후보가 있으면 `url_decode_tool` 계열로 라우팅한다.
- TLS encrypted stream은 별도 excluded로 유지한다.
- 후속 tool이 사용할 full raw 후보는 손실하지 않는다.

최적화 전후에 동일하게 유지된 동작:

- `decoded_status=decode_success_with_residue` 유지
- `completion_status=url_encoded_candidate_detected` 유지
- `recommended_tool_hint=url_decode_tool` 유지
- `needs_llm_review=true` 유지

달라진 동작:

- LLM prompt에 들어가는 preview가 줄었다.
- binary-like decoded preview가 redaction 처리되었다.
- `success_compressed` 후보가 첫 preview로 올라왔다.
- 후속 tool용 full raw는 `tool_input_candidates`로 분리되었다.

문제가 된다면 되돌릴 변경:

- full raw를 preview에서 제거한 부분은 되돌릴 필요가 없다. 후속 tool 입력은 별도 보존되기 때문이다.
- 단, 특정 LLM이 redacted preview만으로 판단을 못 한다면 preview limit을 소폭 늘린다.

## 다음 최적화 계획

다음에 시도할 최적화:

- provider usage metadata 저장
- deterministic stop case 확대
- tool description prompt 축소
- retry attempt count 기록

이유:

- 현재 token은 정확 실측값이 아니라 prompt character proxy다.
- `partial_excluded`처럼 규칙으로 종료 가능한 케이스는 LLM 호출 없이 처리할 수 있다.
- tool schema와 routing guidance가 반복되면 input token이 계속 증가한다.
- 실패 케이스에서 retry 횟수와 retry latency를 알아야 비용 병목을 더 정확히 설명할 수 있다.
