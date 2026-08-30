# 12주차 실습 과제: Fine-tuning 실행과 최종 개선안

## 배경

11주차에는 Fine-tuning에 쓸 작은 데이터셋 초안을 만들었습니다.

12주차에는 이 데이터셋을 실제 Fine-tuning 실험까지 이어 갑니다. 목표는 좋은 모델을 하나 만드는 데 그치지 않습니다. 내가 고른 작업이 Fine-tuning에 맞는지 판단하고, baseline과 비교해 무엇이 나아졌는지 설명하는 데 있습니다.

Fine-tuning은 이런 상황에 잘 맞습니다.

- 반복되는 분류 기준을 안정적으로 맞춰야 할 때
- JSON schema나 응답 형식을 흔들리지 않게 만들고 싶을 때
- 같은 업무 스타일, 말투, 판단 기준을 여러 입력에 일관되게 적용해야 할 때

최신 지식 답변, 문서 기반 질의응답, 긴 문맥 검색은 Fine-tuning보다 RAG나 Prompt Engineering을 먼저 검토합니다.

## 제공 파일

이번 주차에는 아래 파일을 제공합니다.

```text
week-12/README.md
week-12/01_train_sft.ipynb
week-12/02_merge_upload.ipynb
week-12/03_vllm_deploy.ipynb
```

노트북은 RunPod 실행을 기준으로 작성했습니다.

- `01_train_sft.ipynb`: SFT 학습
- `02_merge_upload.ipynb`: LoRA Adapter merge와 Hugging Face 업로드
- `03_vllm_deploy.ipynb`: merged model vLLM 배포

데이터 파일은 저장소에 포함하지 않습니다. AI Hub 원본 데이터와 대량 변환본은 이용정책상 저장소에 올리지 않습니다. 각자 직접 내려받아 사용합니다. 자세한 준비 방법은 `week-12/README.md`를 참고합니다.

- 원본 데이터: https://aihub.or.kr/aihubdata/data/view.do?currMenu=115&dataSetSn=71844&topMenu=100

11주차에 만든 데이터셋이나 직접 만든 합성 데이터셋을 써도 됩니다.

## 과제 목표

본인 Agent나 LLM 서비스에서 Fine-tuning 후보 작업 하나를 고른 뒤, 아래 둘 중 하나를 수행합니다.

| 방식 | 설명 |
|------|------|
| 권장 | `week-12` 노트북을 본인 데이터셋으로 실행 |
| 대체 | GPU, 계정, 시간 문제로 학습을 끝내지 못했다면 Fine-tuning 판단 보고서와 데이터셋 개선안 제출 |

학습을 완료했다면 baseline 모델과 fine-tuned 모델의 결과를 비교합니다.

학습을 끝내지 못했다면 어디서 막혔는지, 어떤 데이터가 더 필요한지, Fine-tuning 대신 RAG나 Prompt Engineering이 더 나은 선택인지 판단합니다.

## 제출 방식

본 `ai-agent-repo`에 아래 경로로 제출합니다.

```text
week-12/{github-id}/README.md
```

Fine-tuning을 실제로 실행했다면 아래 파일을 선택적으로 추가할 수 있습니다.

```text
week-12/{github-id}/data/sample.jsonl
week-12/{github-id}/results/baseline.md
week-12/{github-id}/results/fine_tuned.md
```

원본 dataset, 대량 변환 dataset, 모델 weight, Hugging Face token, RunPod token은 PR에 올리지 않습니다.

## 제출 기한

PR은 늦어도 금요일 18:00 전까지 올립니다.

완성하지 못했더라도 Fine-tuning 후보 판단, 데이터셋 형식, baseline 비교 일부, 막힌 지점을 README에 적어 제출합니다.

## 필수 범위

- Fine-tuning 후보 작업 1개 선정
- Fine-tuning이 필요한 이유 2~3줄 작성
- RAG나 Prompt Engineering으로 충분하지 않은 이유 작성
- 사용 데이터셋의 출처와 라이선스/이용 조건 확인
- 출력 형식 또는 label schema 정의
- baseline 결과 최소 3개 기록
- Fine-tuning 실행 결과 또는 실행 실패 원인 기록
- 최종 개선안 작성
- 개인정보, 내부정보, 라이선스 위험 확인

선택 사항:

- `week-12` 노트북 실행
- train / validation 분리
- 학습 loss 또는 eval loss 기록
- vLLM 배포 후 OpenAI-compatible API 호출 테스트
- 본인 Agent에 적용할 prompt 또는 pipeline 수정안 작성

## Dataset 사용 원칙

데이터 출처는 하나만 골라도 됩니다.

