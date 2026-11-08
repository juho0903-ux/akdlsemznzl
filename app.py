"""오늘의 마음쿠키 | Streamlit + Google Sheets.
GitHub에서 같은 이름의 파일로 교체하면 자동 배포됩니다.
"""
import base64
from datetime import datetime
from html import escape
import json
from pathlib import Path
import random
import time
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

st.set_page_config(page_title="오늘의 마음쿠키 🍪", page_icon="🍪", layout="centered")
ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "emotions.json").read_text(encoding="utf-8"))["emotions"]
BY_NAME = {emotion["name"]: emotion for emotion in DATA}
STUDENTS = [
    "강태영", "김도건", "김민준", "김선우", "김유민", "김이수", "김효준",
    "민이엘", "박주혁", "변나린", "성서준", "신서현", "양하늘", "오다윤",
    "유명산", "이동현", "이수아", "이시아", "이유준", "이채훈", "장예서",
    "정아현", "정찬호", "조예린", "최서우", "피시윤", "홍라희", "장예준",
]
STUDENT_OPTIONS = [f"{i}. {name}" for i, name in enumerate(STUDENTS, 1)]
TABS = {"positive": "☀️ 밝은 마음", "negative": "🌧️ 무거운 마음", "mixed": "🌈 여러 빛깔의 마음"}
HEADERS = ["제출 시각(한국)", "번호", "이름", "감정 1", "감정 2", "담임에게 보내는 말", "마음쿠키 메시지", "추가 활동 유형", "추가 활동 내용"]

# 기존 감정 데이터와 메시지 생성 방식을 유지합니다.
POSITIVE_CLOSINGS = [
    "그 좋은 기운이 오늘 하루에도 오래 이어지길 바라!",
    "오늘의 밝은 마음이 너의 하루를 환하게 밝혀 주면 좋겠어.",
    "이 기분을 마음껏 느끼면서 오늘도 네 속도로 즐겁게 보내길 바라!",
    "지금의 좋은 에너지가 오늘의 작은 순간들에도 함께하길 바라!",
    "그 기분 좋은 마음을 안고 오늘 하루를 시작해 보자!",
]
LOW_CLOSINGS = [
    "오늘은 마음을 너무 서두르지 않고, 네게 필요한 시간을 조금 내어 주면 좋겠어.",
    "혼자 해결하기 어려운 마음이라면 믿을 만한 어른에게 말해도 좋아.",
    "모든 답을 오늘 다 찾으려고 하지 않아도 돼. 작은 한 걸음이면 충분해.",
    "네 마음을 소중하게 여기면서 오늘 하루를 보내길 바라.",
]
MIXED_CLOSINGS = [
    "기대되는 건 기대되는 대로, 걱정되는 건 걱정되는 대로 살펴봐도 좋아.",
    "어느 한쪽 마음을 억지로 지울 필요는 없어. 두 마음 모두 지금의 네 마음이니까.",
    "조금 떨리더라도 네 속도로 오늘을 시작해 보길 바라.",
]


def tone(item):
    if item["category"] == "positive":
        return "bright"
    if item["category"] == "negative" or item["family"] in {"걱정", "당황", "멍함"}:
        return "heavy"
    return "bright"


def make_message(selected):
    """학생의 마음을 먼저 받아 주고, 그날에 어울리는 응원을 건넵니다."""
    chosen = [BY_NAME[name] for name in selected]
    first = chosen[0]
    if len(chosen) == 1:
        mood = tone(first)
        opening = random.choice(first["acknowledge"])
        # acknowledgement와 perspective의 같은 문장이 연달아 나오지 않게 합니다.
        perspectives = [p for p in first["perspective"] if p != opening]
        middle = random.choice(perspectives or first["perspective"])
        closing = random.choice(POSITIVE_CLOSINGS if mood == "bright" else LOW_CLOSINGS)
        main = [opening, middle, closing]
    else:
        second = chosen[1]
        a, b = tone(first), tone(second)
        if a == b == "bright":
            if set(selected) == {"든든한", "쾌활한"}:
                main = [
                    "오늘은 어떤 좋은 일이 있어서 이렇게 든든하고 쾌활한 마음이 들었을까?",
                    "마음이 든든하면 새로운 일을 시작할 힘이 생기고, 밝은 기운은 발걸음을 더 가볍게 해 주지.",
                    "오늘도 네 하루에 기분 좋은 일이 가득하길 바라. 아침의 밝은 에너지가 하루 종일 함께하길!",
                ]
            else:
                main = [
                    random.choice([
                        "오늘 아침엔 마음속에 좋은 기운이 함께하고 있나 봐!",
                        "오늘은 마음이 한결 환해지는 아침인가 봐.",
                        "기분 좋은 마음이 둘이나 찾아온 오늘이네!",
                    ]),
                    random.choice([
                        "지금 느끼는 기분을 서둘러 지나치지 말고, 잠깐 마음껏 누려 봐.",
                        "무슨 일이 이런 기분을 만들어 줬는지 떠올려 보는 것도 즐겁겠다.",
                        "작은 순간에서 찾은 기쁨도 충분히 소중해.",
                    ]),
                    random.choice(POSITIVE_CLOSINGS),
                ]
        elif a == b == "heavy":
            if set(selected) == {"서운한", "화나는"}:
                main = [
                    "기대했던 마음이 있어서 서운했는데, 화까지 났다면 마음이 더 복잡했겠어.",
                    "무엇이 가장 서운했는지, 어떤 점에서 화가 났는지 천천히 살펴봐도 좋아.",
                    "지금 바로 해결하려 애쓰지 말고, 네 마음을 차근차근 정리해 보자.",
                ]
            else:
                main = [
                    random.choice([
                        "마음이 여러모로 무거운 아침일 수도 있겠구나.",
                        "한 가지로 설명하기 어려운 마음이 함께 찾아왔나 봐.",
                        "이런 마음이 겹치는 날에는 평소보다 더 지치게 느껴질 수도 있어.",
                    ]),
                    random.choice([
                        "그중 무엇이 가장 마음에 걸리는지 하나만 살펴봐도 좋아.",
                        "지금 느끼는 감정을 서둘러 바꾸거나 숨기지 않아도 돼.",
                        "무슨 일이 있었는지 당장 설명하기 어렵다면, 천천히 생각해 봐도 좋아.",
                    ]),
                    random.choice(LOW_CLOSINGS),
                ]
        else:
            if set(selected) == {"기대되는", "긴장되는"}:
                main = [
                    "기대되는 일이 있으면서도 잘하고 싶은 마음에 긴장될 수 있지.",
                    "두근거리는 기대와 조심스러운 긴장이 함께하는 건 자연스러운 일이야.",
                    "완벽하게 하려고 애쓰기보다 네가 준비한 만큼 한 걸음씩 해 보길 바라!",
                ]
            else:
                main = [
                    random.choice([
                        "기분 좋은 마음과 조금 무거운 마음이 함께 찾아왔나 봐.",
                        "서로 다른 마음이 한꺼번에 들 때도 있지.",
                        "오늘은 마음이 한 가지 색으로만 느껴지지 않는구나.",
                    ]),
                    random.choice([
                        "어느 쪽이 진짜 마음인지 하나만 고를 필요는 없어.",
                        "좋은 점도, 마음에 걸리는 점도 모두 천천히 바라봐도 좋아.",
                        "지금 더 크게 느껴지는 마음이 무엇인지 살펴보는 것도 좋겠어.",
                    ]),
                    random.choice(MIXED_CLOSINGS),
                ]
    extra_type = random.choice(["question", "action"])
    extra = random.choice(random.choice(chosen)[extra_type])
    return "\n\n".join(main), extra_type, extra


