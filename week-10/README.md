# 10주차 실습 과제: AI Security

## 깃 링크
https://github.com/DChanHong/baseball-agent/blob/main/SECURITY_ASSIGNMENT_SUBMISSION.md


## 보안 관련 추가 작업

- Step 1: 사용자 입력 길이, 공백, 제어문자, 명백한 보안 공격 패턴을 Agent 실행 전에 검증하고 차단했다.
- Step 2: 시스템 프롬프트에 `<security>`, `<tool_policy>`, `<rag_policy>` 태그를 추가해 사용자 입력/RAG/Tool observation을 명령이 아닌 데이터로 구분했다.
- Step 3: `session_id`, `user_context`, conversation history를 제한해 세션 상태 위조와 대화 기록 오염 가능성을 낮췄다.
- Step 4: Tool 내부에서 날짜, 시간, 예산, top_k, 팀명, 구장명, seat document 같은 LLM 생성 인자를 재검증했다.
- Step 5: RAG 문서에 출처, 수집 시점, 신뢰 수준, 데이터 한계, 보안 flag metadata를 추가했다.
- Step 6: LangSmith metadata, Tool arguments, observation excerpt에 남을 수 있는 token, email, 전화번호, session 정보 등을 마스킹했다.
- Step 7: 시스템 프롬프트 추출, 개발자 지침 요구, API key 요구, 개인정보 요구, 보안 우회 요청에 대한 일관된 거절 응답 정책을 추가했다.
- Step 8: Promptfoo로 로컬 `/chat` API 보안 거절 테스트를 자동화하고 PASS 결과를 문서화했다.
- Step 9: Lakera Gandalf에서 얻은 공격 아이디어를 JSON 테스트 케이스로 수집하고 Promptfoo 설정을 자동 생성하도록 구성했다.
- Step 10: 최종 보안 완료 체크리스트와 LLM/API 호출 없는 smoke test를 추가하고 UI에서 security metadata를 확인할 수 있게 했다.