| 방식 | 설명 |
|------|------|
| 11주차 dataset | 본인이 만든 `messages` 기반 JSONL 재사용 |
| AI 합성데이터 | LLM으로 예시를 만들고 직접 검수 |
| Hugging Face dataset | 공개 dataset을 가져와 목적에 맞게 재가공 |
| AI Hub dataset | 각자 신청/다운로드 후 본인 환경에서만 사용 |
| 기존 로그 | 7~10주차 Agent 로그나 실패 trace를 익명화해 재가공 |

AI Hub 데이터를 사용할 때는 원본 파일이나 대량 변환 파일을 PR에 올리지 않습니다. README에는 원본 링크, 사용한 파일명, 변환 규칙, 샘플 5개 이하만 적습니다.

## Fine-tuning 노트북 사용법

`week-12`의 노트북은 기본 실행 흐름을 보여주는 starter입니다.

1. `week-12/README.md`를 읽고 데이터를 준비합니다.
2. `week-12/data/train.jsonl`, `week-12/data/validation.jsonl`을 만듭니다.
3. `week-12` 디렉터리에서 노트북을 실행합니다.
4. `01_train_sft.ipynb`에서 학습을 실행합니다.
5. 가능하면 `02_merge_upload.ipynb`, `03_vllm_deploy.ipynb`까지 실행합니다.

데이터 파일은 직접 준비합니다. 원본 데이터, 대량 변환 데이터, 모델 weight, token은 PR에 올리지 않습니다.

## 비교 기준

가능하면 같은 입력 3~5개로 아래 항목을 비교합니다.

| 항목 | 확인할 것 |
|------|-----------|
| 형식 일관성 | JSON schema나 label 형식을 지키는가 |
| 판단 일관성 | 비슷한 입력에 같은 기준을 적용하는가 |
| 오류 유형 | baseline이 틀린 이유와 fine-tuned 모델이 개선한 이유를 설명할 수 있는가 |
| 비용/복잡도 | Fine-tuning 유지 비용이 prompt/RAG보다 감당 가능한 수준인가 |

정량 지표를 만들 수 있다면 accuracy, exact match, JSON parse success rate 등을 사용합니다. 어렵다면 실패 사례 중심으로 정성 비교를 해도 됩니다.

## README 템플릿

`week-12/{github-id}/README.md`에는 아래 템플릿을 사용합니다.

~~~md
# 12주차 Fine-tuning 실행과 최종 개선안

## Fine-tuning 후보 작업

- 작업 이름:
- 개선하려는 행동:
- Fine-tuning이 필요한 이유:
- RAG나 Prompt Engineering이 먼저가 아닌 이유:

## Dataset

- 데이터 출처:
- 원본 링크:
- 라이선스 또는 이용 조건:
- 학습 row 수:
- 검증 row 수:
- 출력 형식:

## Schema

Assistant 응답 형식:

```json
{
  "category": "string",
  "reply": "string"
}
```

Label 또는 category 정의:

| 값 | 의미 | 판단 기준 |
|----|------|-----------|
| ... | ... | ... |

## 실행 방식

- 사용 모델:
- 학습 환경:
- 실행한 노트북 또는 코드:
- 주요 설정:
- 완료 여부:

## Baseline 비교

| 번호 | 입력 요약 | 기대 출력 | baseline 출력 | 문제점 |
|------|-----------|-----------|---------------|--------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

## Fine-tuning 결과

학습을 실행한 경우:

| 번호 | 입력 요약 | 기대 출력 | fine-tuned 출력 | 개선 여부 |
|------|-----------|-----------|-----------------|-----------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

학습을 완료하지 못한 경우:

- 막힌 지점:
- 원인:
- 다음에 해결할 방법:

## 최종 판단

- Fine-tuning을 계속할 가치가 있는가:
- 더 필요한 데이터:
- Prompt/RAG/Rule 기반 접근과 비교:
- 본인 Agent 또는 LLM 서비스에 적용할 최종 개선안:

## 품질 점검

| 항목 | 확인 결과 |
|------|-----------|
| 출력 형식 일관성 | |
| 판단 기준 일관성 | |
| JSON 파싱 가능 여부 | |
| 개인정보 포함 여부 | |
| 내부정보 포함 여부 | |
| 라이선스 확인 | |
| 원본/대량 데이터 미제출 여부 | |
~~~

## 자가 점검 체크리스트

1. Fine-tuning으로 학습시킬 행동이 한 문장으로 설명되는가
2. baseline과 비교할 입력이 최소 3개 있는가
3. 데이터 출처와 이용 조건을 확인했는가
4. 원본 dataset, token, 모델 weight를 PR에 올리지 않았는가
5. Fine-tuning이 RAG나 Prompt Engineering보다 나은 이유를 설명했는가
