# 🍪 오늘의 마음쿠키

중학교 1학년 학생이 아침에 감정 카드 1~2개를 선택하면, 교사가 준비한 문장 풀에서 메시지와 작은 질문/행동을 조합하는 Streamlit 앱입니다. 생성형 AI API는 사용하지 않습니다.

## 파일 구조
- `app.py` — 실행 화면과 메시지 조합 규칙
- `emotions.json` — 감정 121종의 문장 풀 (감정별 4개 유형 × 각 3문장)
- `requirements.txt` — 설치 라이브러리

## GitHub + Streamlit Community Cloud 배포
1. GitHub 저장소의 **최상위 폴더(root)** 에 위 3개 파일을 업로드합니다. ZIP 파일 자체를 업로드하지 마세요.
2. https://share.streamlit.io 에서 GitHub 저장소를 연결합니다.
3. Main file path를 `app.py` 로 지정하고 배포합니다.
4. 수정 시 GitHub에서 **동일한 이름과 위치**로 새 파일을 올리고 기존 파일을 교체(commit)하면 앱이 업데이트됩니다. GitHub와 Streamlit 반영에는 약간의 지연이 발생할 수 있습니다.
5. `emotions.json`만 바꾸면 메시지가, `app.py`를 바꾸면 화면과 기능이 바뀝니다. `requirements.txt`는 라이브러리가 바뀌는 경우에만 수정합니다.

## 기능
- 밝은 마음 51 / 무거운 마음 57 / 여러 빛깔 13 = 121개
- 한 장 선택 121가지, 서로 다른 두 장 선택 7,260가지 = 총 7,381가지(순서 무시)
- 한 장: `acknowledge + perspective`
- 두 장: 첫 감정 `acknowledge` + 연결문 + 둘째 감정 `perspective`
- 아래에는 질문 또는 작은 행동 중 하나가 랜덤으로 나옵니다.
- 선택 내역 및 학생 식별 정보는 저장하지 않습니다.

## 문장 수정
`emotions.json`을 편집할 때 `acknowledge`, `perspective`, `action`, `question`의 문장을 각각 **최소 3개** 유지하세요. 수정 후 같은 파일명으로 GitHub에 교체 업로드하면 됩니다.

## 주의
현재 문장들은 18개 의미군별 안내를 바탕으로 구성된 **초안**입니다. 같은 의미군의 서로 다른 감정에 유사한 문장이 사용됩니다. 학생에게 공개하기 전 교사가 문장별로 최종 검수하는 것을 권장합니다.
