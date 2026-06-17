# Fine-tuning 노트북 사용 안내

## 포함 파일

이 디렉터리에는 Fine-tuning 실습용 노트북 3개가 있습니다.

- `01_train_sft.ipynb`: SFT 학습
- `02_merge_upload.ipynb`: LoRA Adapter merge와 Hugging Face model repo 업로드
- `03_vllm_deploy.ipynb`: merged model vLLM 배포

노트북은 `week-12` 디렉터리에서 실행한다고 가정하고 작성했습니다.

## 데이터 미포함 안내

AI Hub 원본 데이터와 대량 변환 데이터는 저장소에 포함하지 않았습니다.

이번 예시에서 참고한 데이터는 AI Hub의 `민간 민원 상담 LLM 사전학습 및 Instruction Tuning 데이터`입니다.

- 원본 데이터: https://aihub.or.kr/aihubdata/data/view.do?currMenu=115&dataSetSn=71844&topMenu=100
- 데이터 유형: 민간 민원 상담 텍스트
- 라벨링 유형: 분류, 요약, 질의응답

AI Hub 데이터는 이용 조건을 확인한 뒤 각자 직접 신청/다운로드해서 사용해야 합니다. 원본 zip, 원본 json, 대량 변환 jsonl은 PR이나 공개 저장소에 올리지 않습니다.

- AI Hub 데이터 이용정책: https://aihub.or.kr/intrcn/guid/usagepolicy.do

이 정책 때문에 과제 저장소에는 노트북과 데이터 형식 안내만 올립니다. 실제 데이터 파일은 포함하지 않습니다.

## 데이터 준비 방법

노트북은 아래 파일이 있다고 가정합니다.

```text
week-12/data/train.jsonl
week-12/data/validation.jsonl
```

`data/` 디렉터리는 직접 만들어야 합니다.

```bash
mkdir -p week-12/data
```

데이터는 아래 세 가지 중 하나를 사용하면 됩니다.

- 11주차에 만든 `messages` 기반 JSONL
- AI Hub에서 직접 내려받아 변환한 데이터
- 공개 가능한 합성 데이터 또는 익명화한 본인 서비스 로그

## JSONL 형식

노트북은 `system_prompt`, `user_prompt`, `assistant` 컬럼을 읽습니다.

```json
{
  "system_prompt": "너는 민간 민원 상담 데이터를 처리하는 상담 분석 AI다. 사용자의 작업 지시와 상담 내용을 읽고 정답만 간결하게 답한다.",
  "user_prompt": "[작업] 분류\n[세부 유형] 상담 내용\n[지시] 상담 내용은 \"일반 문의 상담\", \"업무 처리 상담\", \"고충 상담\" 중 어떤 거야?\n\n[상담 내용]\n고객: 예약 가능한 객실과 추가 요금을 알고 싶어요.\n상담사: 예약 가능 여부와 요금을 확인해 드리겠습니다.",
  "assistant": "일반 문의 상담"
}
```

노트북 내부에서는 이 세 컬럼을 OpenAI messages 형식으로 바꿔 학습합니다.

```python
def format_data(sample):
    return {
        "messages": [
            {"role": "system", "content": sample["system_prompt"]},
            {"role": "user", "content": sample["user_prompt"]},
            {"role": "assistant", "content": str(sample["assistant"])},
        ],
    }
```

추적이 필요하면 `source`, `source_id`, `task`, `task_category`, `zip_file`, `json_file` 같은 메타데이터 컬럼을 추가해도 됩니다. 노트북은 학습에 필요한 세 컬럼만 사용합니다.

## AI Hub 데이터를 쓰는 경우

AI Hub 데이터는 이미 instruction tuning 형태로 가공되어 있습니다. 별도의 복잡한 전처리보다는, 노트북이 읽는 세 컬럼으로 맞추는 정도면 됩니다.

1. AI Hub에서 `민간 민원 상담 LLM 사전학습 및 Instruction Tuning 데이터`를 신청하고 내려받습니다.
2. 라벨링 데이터에서 `instruction`, `input`, `output`을 읽습니다.
3. `instruction`과 `input`을 합쳐 `user_prompt`로 저장합니다.
4. `output`은 `assistant`로 저장합니다.
5. train/validation을 나누어 `week-12/data/train.jsonl`, `week-12/data/validation.jsonl`로 저장합니다.

변환 규칙은 아래처럼 짧게 정리할 수 있습니다.

```text
system_prompt = 모델 역할과 출력 원칙
user_prompt = 작업 유형 + 세부 유형 + 지시문 + 상담 내용
assistant = 정답 output
```

대량 데이터는 저장소에 올리지 않습니다. README에는 원본 링크와 변환 규칙만 적습니다. 제출용 샘플이 필요하다면 5개 이하만 포함합니다.

## 실행 순서

1. `01_train_sft.ipynb`를 실행해 LoRA adapter를 학습합니다.
2. `02_merge_upload.ipynb`에서 adapter를 base model과 merge하고 Hugging Face에 업로드합니다.
3. `03_vllm_deploy.ipynb`로 merged model을 vLLM에 올립니다.

`03_vllm_deploy.ipynb`의 `MODEL_ID`는 본인이 업로드한 Hugging Face model repo로 바꿔야 합니다.

Hugging Face token은 파일에 적지 말고, 노트북의 login prompt에서 입력합니다.

## 제출 시 주의사항

PR에 올리지 않는 파일은 아래와 같습니다.

- AI Hub 원본 zip
- AI Hub 원본 json
- 대량 변환 jsonl
- 학습된 model weight
- Hugging Face token
- RunPod token
- vLLM 실행 로그
- `.ipynb_checkpoints`