def sheet_is_configured():
    try:
        return bool(st.secrets.get("spreadsheet_id") and st.secrets.get("gcp_service_account"))
    except (FileNotFoundError, KeyError):
        return False


def get_sheet():
    creds_info = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"],
    )
    client = gspread.authorize(credentials)
    book = client.open_by_key(st.secrets["spreadsheet_id"])
    try:
        sheet = book.worksheet("마음기록")
    except gspread.WorksheetNotFound:
        sheet = book.add_worksheet(title="마음기록", rows=1500, cols=len(HEADERS))
    if sheet.row_values(1) != HEADERS:
        if sheet.row_values(1):
            raise RuntimeError("'마음기록' 시트의 첫 줄 제목이 예상과 다릅니다. 데이터를 덮어쓰지 않기 위해 기록을 중단했습니다.")
        sheet.update("A1:I1", [HEADERS])
        sheet.freeze(rows=1)
    return sheet


def safe_cell(text):
    # Google Sheets 수식 주입 방지: 외부 입력을 텍스트로 취급
    value = str(text or "")
    if value.lstrip().startswith(("=", "+", "-", "@")):
        value = "'" + value
    return value


def save_submission(number, name, selected, message_to_teacher, result):
    main, extra_type, extra = result
    row = [
        datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S"),
        number, name, selected[0], selected[1] if len(selected) > 1 else "",
        safe_cell(message_to_teacher), main, "마음 질문" if extra_type == "question" else "작은 한 걸음", extra,
    ]
    get_sheet().append_row(row, value_input_option="RAW", insert_data_option="INSERT_ROWS")



# ── 감정별 문화 콘텐츠: 파일 교체만으로 적용할 수 있도록 앱 안에 내장 ──
RECOMMENDATIONS = [{'kind': '창작',
  'tags': ['불안', '기대'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '잘하고 싶은 마음이 크면 걱정도 커질 수 있어요. 오늘은 할 수 있는 한 가지만 해 봐요.',
  'question': '지금 할 수 있는 일 하나를 적어 볼까요?'},
 {'kind': '창작',
  'tags': ['슬픔', '속상함'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '마음이 무거운 날에는 꼭 밝은 얼굴을 하지 않아도 괜찮아요.',
  'question': '지금 내 마음에 가장 가까운 단어는 뭘까요?'},
 {'kind': '창작',
  'tags': ['화남', '답답함'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '화가 났다는 건 내게 중요한 무언가가 건드려졌다는 신호일 수 있어요.',
  'question': '무엇이 나를 화나게 했는지 한 문장으로 적어 봐요.'},
 {'kind': '창작',
  'tags': ['외로움', '그리움'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '누군가가 그리운 날에는 그 사람이 내게 남긴 다정함을 떠올려 봐요.',
  'question': '떠오르는 사람에게 안부를 전해 볼까요?'},
 {'kind': '창작',
  'tags': ['기쁨', '감사'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '오늘의 기쁨이 작아 보여도, 작아서 덜 소중한 건 아니에요.',
  'question': '좋았던 순간 하나를 이름 붙여 봐요.'},
 {'kind': '창작',
  'tags': ['두려움', '불안'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '무섭다는 마음과 해 보려는 마음은 함께 있을 수 있어요.',
  'question': '조금 덜 무섭게 만드는 준비 하나는?'},
 {'kind': '창작',
  'tags': ['후회', '속상함'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '어제의 선택을 다시 할 수는 없지만, 오늘의 선택은 아직 남아 있어요.',
  'question': '다음에는 다르게 해 보고 싶은 것은?'},
 {'kind': '창작',
  'tags': ['지침', '답답함'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '쉬는 시간은 뒤처지는 시간이 아니라 다시 움직일 힘을 모으는 시간이에요.',
  'question': '5분 동안 무엇을 쉬어 볼까요?'},
 {'kind': '창작',
  'tags': ['자신감', '설렘'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '잘할 수 있을지 몰라도 시작할 수는 있어요. 시작은 이미 작은 용기예요.',
  'question': '오늘 시작할 일의 첫걸음은?'},
 {'kind': '창작',
  'tags': ['부끄러움', '불안'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '실수 한 번으로 나라는 사람이 전부 설명되지는 않아요.',
  'question': '친구가 같은 실수를 했다면 뭐라고 말할까요?'},
 {'kind': '창작',
  'tags': ['평온', '감사'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '별일 없는 하루에도 조용히 고마운 순간이 숨어 있어요.',
  'question': '오늘 편안했던 순간은 언제였나요?'},
 {'kind': '창작',
  'tags': ['슬픔', '그리움'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '그리운 마음을 빨리 정리해야 할 숙제처럼 여기지 않아도 돼요.',
  'question': '그 마음에 색을 붙이면 무슨 색일까요?'},
 {'kind': '창작',
  'tags': ['화남', '속상함'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '지금 바로 대답하지 않는 것도 나를 지키는 방법이 될 수 있어요.',
  'question': '말하기 전에 숨을 세 번 쉬어 볼까요?'},
 {'kind': '창작',
  'tags': ['답답함', '지침'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '한꺼번에 모든 문제를 해결하지 않아도 오늘은 충분히 지나갈 수 있어요.',
  'question': '가장 먼저 덜어낼 일 하나는?'},
 {'kind': '창작',
  'tags': ['기쁨', '설렘'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '좋은 일이 생기면 마음껏 좋아해도 돼요. 기쁨을 작게 만들 필요는 없어요.',
  'question': '이 기쁨을 누구와 나누고 싶나요?'},
 {'kind': '창작',
  'tags': ['외로움', '슬픔'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '혼자 있는 시간과 혼자라고 느끼는 시간은 서로 다를 수 있어요.',
  'question': '지금 연락하고 싶은 사람이 있나요?'},
 {'kind': '창작',
  'tags': ['두려움', '자신감'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '용기는 겁이 없는 모습보다 겁이 나도 나아가는 모습에 가까워요.',
  'question': '오늘의 아주 작은 도전은?'},
 {'kind': '창작',
  'tags': ['후회', '부끄러움'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '미안한 마음이 든다면 다음 행동으로 그 마음을 전할 수 있어요.',
  'question': '어떤 말이나 행동을 바꾸면 좋을까요?'},
 {'kind': '창작',
  'tags': ['지침', '평온'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '오늘의 속도가 느린 것은 오늘의 속도가 느리다는 뜻일 뿐이에요.',
  'question': '지금 몸이 보내는 신호를 느껴 봐요.'},
 {'kind': '창작',
  'tags': ['감사', '기쁨'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '익숙한 사람의 작은 친절은 생각보다 오래 마음에 남아요.',
  'question': '오늘 누군가에게 고마웠던 일은?'},
 {'kind': '창작',
  'tags': ['불안', '답답함'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '모르는 일이 많을 때는 답을 찾기보다 질문 하나를 정하는 게 도움이 돼요.',
  'question': '내가 정말 알고 싶은 것은 무엇인가요?'},
 {'kind': '창작',
  'tags': ['화남', '후회'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '화를 느끼는 것과 화난 대로 행동하는 것은 다른 일이에요.',
  'question': '내 마음을 해치지 않고 전할 문장은?'},
 {'kind': '창작',
  'tags': ['속상함', '외로움'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '서운하다는 마음에는 알아주었으면 하는 바람이 들어 있을 때가 있어요.',
  'question': '상대가 알아주었으면 하는 점은?'},
 {'kind': '창작',
  'tags': ['설렘', '두려움'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '처음이라 떨리는 건 이상한 일이 아니에요. 낯선 순간은 누구에게나 낯설어요.',
  'question': '내가 기대하는 한 가지는?'},
 {'kind': '창작',
  'tags': ['자신감', '감사'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '지금까지 해 온 노력은 당장 보이지 않아도 사라진 것이 아니에요.',
  'question': '내가 해낸 작은 일 세 가지는?'},
 {'kind': '창작',
  'tags': ['평온', '지침'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '잠깐 창밖을 보는 일도 마음의 쉼표가 될 수 있어요.',
  'question': '지금 창밖에는 무엇이 보이나요?'},
 {'kind': '창작',
  'tags': ['그리움', '감사'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '보고 싶은 사람이 있다는 건 함께한 시간이 내게 의미 있었다는 뜻일 수 있어요.',
  'question': '그 사람과 가장 기억나는 순간은?'},
 {'kind': '창작',
  'tags': ['부끄러움', '자신감'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '다른 사람의 시선보다 내가 무엇을 배웠는지 먼저 살펴봐요.',
  'question': '이번 일에서 배운 것은?'},
 {'kind': '창작',
  'tags': ['슬픔', '평온'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '눈물이 날 때는 마음이 잠시 자기 방식으로 이야기하는 중일지도 몰라요.',
  'question': '조금 편안해지는 장소는 어디인가요?'},
 {'kind': '창작',
  'tags': ['기쁨', '자신감'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '잘된 일을 운이라고만 넘기지 말고 내 몫의 노력도 찾아봐요.',
  'question': '내가 기여한 부분은 무엇이었나요?'},
 {'kind': '창작',
  'tags': ['불안', '지침'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '걱정이 많아질수록 생각과 사실을 나누어 보는 게 도움이 돼요.',
  'question': '확실한 사실 한 가지는 무엇인가요?'},
 {'kind': '창작',
  'tags': ['외로움', '평온'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '잠시 혼자인 날에도 나를 즐겁게 하는 일 하나쯤은 곁에 둘 수 있어요.',
  'question': '혼자서도 좋아하는 것은?'},
 {'kind': '창작',
  'tags': ['답답함', '두려움'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '갈 길이 잘 보이지 않을 때는 발밑의 한 걸음부터 확인해 봐요.',
  'question': '오늘 내가 선택할 수 있는 일은?'},
 {'kind': '창작',
  'tags': ['속상함', '후회'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '원하는 결과가 아니었다고 해서 그동안의 시간이 전부 헛된 건 아니에요.',
  'question': '과정에서 얻은 것은 무엇인가요?'},
 {'kind': '창작',
  'tags': ['감사', '그리움'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '고마운 마음은 늦게 알아차려도 여전히 고마운 마음이에요.',
  'question': '전하고 싶은 고마운 한마디는?'},
 {'kind': '창작',
  'tags': ['화남', '평온'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '마음을 가라앉힌 다음 이야기해도 내 의견의 중요함은 줄어들지 않아요.',
  'question': '조금 진정된 뒤 어떤 말을 하고 싶나요?'},
 {'kind': '창작',
  'tags': ['설렘', '기쁨'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '기다리는 일이 있다는 것만으로도 하루는 조금 달라 보여요.',
  'question': '무엇이 가장 기대되나요?'},
 {'kind': '창작',
  'tags': ['부끄러움', '슬픔'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '누구나 보여 주고 싶지 않은 순간이 있어요. 그 순간도 내 이야기의 일부예요.',
  'question': '오늘 나에게 다정한 말 한마디는?'},
 {'kind': '창작',
  'tags': ['자신감', '후회'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '지난번에 잘 안됐더라도 이번에 시도할 방법은 새로 고를 수 있어요.',
  'question': '이번에는 무엇을 달리 해 볼까요?'},
 {'kind': '창작',
  'tags': ['평온', '기쁨'],
  'title': '마음쿠키 창작 문장',
  'author': '오늘의 마음쿠키',
  'description': '좋은 하루를 특별하게 만드는 것은 큰 사건보다 알아차리는 마음일지도 몰라요.',
  'question': '오늘 마음에 남겨 둘 장면은?'},
 {'kind': '노래',
  'tags': ['감사', '평온'],
  'title': '마음',
  'author': '아이유',
  'description': '마음속에 있는 다정함을 떠올리고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['그리움', '설렘'],
  'title': '밤편지',
  'author': '아이유',
  'description': '직접 말하기 어려운 마음을 조용히 떠올릴 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['슬픔', '외로움'],
  'title': 'Love poem',
  'author': '아이유',
  'description': '누군가의 곁에 있어 주는 마음을 생각할 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['자신감', '부끄러움'],
  'title': '팔레트',
  'author': '아이유',
  'description': '지금의 나를 알아 가는 과정에 어울리는 노래',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['그리움', '슬픔'],
  'title': '에잇',
  'author': '아이유',
  'description': '지나간 시간을 돌아보고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['지침', '속상함'],
  'title': '수고했어, 오늘도',
  'author': '옥상달빛',
  'description': '열심히 보낸 하루의 끝에 스스로를 다독일 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['자신감', '부끄러움'],
  'title': '없는게 메리트',
  'author': '옥상달빛',
  'description': '나만의 모습을 새롭게 바라보고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['불안', '지침'],
  'title': '걱정말아요 그대',
  'author': '이적',
  'description': '걱정이 너무 커진 날 잠시 쉬어 가고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['감사', '기쁨'],
  'title': '다행이다',
  'author': '이적',
  'description': '소중한 사람에게 감사한 마음이 생길 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['자신감', '설렘'],
  'title': '하늘을 달리다',
  'author': '이적',
  'description': '가슴이 벅차는 에너지가 필요할 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['설렘', '답답함'],
  'title': '여행',
  'author': '볼빨간사춘기',
  'description': '일상에서 잠깐 벗어나고 싶은 마음이 들 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['설렘', '기쁨'],
  'title': '우주를 줄게',
  'author': '볼빨간사춘기',
  'description': '누군가를 향한 좋은 감정이 자라날 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['그리움', '슬픔'],
  'title': '오랜 날 오랜 밤',
  'author': 'AKMU',
  'description': '지나간 관계를 떠올릴 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['지침', '답답함'],
  'title': '후라이의 꿈',
  'author': 'AKMU',
  'description': '정해진 길이 답답하게 느껴지는 날',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['두려움', '불안'],
  'title': 'DINOSAUR',
  'author': 'AKMU',
  'description': '낯선 두려움을 음악으로 풀어 보고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['그리움', '평온'],
  'title': '11:11',
  'author': '태연',
  'description': '조용한 밤, 오래된 기억을 떠올릴 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['후회', '그리움'],
  'title': '사계',
  'author': '태연',
  'description': '달라진 마음과 계절을 돌아볼 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['자신감', '설렘'],
  'title': 'I',
  'author': '태연',
  'description': '새로운 시작을 응원하고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['그리움', '외로움'],
  'title': '봄날',
  'author': 'BTS',
  'description': '보고 싶은 사람을 떠올리는 날',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['자신감', '부끄러움'],
  'title': 'Answer : Love Myself',
  'author': 'BTS',
  'description': '스스로를 조금 더 따뜻하게 바라보고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['외로움', '감사'],
  'title': 'Mikrokosmos',
  'author': 'BTS',
  'description': '서로 다른 사람들의 존재를 소중히 느끼고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['기쁨', '설렘'],
  'title': '아주 NICE',
  'author': '세븐틴',
  'description': '신나는 마음을 마음껏 표현하고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['불안', '자신감'],
  'title': '같이 가요',
  'author': '세븐틴',
  'description': '앞날이 걱정될 때 함께 걷는 마음을 떠올리고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['설렘', '자신감'],
  'title': '한 페이지가 될 수 있게',
  'author': 'DAY6',
  'description': '새로운 추억과 도전을 기대하는 날',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['그리움', '슬픔'],
  'title': '예뻤어',
  'author': 'DAY6',
  'description': '지난 추억이 또렷하게 떠오를 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['감사', '그리움'],
  'title': '행복했던 날들이었다',
  'author': 'DAY6',
  'description': '좋았던 시간을 고마운 마음으로 돌아볼 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['두려움', '설렘'],
  'title': '주저하는 연인들을 위해',
  'author': '잔나비',
  'description': '망설임과 설렘이 함께 찾아올 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['설렘', '기쁨'],
  'title': '폰서트',
  'author': '10CM',
  'description': '소박한 다정함이 떠오를 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['감사', '그리움'],
  'title': '모든 날, 모든 순간',
  'author': '폴킴',
  'description': '평범한 하루를 특별하게 기억하고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '노래',
  'tags': ['후회', '자신감'],
  'title': '사건의 지평선',
  'author': '윤하',
  'description': '끝과 시작이 이어지는 순간을 생각하고 싶을 때',
  'question': '이 노래를 듣고 떠오른 기분은?'},
 {'kind': '시',
  'tags': ['외로움', '평온'],
  'title': '산유화',
  'author': '김소월',
  'description': '산에는 꽃 피네 / 꽃이 피네',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['슬픔', '그리움'],
  'title': '진달래꽃',
  'author': '김소월',
  'description': '이별을 마주하는 화자의 마음을 생각해 볼 수 있어요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['그리움', '슬픔'],
  'title': '초혼',
  'author': '김소월',
  'description': '간절한 그리움이 말에 담기는 방식을 느껴 보세요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['평온', '그리움'],
  'title': '엄마야 누나야',
  'author': '김소월',
  'description': '평화롭고 다정한 풍경을 상상해 보세요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['후회', '그리움'],
  'title': '먼 후일',
  'author': '김소월',
  'description': '마음과 말이 서로 어긋날 때를 생각해 볼 수 있어요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['그리움', '답답함'],
  'title': '가는 길',
  'author': '김소월',
  'description': '떠나야 하는 마음과 머물고 싶은 마음을 살펴봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['그리움', '외로움'],
  'title': '못잊어',
  'author': '김소월',
  'description': '오랫동안 마음에 남는 사람을 떠올려 볼 수 있어요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['감사', '후회'],
  'title': '예전엔 미처 몰랐어요',
  'author': '김소월',
  'description': '익숙한 것의 소중함을 뒤늦게 깨닫는 순간을 생각해 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['슬픔', '그리움'],
  'title': '접동새',
  'author': '김소월',
  'description': '가족을 향한 그리움이 이야기와 만나는 시예요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['그리움', '슬픔'],
  'title': '금잔디',
  'author': '김소월',
  'description': '계절과 풍경 속에 남은 마음을 살펴봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['설렘', '그리움'],
  'title': '첫치마',
  'author': '김소월',
  'description': '기억 속의 관계와 감정을 들여다볼 수 있어요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['설렘', '평온'],
  'title': '봄밤',
  'author': '김소월',
  'description': '봄밤의 분위기와 마음의 움직임을 상상해 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['설렘', '그리움'],
  'title': '꿈',
  'author': '김소월',
  'description': '꿈과 현실 사이의 감정을 생각해 볼 수 있어요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['슬픔', '답답함'],
  'title': '왕십리',
  'author': '김소월',
  'description': '비와 공간이 만들어 내는 정서를 느껴 보세요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['그리움', '외로움'],
  'title': '삭주구성',
  'author': '김소월',
  'description': '멀어진 곳을 떠올리는 마음을 생각해 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['후회', '자신감'],
  'title': '서시',
  'author': '윤동주',
  'description': '어떤 사람이 되고 싶은지 조용히 질문해 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['그리움', '평온'],
  'title': '별 헤는 밤',
  'author': '윤동주',
  'description': '별을 떠올리며 기억 속 사람과 시간을 생각해 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['부끄러움', '후회'],
  'title': '자화상',
  'author': '윤동주',
  'description': '스스로를 바라보는 복잡한 마음을 이야기해 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['자신감', '설렘'],
  'title': '새로운 길',
  'author': '윤동주',
  'description': '낯설지만 새롭게 시작하는 마음을 떠올려 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['부끄러움', '답답함'],
  'title': '쉽게 쓰여진 시',
  'author': '윤동주',
  'description': '내 마음과 현실 사이의 거리를 생각해 볼 수 있어요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['외로움', '불안'],
  'title': '또 다른 고향',
  'author': '윤동주',
  'description': '익숙한 곳에서도 낯설게 느껴지는 마음을 살펴봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['후회', '부끄러움'],
  'title': '참회록',
  'author': '윤동주',
  'description': '지난 행동을 돌아보고 더 나은 방향을 생각해 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['불안', '자신감'],
  'title': '길',
  'author': '윤동주',
  'description': '내가 가려는 길과 내 선택을 떠올려 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['그리움', '슬픔'],
  'title': '눈 오는 지도',
  'author': '윤동주',
  'description': '계절 속에서 떠오르는 그리움을 살펴봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['지침', '불안'],
  'title': '쉽게 쓰여진 시',
  'author': '윤동주',
  'description': '힘든 때에도 글을 쓰는 마음을 생각해 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['지침', '평온'],
  'title': '산유화',
  'author': '김소월',
  'description': '저만치 혼자서 피어 있네',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['감사', '그리움'],
  'title': '별 헤는 밤',
  'author': '윤동주',
  'description': '마음에 남은 이름 하나를 조용히 떠올려 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['화남', '속상함'],
  'title': '진달래꽃',
  'author': '김소월',
  'description': '상처받은 마음을 어떻게 표현하는지 살펴봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['불안', '두려움'],
  'title': '서시',
  'author': '윤동주',
  'description': '흔들리는 순간에도 지키고 싶은 가치를 생각해 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'},
 {'kind': '시',
  'tags': ['감사', '평온'],
  'title': '엄마야 누나야',
  'author': '김소월',
  'description': '함께하는 사람들과 편안한 풍경을 떠올려 봐요.',
  'question': '이 시가 어떤 마음과 닮았나요?'}]

# 감정 카드에 표시되는 세부 감정을 콘텐츠의 큰 감정 태그로 연결합니다.
EMOTION_MATCHES = {
    "기쁨": "기쁜|행복한|신나는|즐거운|환희에 찬|쾌활한|명랑한|통쾌한|짜릿한|흐뭇한|유쾌한|재미있는",
    "설렘": "설레는|기대되는|두근거리는|흥미로운|끌리는|가슴뭉클한",
    "평온": "편안한|평화로운|포근한|느긋한|차분한|안심이 되는|여유로운|홀가분한|산뜻한",
    "감사": "감사한|고마운|감격스러운|정겨운|따뜻한|다정한",
    "슬픔": "슬픈|우울한|울적한|서글픈|괴로운|비참한|참담한|낙담한",
    "외로움": "외로운|공허한|서먹한|서글픈",
    "불안": "불안한|걱정스러운|초조한|신경쓰이는|근심스러운|속타는|긴장되는",
    "두려움": "두려운|겁나는|오싹한|무서운",
    "화남": "화나는|열받은|격분한|분한",
    "답답함": "답답한|갑갑한|성가신|지루한|따분한|심심한|귀찮은",
    "속상함": "속상한|서운한|섭섭한|실망한|불편한",
    "지침": "지친|피곤한|무기력한|지루한|귀찮은",
    "자신감": "자랑스러운|뿌듯한|든든한|용기 나는|떳떳한|자신 있는",
    "부끄러움": "부끄러운|창피한|민망한|어색한|난처한|곤혹스러운|당혹스런",
    "후회": "후회되는|미안한|죄책감이 드는",
    "그리움": "그리운|보고 싶은|아련한",
}


def content_tags_for_emotion(name):
    matches = {tag for tag, names in EMOTION_MATCHES.items() if name in names.split("|")}
    if matches:
        return matches
    item = BY_NAME.get(name, {})
    if item.get("category") == "positive":
        return {"기쁨", "감사", "평온", "설렘", "자신감"}
    if item.get("category") == "negative":
        return {"슬픔", "불안", "속상함", "답답함", "지침"}
    return {"설렘", "불안", "평온"}


def pick_recommendation(kind, selected, exclude=None):
    target = set().union(*(content_tags_for_emotion(name) for name in selected))
    group = [row for row in RECOMMENDATIONS if row["kind"] == kind]
    scored = [(len(set(row["tags"]) & target), row) for row in group]
    best = [row for score, row in scored if score > 0]
    pool = best or group
    if exclude is not None and len(pool) > 1:
        pool = [row for row in pool if row != exclude] or pool
    return random.choice(pool)

st.markdown("""
<style>
.stApp { background: linear-gradient(155deg, #fff9f1 0%, #fff6f0 70%, #fffdfa 100%); }
.block-container {max-width: 840px; padding-top:1.6rem; padding-bottom:4rem;}
h1,h2,h3 {color:#654435;}
[data-testid="stButton"] button {border-radius:15px;min-height:49px;white-space:normal;}
.cookie-message {background:white;border:1px solid #f1d8bd;border-radius:22px;padding:24px;box-shadow:0 7px 20px #9a72551a;}
.cookie-message p {font-size:1.12rem;line-height:1.8;color:#573d2e;}
.selected-feelings {background:#fff8ec;border:1px solid #f1dcc5;border-radius:17px;padding:14px 19px;margin:0 0 14px;color:#744b3c;}
.selected-feelings div {font-size:1.1rem;margin-top:5px;font-weight:600;}
.cookie-stage {height:230px;position:relative;max-width:340px;margin:0 auto 6px;overflow:hidden;}
.cookie-half {position:absolute;left:50%;top:0; width:205px;height:205px;transform:translateX(-50%);background-size:205px 205px;background-repeat:no-repeat;}
.cookie-left {clip-path:inset(0 50% 0 0); animation:splitLeft 3s ease-in-out forwards;}
.cookie-right {clip-path:inset(0 0 0 50%);animation:splitRight 3s ease-in-out forwards;}
.cookie-note {position:absolute;z-index:-1;left:50%;top:88px;transform:translateX(-50%);background:#fff4d9;box-shadow:0 2px 12px #b08c6b55;border-radius:5px;padding:18px 25px;font-size:24px;animation:paper 3s ease forwards;}
@keyframes splitLeft {0%,28%{transform:translateX(-50%) rotate(0)} 65%,100%{transform:translateX(-81%) rotate(-12deg)}}
@keyframes splitRight {0%,28%{transform:translateX(-50%) rotate(0)} 65%,100%{transform:translateX(-19%) rotate(12deg)}}
@keyframes paper {0%,35%{opacity:0;transform:translate(-50%,12px) scale(.35)} 72%,100%{opacity:1;transform:translate(-50%,0) scale(1)}}
.culture-card {background:#fffefb;border:1px solid #ecd8be;border-radius:20px;padding:23px 24px;margin:8px 0 14px;box-shadow:0 5px 20px #9a725514;}
.culture-kicker {color:#986f4e;font-size:.85rem;font-weight:650;margin-bottom:12px;}
.culture-title {font-size:1.28rem;color:#583a2f;line-height:1.65;font-weight:700;overflow-wrap:anywhere;}
.culture-source {font-size:.92rem;color:#947962;margin-top:11px;}
.culture-description {border-top:1px solid #f0e3d4;margin-top:14px;padding-top:14px;color:#6b5042;line-height:1.7;}
</style>
""", unsafe_allow_html=True)

st.title("🍪 오늘의 마음쿠키")
st.write("오늘 내 마음에 가장 가까운 감정을 **1~2개** 골라서 쿠키를 열어 봐요.")
st.caption("감정에는 정답이 없어요. 오늘의 마음을 있는 그대로 선택해 주세요.")

configured = sheet_is_configured()
if not configured:
    st.warning("선생님이 구글 스프레드시트 연결을 마치면 사용할 수 있어요. 아직 기록이 저장되지 않기 때문에 제출 기능을 잠시 닫아 두었어요.")

student_label = st.selectbox("📋 번호와 이름을 선택해 주세요", ["번호와 이름 선택"] + STUDENT_OPTIONS, index=0)
st.caption("선택한 번호와 이름, 감정, 선생님께 남긴 말이 선생님 전용 기록에 저장됩니다. 다른 학생은 기록을 볼 수 없어요.")
if st.session_state.pop("reset_requested", False):
    st.session_state.selected = []
    st.session_state.result = None
    st.session_state.recommendation = None
    st.session_state.show_recommendations = False
    st.session_state.recorded = False
    st.session_state["teacher_note"] = ""

if "selected" not in st.session_state:
    st.session_state.selected = []
if "result" not in st.session_state:
    st.session_state.result = None
if "recorded" not in st.session_state:
    st.session_state.recorded = False
if "student_id" not in st.session_state:
    st.session_state.student_id = ""

# 다른 학생으로 명단을 바꾸는 경우 이전 결과가 남지 않도록 합니다.
if st.session_state.student_id != student_label:
    st.session_state.selected = []
    st.session_state.result = None
    st.session_state.recommendation = None
    st.session_state.show_recommendations = False
    st.session_state.recorded = False
    st.session_state.student_id = student_label
    st.session_state["teacher_note"] = ""

st.markdown("### 🎨 오늘의 감정 카드")
search = st.text_input("감정 검색", placeholder="예: 설레는, 서운한, 기쁜")
for tab, (category, title) in zip(st.tabs(list(TABS.values())), TABS.items()):
    with tab:
        subset = [e for e in DATA if e["category"] == category and search.strip() in e["name"]]
        if not subset:
            st.caption("해당하는 감정 카드가 없어요.")
        for start in range(0, len(subset), 3):
            for col, emotion in zip(st.columns(3), subset[start:start + 3]):
                name = emotion["name"]
                active = name in st.session_state.selected
                with col:
                    if st.button(("✓ " if active else "") + name, key=f"emotion-{name}", type="primary" if active else "secondary", use_container_width=True, disabled=st.session_state.recorded):
                        if active:
                            st.session_state.selected.remove(name)
                        elif len(st.session_state.selected) < 2:
                            st.session_state.selected.append(name)
                        else:
                            st.toast("감정은 최대 두 개까지 고를 수 있어요.")
                        st.session_state.result = None
                        st.session_state.recommendation = None
                        st.rerun()

st.write("**내가 고른 마음:** " + (" · ".join(st.session_state.selected) if st.session_state.selected else "아직 선택하지 않았어요"))
st.markdown("### 💌 담임 선생님께 전하고 싶은 말")
st.write("평소 얼굴을 보고 말하기 어려웠던 이야기나, 오늘 남기고 싶은 말이 있다면 자유롭게 적어 주세요.")
st.text_area("선생님께 보내는 말 (선택)", key="teacher_note", height=130, max_chars=1000, placeholder="꼭 적지 않아도 돼요. 선생님께 전하고 싶은 말이 있을 때 사용해 주세요.", disabled=st.session_state.recorded)
st.caption("이 글은 담임 선생님이 확인합니다. 바로 읽거나 즉시 답장하는 채팅창은 아니에요. 급하거나 위험한 일이 있다면 선생님이나 믿을 수 있는 어른에게 직접 알려 주세요.")

if not st.session_state.recorded:
    if st.button("🍪 마음쿠키 열기 · 오늘의 마음 제출", type="primary", use_container_width=True,
                 disabled=(student_label == "번호와 이름 선택" or not st.session_state.selected or not configured)):
        result = make_message(st.session_state.selected)
        number = STUDENT_OPTIONS.index(student_label) + 1
        name = STUDENTS[number - 1]
        # 먼저 기록 성공을 확인합니다. 실패하면 애니메이션이나 완료 메시지를 보이지 않습니다.
        try:
            save_submission(number, name, list(st.session_state.selected), st.session_state.teacher_note, result)
        except Exception:
            st.error("지금은 기록을 저장하지 못했어요. 쿠키를 다시 눌러 주세요. 계속 안 되면 선생님께 알려 주세요.")
        else:
            st.session_state.recorded = True
            st.session_state.result = result
            cookie_image = base64.b64encode((ROOT / "fortune_cookie.png").read_bytes()).decode("ascii")
            stage = st.empty()
            stage.markdown(f'''<div class="cookie-stage"><div class="cookie-note">💌</div><div class="cookie-half cookie-left" style="background-image:url(data:image/png;base64,{cookie_image})"></div><div class="cookie-half cookie-right" style="background-image:url(data:image/png;base64,{cookie_image})"></div></div><div style="text-align:center;color:#976045">🍪 마음쿠키를 여는 중...</div>''', unsafe_allow_html=True)
            time.sleep(3.05)
            stage.empty()
            st.rerun()

if st.session_state.recorded and st.session_state.result:
    main, extra_type, extra = st.session_state.result
    st.success("오늘의 마음이 선생님께 전달되었어요. 🍀")
    st.markdown("### 🍪 오늘의 마음 메시지")
    feelings = " · ".join(escape(name) for name in st.session_state.selected)
    st.markdown(f'<div class="selected-feelings"><strong>💗 내가 고른 감정</strong><div>{feelings}</div></div>', unsafe_allow_html=True)
    paragraphs = "".join(f"<p>{escape(p)}</p>" for p in main.split("\n\n"))
    st.markdown(f'<div class="cookie-message">{paragraphs}</div>', unsafe_allow_html=True)
    st.write("")
    if extra_type == "question":
        st.info("🔎 **마음 질문**\n\n" + extra)
    else:
        st.success("🌱 **오늘의 작은 한 걸음**\n\n" + extra)
    if st.button("🍪 같은 마음으로 다른 메시지 보기", use_container_width=True):
        st.session_state.result = make_message(st.session_state.selected)
        st.rerun()
    st.caption("'다른 메시지 보기'는 새 기록을 추가하지 않아요.")
    if "show_recommendations" not in st.session_state:
        st.session_state.show_recommendations = False
    if st.button("📖 내 마음과 닮은 문장 더 보기" if not st.session_state.show_recommendations else "📖 추천 문장 접기", use_container_width=True):
        st.session_state.show_recommendations = not st.session_state.show_recommendations
        st.rerun()
    if st.session_state.show_recommendations:
        st.markdown("### 📖 내 마음과 닮은 문장 더 보기")
        st.caption("오늘 내가 고른 감정과 닮은 문장, 시, 노래를 만나 보세요. 보고 싶은 종류를 고를 수 있어요.")
        if "recommendation_kind" not in st.session_state:
            st.session_state.recommendation_kind = "창작"
        labels = {"창작": "💬 마음 문장", "노래": "🎵 노래", "시": "📜 시"}
        kind = st.radio("추천 종류", list(labels), format_func=lambda x: labels[x], horizontal=True, key="recommendation_kind")
        current = st.session_state.get("recommendation")
        if current is None or current["kind"] != kind:
            current = pick_recommendation(kind, st.session_state.selected)
            st.session_state.recommendation = current
        if kind == "창작":
            st.markdown(
                f'<div class="culture-card"><div class="culture-kicker">💬 마음을 닮은 문장</div>'
                f'<div class="culture-title">{escape(current["description"])}</div>'
                f'<div class="culture-source">오늘의 마음쿠키 · 창작 문장</div></div>',
                unsafe_allow_html=True,
            )
        else:
            title = escape(current["title"])
            author = escape(current["author"])
            description = escape(current["description"])
            name = "오늘의 노래" if kind == "노래" else "오늘의 시"
            st.markdown(
                f'<div class="culture-card"><div class="culture-kicker">{name}</div>'
                f'<div class="culture-title">{title}</div>'
                f'<div class="culture-source">{author}</div>'
                f'<div class="culture-description">{description}</div></div>',
                unsafe_allow_html=True,
            )
            if kind == "노래":
                st.caption("노래 가사는 저작권을 고려해 제공하지 않아요. 곡명과 가수로 찾아 들어 보세요.")
            else:
                st.caption("시구 또는 작품 소개입니다. 감상할 때에는 원문 출처도 확인해 보세요.")
        st.info("💭 " + current["question"])
        if st.button("🔄 이 감정에 어울리는 다른 추천 보기", use_container_width=True):
            st.session_state.recommendation = pick_recommendation(kind, st.session_state.selected, exclude=current)
            st.rerun()
        st.caption("추천을 바꾸어도 선생님께 새로운 기록이 제출되지는 않아요.")
    if st.button("새로 시작하기", use_container_width=True):
        st.session_state.selected = []
        st.session_state.result = None
        st.session_state.recommendation = None
        st.session_state.show_recommendations = False
        st.session_state.recorded = False
        st.session_state.reset_requested = True
        st.rerun()

st.divider()
st.caption("이름을 고르는 방식은 본인 확인 기능이 아니에요. 반드시 자기 이름을 선택해 주세요.")
