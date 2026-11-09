"""오늘의 마음쿠키 | Streamlit + Google Sheets.
GitHub에서 같은 이름의 파일로 교체하면 자동 배포됩니다.
"""
import base64
import hashlib
import hmac
import secrets
import threading
import time as clock
from difflib import SequenceMatcher
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
HEADERS = ["제출 시각(한국)", "번호", "이름", "감정 1", "감정 2", "담임에게 보내는 말", "마음쿠키 메시지", "추가 활동 유형", "추가 활동 내용", "감정을 고른 이유", "선생님 답장"]
AUTH_HEADERS = ["번호", "이름", "최초 등록 코드(교사 배부)", "비밀 코드 해시", "솔트"]

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
    full_message = add_matching_sentence("\n\n".join(main), selected)
    return full_message, extra_type, extra


def sheet_is_configured():
    try:
        return bool(st.secrets.get("spreadsheet_id") and st.secrets.get("gcp_service_account"))
    except (FileNotFoundError, KeyError):
        return False


@st.cache_resource

def google_book():
    creds_info = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"],
    )
    return gspread.authorize(credentials).open_by_key(st.secrets["spreadsheet_id"])


def get_sheet():
    book = google_book()
    try:
        sheet = book.worksheet("마음기록")
    except gspread.WorksheetNotFound:
        sheet = book.add_worksheet(title="마음기록", rows=1500, cols=len(HEADERS))
    if sheet.col_count < len(HEADERS):
        sheet.resize(cols=len(HEADERS))
    existing = sheet.row_values(1)
    if not existing:
        sheet.update(range_name="A1:K1", values=[HEADERS])
        sheet.freeze(rows=1)
    elif existing[:9] == HEADERS[:9]:
        for idx in (9, 10):
            if len(existing) <= idx or not existing[idx]:
                sheet.update_cell(1, idx + 1, HEADERS[idx])
            elif existing[idx] != HEADERS[idx]:
                raise RuntimeError("마음기록 시트의 J/K열 제목이 예상과 다릅니다. 기존 기록은 유지했습니다.")
    else:
        raise RuntimeError("마음기록 시트의 기존 열 제목이 예상과 다릅니다. 기존 기록은 유지했습니다.")
    return sheet


def get_auth_sheet():
    book = google_book()
    try:
        sheet = book.worksheet("학생인증")
    except gspread.WorksheetNotFound:
        sheet = book.add_worksheet(title="학생인증", rows=100, cols=5)
    if sheet.col_count < 5:
        sheet.resize(cols=5)
    values = sheet.get_all_values()
    if not values:
        # 최초 1회만 등록 코드를 생성합니다. 공개 앱 화면에는 절대 표시하지 않습니다.
        rows = [AUTH_HEADERS] + [
            [str(i), name, secrets.token_urlsafe(9), "", ""]
            for i, name in enumerate(STUDENTS, 1)
        ]
        sheet.update(range_name=f"A1:E{len(rows)}", values=rows, value_input_option="RAW")
        sheet.freeze(rows=1)
    elif values[0][:5] != AUTH_HEADERS:
        raise RuntimeError("학생인증 시트의 제목이 맞지 않습니다.")
    return sheet


def auth_record(number):
    sheet = get_auth_sheet()
    row_idx = number + 1
    values = sheet.row_values(row_idx)
    if len(values) < 2 or str(values[0]) != str(number) or values[1] != STUDENTS[number - 1]:
        raise RuntimeError("학생인증 명단을 확인해 주세요.")
    return sheet, row_idx, values + [""] * (5 - len(values))


def hash_code(code, salt):
    # 개인 코드는 평문으로 보관하지 않습니다.
    return hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), bytes.fromhex(salt), 310000).hex()


@st.cache_resource

def login_limits():
    return {"lock": threading.Lock(), "events": {}}


def is_rate_limited(number):
    limit = login_limits()
    now = clock.monotonic()
    with limit["lock"]:
        attempts = [t for t in limit["events"].get(number, []) if now - t < 900]
        limit["events"][number] = attempts
        return len(attempts) >= 8


def note_failed_attempt(number):
    limit = login_limits()
    with limit["lock"]:
        limit["events"].setdefault(number, []).append(clock.monotonic())


def clear_failed_attempts(number):
    limit = login_limits()
    with limit["lock"]:
        limit["events"].pop(number, None)


def student_replies(number):
    # 이미 기록된 모든 메시지 중 학생 번호가 일치하며 K열에 답장이 있는 것만 보여 줍니다.
    # 해당 호출은 서버에서 인증 후에만 일어납니다.
    sheet = get_sheet()
    rows = sheet.get_all_values()[1:]
    replies = []
    for row in rows:
        if len(row) >= 11 and row[1].strip() == str(number) and row[2].strip() == STUDENTS[number - 1] and row[10].strip():
            replies.append({"date": row[0], "note": row[5] if len(row) > 5 else "", "reply": row[10]})
    return list(reversed(replies))[:20]


def safe_cell(text):
    # Google Sheets 수식 주입 방지: 외부 입력을 텍스트로 취급
    value = str(text or "")
    if value.lstrip().startswith(("=", "+", "-", "@")):
        value = "'" + value
    return value


def save_submission(number, name, selected, message_to_teacher, reason, result):
    main, extra_type, extra = result
    row = [
        datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S"),
        number, name, selected[0], selected[1] if len(selected) > 1 else "",
        safe_cell(message_to_teacher), main, "마음 질문" if extra_type == "question" else "작은 한 걸음", extra,
        safe_cell(reason),
    ]
    get_sheet().append_row(row, value_input_option="RAW", insert_data_option="INSERT_ROWS")



# 마음 메시지의 네 번째 문장: 세부 감정 계열별 창작 문장만 사용합니다.
# 시·노래 및 별도 선택 UI는 제공하지 않습니다.
EXTRA_SENTENCES = [
  {
    "family": "편안함",
    "text": "숨을 한 번 천천히 쉬어 봐. 지금의 가벼움이 더 또렷해질지도 몰라."
  },
  {
    "family": "편안함",
    "text": "마음이 한결 가벼운 날에는 평소 놓치던 풍경도 새롭게 보일 수 있어."
  },
  {
    "family": "편안함",
    "text": "오늘의 여유를 급하게 채워 넣지 않아도 좋아."
  },
  {
    "family": "편안함",
    "text": "어깨에 힘을 조금 빼고, 지금 이 순간의 편안함을 느껴 봐."
  },
  {
    "family": "편안함",
    "text": "상쾌한 마음으로 바라보면 익숙한 길도 조금 다르게 느껴질 수 있어."
  },
  {
    "family": "편안함",
    "text": "무엇을 하지 않아도 마음이 편안한 순간은 그 자체로 소중해."
  },
  {
    "family": "편안함",
    "text": "마음이 놓이는 이유가 있다면 그 장면을 잠시 떠올려 봐."
  },
  {
    "family": "편안함",
    "text": "급한 일이 없다는 느낌을 오랜만에 누리는 날일지도 몰라."
  },
  {
    "family": "편안함",
    "text": "아무 일도 크게 걱정되지 않는 이 순간을 편하게 맞이해 봐."
  },
  {
    "family": "편안함",
    "text": "한숨 돌릴 수 있는 시간은 마음에도 작은 휴식이 돼."
  },
  {
    "family": "편안함",
    "text": "가벼운 발걸음으로 오늘의 첫 장면을 시작해도 좋겠어."
  },
  {
    "family": "편안함",
    "text": "오늘의 좋은 기분을 오래 붙잡으려 애쓰기보다 자연스럽게 즐겨 봐."
  },
  {
    "family": "편안함",
    "text": "바람이 잘 통하는 창문처럼 마음도 시원해지는 날이 있어."
  },
  {
    "family": "편안함",
    "text": "잠깐 생긴 여유를 내가 좋아하는 일에 써 보는 건 어떨까?"
  },
  {
    "family": "따뜻함",
    "text": "누군가와 함께 있을 때 느끼는 온기가 마음에 오래 남기도 해."
  },
  {
    "family": "따뜻함",
    "text": "지금의 다정한 마음을 작고 쉬운 말로 전해 봐도 좋겠어."
  },
  {
    "family": "따뜻함",
    "text": "편한 사람을 떠올리기만 해도 마음이 포근해질 때가 있지."
  },
  {
    "family": "따뜻함",
    "text": "마음이 든든한 날에는 익숙한 것들이 더 고맙게 느껴질 수 있어."
  },
  {
    "family": "따뜻함",
    "text": "따뜻한 마음을 느낀 순간이 있다면 조용히 기억해 둬."
  },
  {
    "family": "따뜻함",
    "text": "누군가의 작은 친절이 오늘을 포근하게 만든 걸지도 몰라."
  },
  {
    "family": "따뜻함",
    "text": "마음이 가까워지는 데는 거창한 말이 필요하지 않을 때도 있어."
  },
  {
    "family": "따뜻함",
    "text": "함께 있는 것만으로 편안해지는 사람을 떠올려 봐."
  },
  {
    "family": "따뜻함",
    "text": "지금의 따뜻함을 다른 사람에게 꼭 나누지 않아도 괜찮아. 먼저 충분히 느껴 봐."
  },
  {
    "family": "따뜻함",
    "text": "오래 알고 지낸 사이에서 느끼는 편안함도 특별한 선물이야."
  },
  {
    "family": "따뜻함",
    "text": "나를 믿어 주는 사람이 있다는 생각만으로도 든든할 수 있어."
  },
  {
    "family": "따뜻함",
    "text": "다정함은 눈에 띄지 않는 작은 행동 속에도 숨어 있어."
  },
  {
    "family": "따뜻함",
    "text": "오늘 마음에 남은 따뜻한 장면을 하나 골라 봐."
  },
  {
    "family": "따뜻함",
    "text": "지금 느끼는 친근함이 어디에서 왔는지 생각해 보는 것도 좋겠어."
  },
  {
    "family": "감동",
    "text": "가슴이 뭉클해지는 순간은 말보다 오래 남을 때가 있어."
  },
  {
    "family": "감동",
    "text": "어떤 장면이 너를 감동하게 했는지 천천히 떠올려 봐."
  },
  {
    "family": "감동",
    "text": "정말 놀라운 것을 만났다면 그 느낌을 서둘러 설명하지 않아도 돼."
  },
  {
    "family": "감동",
    "text": "벅찬 마음은 한 가지 단어로 다 담기 어려울 때가 있지."
  },
  {
    "family": "감동",
    "text": "오늘 마음을 움직인 순간이 너에게 어떤 의미였을까?"
  },
  {
    "family": "감동",
    "text": "감동은 예상하지 못한 작은 장면에서 찾아오기도 해."
  },
  {
    "family": "감동",
    "text": "마음 깊이 와닿은 일을 기억하고 싶다면 짧게 적어 봐."
  },
  {
    "family": "감동",
    "text": "놀라움과 고마움이 함께 느껴지는 순간도 있어."
  },
  {
    "family": "감동",
    "text": "오랫동안 바라던 일을 마주하면 마음이 쉽게 가라앉지 않을 수 있어."
  },
  {
    "family": "감동",
    "text": "지금의 뭉클함을 조용히 느끼는 것만으로도 충분해."
  },
  {
    "family": "감동",
    "text": "어떤 말은 지나가도 그때 느낀 감정은 오래 머물 수 있어."
  },
  {
    "family": "감동",
    "text": "내 마음이 움직였다는 건 그만큼 중요한 무언가를 만났다는 뜻일 수 있어."
  },
  {
    "family": "감동",
    "text": "눈앞의 장면이 평소보다 특별하게 느껴지는 날이 있지."
  },
  {
    "family": "감동",
    "text": "지금의 감동을 언젠가 다시 떠올릴 수 있도록 마음에 남겨 둬."
  },
  {
    "family": "기쁨",
    "text": "몸에 생기가 도는 날에는 작은 일도 신나게 느껴질 수 있어."
  },
  {
    "family": "기쁨",
    "text": "마음속 에너지가 움직이는 느낌이라면 오늘은 무엇을 해 보고 싶어?"
  },
  {
    "family": "기쁨",
    "text": "오늘의 기쁨을 다른 이유로 설명하지 말고 그대로 즐겨도 좋아."
  },
  {
    "family": "기쁨",
    "text": "좋은 기분이 찾아왔다면 그 순간을 조금 더 누려 봐."
  },
  {
    "family": "기쁨",
    "text": "신나는 마음은 웃음과 몸짓으로 드러나기도 해."
  },
  {
    "family": "기쁨",
    "text": "기분 좋은 일이 있었다면 그 장면을 한 번 더 떠올려 봐."
  },
  {
    "family": "기쁨",
    "text": "오늘의 활력을 내가 좋아하는 일에 써 보면 어떨까?"
  },
  {
    "family": "기쁨",
    "text": "들뜬 마음을 꼭 차분하게 만들 필요는 없어. 지금의 즐거움을 느껴 봐."
  },
  {
    "family": "기쁨",
    "text": "친구와 웃었던 순간처럼 기쁨은 함께할 때 더 커지기도 해."
  },
  {
    "family": "기쁨",
    "text": "발걸음이 가볍고 표정이 밝은 날은 그냥 그 자체로 좋아."
  },
  {
    "family": "기쁨",
    "text": "작은 성취가 아니어도 하루가 즐거울 이유는 충분해."
  },
  {
    "family": "기쁨",
    "text": "오늘처럼 기운이 나는 날에는 새로운 활동을 하나 골라 봐도 좋겠어."
  },
  {
    "family": "기쁨",
    "text": "행복한 마음이 드는 순간을 너무 빨리 지나치지 말자."
  },
  {
    "family": "기쁨",
    "text": "생기가 느껴지는 오늘, 나를 즐겁게 하는 것이 무엇인지 찾아봐."
  },
  {
    "family": "기대",
    "text": "앞으로 일어날 일을 상상하면 마음이 두근거릴 수 있어."
  },
  {
    "family": "기대",
    "text": "기다리는 일이 있다는 것만으로도 하루가 특별해지지."
  },
  {
    "family": "기대",
    "text": "무엇이 가장 기대되는지 하나만 콕 집어 봐."
  },
  {
    "family": "기대",
    "text": "새로운 것을 향한 호기심이 마음을 움직이고 있나 봐."
  },
  {
    "family": "기대",
    "text": "설레는 일 앞에서는 시간이 조금 느리게 흐르는 것 같기도 해."
  },
  {
    "family": "기대",
    "text": "아직 만나지 않은 순간을 즐겁게 상상해 봐도 좋아."
  },
  {
    "family": "기대",
    "text": "호기심이 생겼다면 무엇을 더 알고 싶은지 생각해 봐."
  },
  {
    "family": "기대",
    "text": "마음이 끌리는 이유를 아직 분명히 몰라도 괜찮아."
  },
  {
    "family": "기대",
    "text": "즐거운 예상을 떠올릴 때 나도 모르게 웃음이 날 수 있어."
  },
  {
    "family": "기대",
    "text": "기대가 큰 만큼 모든 일이 완벽해야 하는 건 아니야."
  },
  {
    "family": "기대",
    "text": "처음 해 볼 일이라면 가장 재미있을 것 같은 부분부터 떠올려 봐."
  },
  {
    "family": "기대",
    "text": "기다림 속에도 이미 작은 즐거움이 들어 있을 수 있어."
  },
  {
    "family": "기대",
    "text": "지금의 설렘을 누군가에게 한마디로 전해 봐도 좋겠어."
  },
  {
    "family": "기대",
    "text": "마음이 향하는 곳이 있다는 사실을 오늘은 즐겨 봐."
  },
  {
    "family": "감사",
    "text": "누군가의 배려가 떠올랐다면 그 마음을 간직해 봐."
  },
  {
    "family": "감사",
    "text": "고마운 마음은 짧은 한마디로도 충분히 전해질 수 있어."
  },
  {
    "family": "감사",
    "text": "익숙해서 지나쳤던 친절이 오늘은 더 크게 느껴졌을지도 몰라."
  },
  {
    "family": "감사",
    "text": "누가 내 하루를 조금 더 편하게 해 주었는지 떠올려 봐."
  },
  {
    "family": "감사",
    "text": "고마운 일이 꼭 거창해야 하는 건 아니야."
  },
  {
    "family": "감사",
    "text": "감사한 마음이 든다면 무엇이 가장 소중했는지 생각해 봐."
  },
  {
    "family": "감사",
    "text": "누군가에게 도움받은 일을 기억하는 것만으로도 따뜻할 수 있어."
  },
  {
    "family": "감사",
    "text": "받은 친절을 반드시 똑같이 돌려줘야 하는 건 아니야."
  },
  {
    "family": "감사",
    "text": "오늘 고마웠던 순간을 하나 적어 두면 오래 기억할 수 있어."
  },
  {
    "family": "감사",
    "text": "반가운 얼굴을 만났다면 그 반가움을 표현해 봐도 좋아."
  },
  {
    "family": "감사",
    "text": "고마운 마음이 들면 잠깐 멈춰 그 이유를 떠올려 봐."
  },
  {
    "family": "감사",
    "text": "평범한 하루에도 고맙다고 말하고 싶은 순간은 있을 수 있어."
  },
  {
    "family": "감사",
    "text": "마음이 뭉클할 만큼 고맙다면 말없이 웃어도 괜찮아."
  },
  {
    "family": "감사",
    "text": "내 곁에 있는 사람의 소중함이 새삼 느껴지는 날이 있지."
  },
  {
    "family": "성취",
    "text": "스스로 뿌듯하다면 그만큼 해낸 일이 있었다는 뜻일 거야."
  },
  {
    "family": "성취",
    "text": "잘한 점을 말하는 일이 자랑처럼 느껴져도 오늘은 인정해 줘도 좋아."
  },
  {
    "family": "성취",
    "text": "네가 노력한 시간을 너 자신이 먼저 알아봐 주자."
  },
  {
    "family": "성취",
    "text": "해낸 일이 있다면 작은 성공이라도 분명하게 기억해 둬."
  },
  {
    "family": "성취",
    "text": "지금의 자신감은 앞으로 해 볼 일을 떠올리게 할 수 있어."
  },
  {
    "family": "성취",
    "text": "결과가 마음에 든다면 그 순간을 충분히 즐겨 봐."
  },
  {
    "family": "성취",
    "text": "남과 비교하지 않고도 내가 성장한 부분을 찾을 수 있어."
  },
  {
    "family": "성취",
    "text": "어려운 일을 끝냈다면 내가 어떤 방법을 썼는지 떠올려 봐."
  },
  {
    "family": "성취",
    "text": "당당한 마음은 나를 더 믿어 보게 만드는 힘이 되기도 해."
  },
  {
    "family": "성취",
    "text": "오늘 스스로에게 '잘했어'라고 말하고 싶은 장면은 무엇일까?"
  },
  {
    "family": "성취",
    "text": "마음이 든든하다면 그 힘으로 어떤 일을 시작하고 싶어?"
  },
  {
    "family": "성취",
    "text": "만족스럽다는 느낌을 서둘러 다음 목표로 바꾸지 않아도 돼."
  },
  {
    "family": "성취",
    "text": "내가 해낸 일을 차분하게 돌아보는 시간도 기쁨의 일부야."
  },
  {
    "family": "성취",
    "text": "작은 용기가 모여 오늘의 자신감이 되었을지도 몰라."
  },
  {
    "family": "답답함",
    "text": "마음이 막힌 것 같다면 무엇이 가장 걸리는지 하나만 찾아봐."
  },
  {
    "family": "답답함",
    "text": "답이 바로 떠오르지 않는 날에도 내 마음을 살펴볼 수는 있어."
  },
  {
    "family": "답답함",
    "text": "답답한 마음이 들 때는 잠깐 자리를 옮기는 것도 도움이 될 수 있어."
  },
  {
    "family": "답답함",
    "text": "말로 다 설명하기 어려운 불편함이 있을 수 있지."
  },
  {
    "family": "답답함",
    "text": "지금 당장 해결할 수 있는 일과 시간이 필요한 일을 나눠 봐."
  },
  {
    "family": "답답함",
    "text": "마음이 갑갑하다면 한 문장으로 그 이유를 적어 봐도 좋아."
  },
  {
    "family": "답답함",
    "text": "앞이 잘 보이지 않는다고 해서 지금 결정을 서둘러야 하는 건 아니야."
  },
  {
    "family": "답답함",
    "text": "꺼림칙한 느낌이 든다면 어떤 점이 불편했는지 생각해 봐."
  },
  {
    "family": "답답함",
    "text": "하나씩 살펴볼 수 있도록 문제를 조금 작게 나눠 보자."
  },
  {
    "family": "답답함",
    "text": "마음이 복잡한 날에는 답보다 질문 하나가 먼저일 수 있어."
  },
  {
    "family": "답답함",
    "text": "가끔은 해결보다 잠깐 멈추는 일이 필요할 때도 있어."
  },
  {
    "family": "답답함",
    "text": "지금 내 힘으로 바꿀 수 없는 일이라면 도움을 요청해도 좋아."
  },
  {
    "family": "답답함",
    "text": "말로 꺼내기 어려운 마음은 글로 먼저 적어 봐도 돼."
  },
  {
    "family": "답답함",
    "text": "어디서부터 시작할지 모르겠다면 가장 작은 부분부터 살펴보자."
  },
  {
    "family": "당황",
    "text": "예상하지 못한 일이 생기면 잠깐 말문이 막힐 수 있어."
  },
  {
    "family": "당황",
    "text": "민망했던 순간이 머릿속에 남아 있다면 천천히 숨을 골라 봐."
  },
  {
    "family": "당황",
    "text": "어색한 분위기에서 무슨 말을 해야 할지 모를 때도 있어."
  },
  {
    "family": "당황",
    "text": "놀란 마음이 가라앉을 시간을 잠깐 가져도 괜찮아."
  },
  {
    "family": "당황",
    "text": "당황했다는 건 준비하지 못한 순간을 만났다는 뜻일 수 있어."
  },
  {
    "family": "당황",
    "text": "모두가 나를 보고 있는 것 같아도 실제로는 아닐 수 있어."
  },
  {
    "family": "당황",
    "text": "한 번의 어색한 순간이 오늘 하루 전체를 결정하지는 않아."
  },
  {
    "family": "당황",
    "text": "무슨 말이 적절할지 모르겠다면 잠깐 생각하고 답해도 돼."
  },
  {
    "family": "당황",
    "text": "부끄러움이 느껴진다면 내게 무엇이 중요했는지 살펴봐."
  },
  {
    "family": "당황",
    "text": "민망한 일은 시간이 지난 뒤 조금 다르게 느껴질 수도 있어."
  },
  {
    "family": "당황",
    "text": "지금은 어리둥절해도 상황을 이해할 시간이 생길 거야."
  },
  {
    "family": "당황",
    "text": "내가 실수했다고 느껴진다면 필요한 만큼만 바로잡아도 괜찮아."
  },
  {
    "family": "당황",
    "text": "말을 더듬거나 얼굴이 붉어졌다고 해서 이상한 건 아니야."
  },
  {
    "family": "당황",
    "text": "갑작스러운 상황 앞에서 멈칫하는 건 자연스러운 일이야."
  },
  {
    "family": "두려움",
    "text": "무서운 마음이 든다면 먼저 안전한 곳인지 살펴보자."
  },
  {
    "family": "두려움",
    "text": "겁이 난다는 사실을 숨기지 않아도 괜찮아."
  },
  {
    "family": "두려움",
    "text": "어떤 점이 두려운지 이름을 붙이면 조금 더 구체적으로 보일 수 있어."
  },
  {
    "family": "두려움",
    "text": "두려운 순간에 혼자 버티지 말고 믿을 만한 사람을 찾아도 좋아."
  },
  {
    "family": "두려움",
    "text": "무서울 때는 크게 움직이기보다 지금 안전한지를 확인해 봐."
  },
  {
    "family": "두려움",
    "text": "몸이 긴장되는 건 무서운 상황에 반응하는 방식일 수 있어."
  },
  {
    "family": "두려움",
    "text": "아직 하지 않은 일 때문에 겁이 난다면 준비할 수 있는 한 가지를 찾아봐."
  },
  {
    "family": "두려움",
    "text": "용감한 척하지 않아도 네 마음은 존중받아야 해."
  },
  {
    "family": "두려움",
    "text": "무엇이 가장 걱정되는지 차분하게 말해 봐도 좋아."
  },
  {
    "family": "두려움",
    "text": "두려움이 큰 날에는 당장 결정을 내리지 않아도 돼."
  },
  {
    "family": "두려움",
    "text": "위험하게 느껴지는 상황이라면 가까운 어른에게 바로 도움을 청하자."
  },
  {
    "family": "두려움",
    "text": "지금 여기에서 내가 확실히 아는 사실부터 살펴봐."
  },
  {
    "family": "두려움",
    "text": "무서움과 호기심이 함께 있을 수도 있어. 안전을 먼저 생각해 보자."
  },
  {
    "family": "두려움",
    "text": "두려움을 느낀다고 해서 약한 사람이 되는 건 아니야."
  },
  {
    "family": "슬픔",
    "text": "슬픈 마음을 빨리 없애야 할 숙제처럼 여기지 않아도 돼."
  },
  {
    "family": "슬픔",
    "text": "마음이 가라앉는 날에는 조용히 쉬는 시간이 필요할 수 있어."
  },
  {
    "family": "슬픔",
    "text": "속상했던 일을 말하고 싶다면 믿을 만한 사람에게 천천히 이야기해 봐."
  },
  {
    "family": "슬픔",
    "text": "슬픈 이유를 당장 정확하게 설명하지 못해도 괜찮아."
  },
  {
    "family": "슬픔",
    "text": "괜찮은 척 웃지 않아도 되는 순간이 필요할 수 있어."
  },
  {
    "family": "슬픔",
    "text": "오늘은 마음이 평소보다 무겁게 느껴지는 날일지도 몰라."
  },
  {
    "family": "슬픔",
    "text": "서글픈 마음이 들면 나에게 필요한 것이 무엇인지 물어봐."
  },
  {
    "family": "슬픔",
    "text": "울고 싶은 마음이 드는 건 이상한 일이 아니야."
  },
  {
    "family": "슬픔",
    "text": "상처받은 마음을 다루는 데는 시간이 걸릴 수 있어."
  },
  {
    "family": "슬픔",
    "text": "누군가에게 '오늘은 조금 힘들어'라고 말해도 괜찮아."
  },
  {
    "family": "슬픔",
    "text": "지금은 좋은 말을 듣는 것보다 조용히 있어 주는 사람이 필요할 수도 있어."
  },
  {
    "family": "슬픔",
    "text": "마음을 돌보는 일에도 서두르지 않는 시간이 필요해."
  },
  {
    "family": "슬픔",
    "text": "안타까운 일을 떠올릴 때 마음이 아플 수 있지."
  },
  {
    "family": "슬픔",
    "text": "오늘의 슬픔을 혼자서 모두 감당해야 하는 건 아니야."
  },
  {
    "family": "화",
    "text": "화가 난 이유가 있다면 무엇이 선을 넘었다고 느꼈는지 살펴봐."
  },
  {
    "family": "화",
    "text": "화를 느끼는 것과 화난 대로 행동하는 것은 서로 다른 일이야."
  },
  {
    "family": "화",
    "text": "억울한 마음이 들 때는 내가 겪은 사실을 차분히 정리해 봐."
  },
  {
    "family": "화",
    "text": "당장 반응하지 않고 숨을 고르는 것도 선택이야."
  },
  {
    "family": "화",
    "text": "나에게 중요한 것이 무시되었다고 느꼈을 수도 있어."
  },
  {
    "family": "화",
    "text": "화난 마음을 알아차렸다면 어떻게 표현할지 내가 선택할 수 있어."
  },
  {
    "family": "화",
    "text": "속이 부글거릴 때는 먼저 몸을 조금 진정시켜 봐."
  },
  {
    "family": "화",
    "text": "상대에게 전하고 싶은 말을 공격적이지 않은 문장으로 바꿔 봐."
  },
  {
    "family": "화",
    "text": "내가 화난 이유를 정확히 아는 일이 해결의 시작일 수 있어."
  },
  {
    "family": "화",
    "text": "마음이 격해진 때에는 중요한 답변을 잠깐 미뤄도 좋아."
  },
  {
    "family": "화",
    "text": "억울한 일이 있다면 믿을 만한 어른에게 사실을 알려도 돼."
  },
  {
    "family": "화",
    "text": "누군가를 탓하기 전에 내가 바라는 변화를 생각해 봐."
  },
  {
    "family": "화",
    "text": "서로 다른 생각 때문에 화가 날 수 있지만 상처 주는 말은 피할 수 있어."
  },
  {
    "family": "화",
    "text": "화를 느낀 내 마음도 존중하면서 행동은 신중하게 골라 보자."
  },
  {
    "family": "걱정",
    "text": "걱정이 많아질 때는 아직 일어나지 않은 일과 실제 상황을 구분해 봐."
  },
  {
    "family": "걱정",
    "text": "불안한 마음이 든다면 지금 확인할 수 있는 사실 한 가지를 찾아봐."
  },
  {
    "family": "걱정",
    "text": "내일의 일을 오늘 모두 해결하지 않아도 괜찮아."
  },
  {
    "family": "걱정",
    "text": "긴장될 때는 숨을 천천히 내쉬며 몸의 속도를 늦춰 봐."
  },
  {
    "family": "걱정",
    "text": "생각이 자꾸 앞서간다면 지금 할 수 있는 일 하나에 집중해 보자."
  },
  {
    "family": "걱정",
    "text": "걱정의 크기가 크다고 해서 나쁜 일이 반드시 일어나는 건 아니야."
  },
  {
    "family": "걱정",
    "text": "초조한 마음은 기다림이 길게 느껴질 때 더 커질 수 있어."
  },
  {
    "family": "걱정",
    "text": "내가 통제할 수 있는 것과 없는 것을 나눠 보면 도움이 될 수 있어."
  },
  {
    "family": "걱정",
    "text": "확실하지 않은 일을 상상하며 지쳤다면 잠시 쉬어도 좋아."
  },
  {
    "family": "걱정",
    "text": "지금 가장 궁금한 점이 무엇인지 적어 봐."
  },
  {
    "family": "걱정",
    "text": "불안을 없애려고 애쓰기보다 안전한 준비부터 해 보자."
  },
  {
    "family": "걱정",
    "text": "아직 결과를 모르는 상황이라면 섣불리 결론 내리지 않아도 돼."
  },
  {
    "family": "걱정",
    "text": "몸이 긴장되어 있다면 발바닥이 바닥에 닿는 느낌을 느껴 봐."
  },
  {
    "family": "걱정",
    "text": "걱정되는 일을 혼자 품기 어렵다면 누군가에게 알려도 돼."
  },
  {
    "family": "거리감",
    "text": "누군가와 멀어진 듯한 기분이라면 그 마음을 먼저 알아차려 봐."
  },
  {
    "family": "거리감",
    "text": "서운한 마음에는 기대했던 것이 있었을 수 있어."
  },
  {
    "family": "거리감",
    "text": "외로운 날에는 내가 편하게 연락할 수 있는 사람을 떠올려 봐."
  },
  {
    "family": "거리감",
    "text": "같은 공간에 있어도 혼자라고 느껴지는 순간이 있지."
  },
  {
    "family": "거리감",
    "text": "마음이 허전할 때는 지금 내게 필요한 것이 무엇인지 물어봐."
  },
  {
    "family": "거리감",
    "text": "섭섭했다면 무엇을 바랐는지 차분하게 생각해 봐."
  },
  {
    "family": "거리감",
    "text": "누군가에게 먼저 말을 건네는 작은 용기가 도움이 될 수 있어."
  },
  {
    "family": "거리감",
    "text": "아쉬운 마음은 그 순간이 내게 소중했다는 뜻일 수도 있어."
  },
  {
    "family": "거리감",
    "text": "사람들과 거리를 느낀다고 해서 내게 문제가 있다는 뜻은 아니야."
  },
  {
    "family": "거리감",
    "text": "함께하고 싶은 사람이 있다면 부담 없는 안부를 건네 봐."
  },
  {
    "family": "거리감",
    "text": "혼자 있고 싶은 마음과 누군가가 그리운 마음이 함께 들 수도 있어."
  },
  {
    "family": "거리감",
    "text": "서운한 일을 말할 때는 '나는 이렇게 느꼈어'라고 시작해 봐."
  },
  {
    "family": "거리감",
    "text": "적막하게 느껴지는 날에는 내가 좋아하는 소리 하나를 찾아봐."
  },
  {
    "family": "거리감",
    "text": "누군가가 내 마음을 알아주길 바라는 건 자연스러운 일이야."
  },
  {
    "family": "지루함",
    "text": "지루한 시간이라면 평소 그냥 지나치던 것을 하나 관찰해 봐."
  },
  {
    "family": "지루함",
    "text": "심심함은 새로운 재미를 찾고 싶다는 신호일 수 있어."
  },
  {
    "family": "지루함",
    "text": "지금 할 수 있는 작고 쉬운 활동을 하나 골라 볼까?"
  },
  {
    "family": "지루함",
    "text": "뭔가 하고 싶은데 떠오르지 않는 순간도 있지."
  },
  {
    "family": "지루함",
    "text": "하루가 느리게 가는 날에는 주변의 작은 변화를 찾아봐."
  },
  {
    "family": "지루함",
    "text": "심심한 순간에 오히려 새로운 생각이 떠오르기도 해."
  },
  {
    "family": "지루함",
    "text": "꼭 재미있는 일을 찾아야 하는 건 아니야. 잠깐 아무것도 안 해도 돼."
  },
  {
    "family": "지루함",
    "text": "지루할 때는 평소 좋아하던 활동을 조금 다르게 해 봐."
  },
  {
    "family": "지루함",
    "text": "오늘 처음 보는 색이나 모양을 찾아보는 건 어떨까?"
  },
  {
    "family": "지루함",
    "text": "재미없다고 느끼는 일에서도 궁금한 점 하나는 찾을 수 있어."
  },
  {
    "family": "지루함",
    "text": "기다림이 길게 느껴진다면 마음속으로 짧은 이야기를 만들어 봐."
  },
  {
    "family": "지루함",
    "text": "친구와 가벼운 대화를 나누는 것도 심심함을 달랠 수 있어."
  },
  {
    "family": "지루함",
    "text": "지금 내 마음이 원하는 자극이 무엇인지 살펴봐."
  },
  {
    "family": "지루함",
    "text": "지루함 속에도 잠깐 쉬어 갈 여유가 있을 수 있어."
  },
  {
    "family": "지침",
    "text": "몸과 마음이 지친 날에는 해야 할 일을 조금 덜어도 괜찮아."
  },
  {
    "family": "지침",
    "text": "피곤함을 느끼고 있다면 지금 내 몸에 무엇이 필요한지 살펴봐."
  },
  {
    "family": "지침",
    "text": "쉬는 시간은 일을 미루는 시간이 아니라 회복하는 시간이기도 해."
  },
  {
    "family": "지침",
    "text": "할 일이 많아 지쳤다면 가장 급한 것 하나부터 정리해 봐."
  },
  {
    "family": "지침",
    "text": "기운이 없을 때는 내 속도를 평소보다 늦춰도 좋아."
  },
  {
    "family": "지침",
    "text": "잠깐 눈을 감고 어깨의 힘을 빼 보는 건 어떨까?"
  },
  {
    "family": "지침",
    "text": "오늘은 열심히 하는 것만큼 쉬는 것도 중요할 수 있어."
  },
  {
    "family": "지침",
    "text": "귀찮다는 마음 뒤에는 피로가 숨어 있을지도 몰라."
  },
  {
    "family": "지침",
    "text": "모든 것을 잘해 내려고 힘주지 않아도 되는 날이 있어."
  },
  {
    "family": "지침",
    "text": "피곤할 때는 물을 마시고 가볍게 몸을 움직여 봐."
  },
  {
    "family": "지침",
    "text": "내가 쉬어야 할 때를 알아차리는 것도 중요한 능력이야."
  },
  {
    "family": "지침",
    "text": "지금 힘이 부족하다면 도움을 요청해도 괜찮아."
  },
  {
    "family": "지침",
    "text": "쉬고 난 뒤에 다시 생각해도 되는 일은 잠시 내려놓자."
  },
  {
    "family": "지침",
    "text": "오늘은 가능한 만큼 해낸 것으로 충분할 수 있어."
  },
  {
    "family": "실망",
    "text": "기대했던 결과가 아니라면 실망스러운 마음이 드는 게 자연스러워."
  },
  {
    "family": "실망",
    "text": "무엇을 기대했는지 떠올리면 실망의 이유가 조금 보일 수 있어."
  },
  {
    "family": "실망",
    "text": "원하는 대로 되지 않았다는 사실과 내 가치가 낮다는 건 다른 일이야."
  },
  {
    "family": "실망",
    "text": "실망한 순간에 바로 긍정적으로 생각할 필요는 없어."
  },
  {
    "family": "실망",
    "text": "아쉬운 점을 인정한 뒤에 다음을 생각해 봐도 늦지 않아."
  },
  {
    "family": "실망",
    "text": "잘되지 않은 일에서 나에게 중요한 기준을 발견할 수도 있어."
  },
  {
    "family": "실망",
    "text": "마음이 가라앉았다면 잠시 쉬고 나서 다시 살펴보자."
  },
  {
    "family": "실망",
    "text": "실망이 컸다는 건 그만큼 기대했던 일이었다는 뜻일 수 있어."
  },
  {
    "family": "실망",
    "text": "어떤 점이 가장 아쉬웠는지 한 가지만 정리해 봐."
  },
  {
    "family": "실망",
    "text": "결과를 바꿀 수 없다면 다음에 선택할 수 있는 일을 찾아봐."
  },
  {
    "family": "실망",
    "text": "오늘의 아쉬움을 서둘러 배움으로 바꾸지 않아도 돼."
  },
  {
    "family": "실망",
    "text": "누군가에게 실망한 이유를 차분하게 표현해 봐도 좋아."
  },
  {
    "family": "실망",
    "text": "마음에 안 드는 결과가 나왔다고 모든 과정이 사라지는 건 아니야."
  },
  {
    "family": "실망",
    "text": "실망한 내 마음을 먼저 받아 준 뒤에 다음 걸음을 생각해 보자."
  },
  {
    "family": "멍함",
    "text": "머릿속이 멍하다면 잠깐 주변을 둘러보는 것부터 시작해 봐."
  },
  {
    "family": "멍함",
    "text": "생각이 잘 모이지 않는 날도 있어. 천천히 지금을 느껴 봐."
  },
  {
    "family": "멍함",
    "text": "말로 설명하기 어려운 묘한 기분이 들 수 있지."
  },
  {
    "family": "멍함",
    "text": "지금 보이는 것 세 가지를 조용히 찾아봐."
  },
  {
    "family": "멍함",
    "text": "어떤 감정인지 아직 모르겠다면 이름 붙이기를 미뤄도 좋아."
  },
  {
    "family": "멍함",
    "text": "잠깐 멈춘 듯한 느낌이 들 때는 몸을 가볍게 움직여 봐."
  },
  {
    "family": "멍함",
    "text": "마음이 복잡해서 멍한 건지, 그냥 쉬고 싶은 건지 살펴봐."
  },
  {
    "family": "멍함",
    "text": "무슨 생각을 해야 할지 모르는 순간에도 숨은 계속 흐르고 있어."
  },
  {
    "family": "멍함",
    "text": "지금은 뚜렷한 답보다 잠깐의 휴식이 필요할 수도 있어."
  },
  {
    "family": "멍함",
    "text": "생각이 멀리 떠 있는 것 같다면 발끝의 감각을 느껴 봐."
  },
  {
    "family": "멍함",
    "text": "묘한 기분을 꼭 좋거나 나쁘게 나눌 필요는 없어."
  },
  {
    "family": "멍함",
    "text": "오늘 내 마음을 가장 잘 닮은 색이 있다면 무엇일까?"
  },
  {
    "family": "멍함",
    "text": "조용한 순간에 내 생각이 어디로 향하는지 살펴봐."
  },
  {
    "family": "멍함",
    "text": "머리가 복잡한 날에는 한 가지 일만 천천히 해 보자."
  }
]

SENTENCES_BY_FAMILY = {}
for item in EXTRA_SENTENCES:
    SENTENCES_BY_FAMILY.setdefault(item["family"], []).append(item["text"])


def add_matching_sentence(main, selected):
    """선택한 감정 계열과 일치하는 문장을 기존 세 문장 뒤에 추가합니다."""
    families = list(dict.fromkeys(BY_NAME[name]["family"] for name in selected))
    # 두 감정이 다른 계열이면 계열을 무작위 선택하되, 항상 정확히 일치하는 계열만 사용합니다.
    available = [family for family in families if SENTENCES_BY_FAMILY.get(family)]
    if not available:
        return main  # 무관한 문장으로 대체하지 않습니다.
    family = random.choice(available)
    used = set(main.split("\n\n"))
    pool = [x for x in SENTENCES_BY_FAMILY[family] if x not in used]
    return main + "\n\n" + random.choice(pool or SENTENCES_BY_FAMILY[family])

# 학생의 일상 표현으로도 현재 감정 카드를 찾을 수 있게 합니다.
# 같은 의미로 보이는 검색어만 수동 연결하고, 범주 전체를 무작정 섞지 않습니다.
SEARCH_ALIASES = {
    "행복": ["행복한", "기쁜", "즐거운"],
    "기분좋": ["기쁜", "즐거운", "상쾌한"],
    "좋아": ["즐거운", "행복한"],
    "신남": ["신나는", "활기 넘치는", "쾌활한"],
    "신나": ["신나는", "활기 넘치는", "쾌활한"],
    "텐션": ["신나는", "활기 넘치는"],
    "에너지": ["생기가 도는", "활기 넘치는"],
    "활력": ["생기가 도는", "활기 넘치는"],
    "설렘": ["설레는", "기대되는"],
    "두근": ["설레는", "떨리는", "긴장되는"],
    "기대감": ["기대되는", "설레는"],
    "뿌듯": ["뿌듯한", "자랑스러운", "만족스러운"],
    "자신감": ["용기 나는", "든든한"],
    "자신있": ["용기 나는", "든든한"],
    "보람": ["뿌듯한", "만족스러운", "흐뭇한"],
    "고마움": ["고마운", "감사한"],
    "감동": ["가슴뭉클한", "감격스러운"],
    "포근": ["포근한", "따뜻한", "푸근한"],
    "사랑": ["따뜻한", "다정한", "달콤한"],
    "안도": ["안심이 되는", "마음이 놓이는", "후련한"],
    "편함": ["편안한", "여유로운", "느긋한"],
    "편해": ["편안한", "마음이 놓이는"],
    "해방감": ["홀가분한", "후련한"],
    "홀가분": ["홀가분한", "가벼운"],
    "짜증": ["화나는", "열받은", "성가신"],
    "빡침": ["화나는", "열받은"],
    "빡쳐": ["화나는", "열받은"],
    "분노": ["화나는", "격분한", "분한"],
    "억울": ["억울한", "분한"],
    "화남": ["화나는", "열받은"],
    "화나": ["화나는", "열받은"],
    "속상": ["속상한", "서운한", "실망한"],
    "우울": ["우울한", "울적한", "서글픈"],
    "눈물": ["슬픈", "서글픈", "속상한"],
    "슬픔": ["슬픈", "서글픈", "울적한"],
    "외로움": ["외로운", "쓸쓸한", "공허한"],
    "외롭": ["외로운", "쓸쓸한"],
    "소외": ["외로운", "서운한"],
    "서운함": ["서운한", "섭섭한"],
    "섭섭함": ["섭섭한", "서운한"],
    "허전": ["공허한", "쓸쓸한"],
    "불안감": ["불안한", "초조한", "걱정스러운"],
    "걱정": ["걱정스러운", "불안한", "근심스러운"],
    "긴장감": ["긴장되는", "떨리는", "초조한"],
    "스트레스": ["지친", "답답한", "불편한"],
    "압박감": ["답답한", "초조한", "걱정스러운"],
    "답답함": ["답답한", "갑갑한", "막막한"],
    "막막": ["막막한", "암담한"],
    "무서움": ["무서운", "겁나는", "두려운"],
    "공포": ["무서운", "겁나는", "오싹한"],
    "당황": ["당혹스런", "난감한", "어리둥절한"],
    "쪽팔": ["창피한", "민망한"],
    "민망함": ["민망한", "부끄러운"],
    "어색함": ["어색한", "서먹한"],
    "심심": ["심심한", "지루한", "따분한"],
    "노잼": ["지루한", "따분한"],
    "귀찮": ["귀찮은", "무기력한"],
    "피곤": ["피곤한", "지친"],
    "졸림": ["피곤한", "지친"],
    "힘듦": ["지친", "괴로운", "피곤한"],
    "힘들": ["지친", "괴로운", "피곤한"],
    "번아웃": ["지친", "무기력한"],
    "무기력": ["무기력한", "지친"],
    "실패": ["실망한", "낙담한", "속상한"],
    "실망감": ["실망한", "낙담한"],
    "혼란": ["어리둥절한", "멍한", "당혹스런"],
    "멍때림": ["멍한", "얼떨떨한"],
}


def normalize_search(text):
    return "".join(str(text).lower().split()).replace("·", "").replace("!", "")


def search_emotions(query):
    """정확한 검색 결과 먼저, 그다음 비슷한 표현. 전혀 무관한 후보는 제외."""
    query = normalize_search(query)
    if not query:
        return {e["name"]: 1.0 for e in DATA}
    scores = {}
    for e in DATA:
        name = e["name"]
        norm = normalize_search(name)
        if query == norm:
            scores[name] = 100.0
        elif query in norm or (len(norm) >= 2 and norm in query):
            scores[name] = 90.0
    for alias, candidates in SEARCH_ALIASES.items():
        if query == alias or (len(query) >= 2 and query in alias) or (len(alias) >= 2 and alias in query):
            for i, name in enumerate(candidates):
                if name in BY_NAME:
                    scores[name] = max(scores.get(name, 0.0), 78.0 - i)
    if not scores and len(query) >= 2:
        # 오타 보정은 높은 유사도에서만 제한적으로 동작합니다.
        for e in DATA:
            name = e["name"]
            similarity = SequenceMatcher(None, query, normalize_search(name)).ratio()
            if similarity >= 0.72:
                scores[name] = 60.0 + similarity
    return dict(sorted(scores.items(), key=lambda pair: (-pair[1], pair[0])))


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

/* 감정 카드: 작은 화면에서도 3열을 유지합니다.
   Streamlit은 모바일에서 st.columns를 기본적으로 세로로 쌓기 때문에,
   감정 탭 안의 행에만 가로 배치를 다시 적용합니다. */
@media (max-width: 640px) {
  .block-container {
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
  }
  [data-testid="stTabs"] [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: stretch !important;
    gap: 0.4rem !important;
  }
  [data-testid="stTabs"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
  [data-testid="stTabs"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    flex: 1 1 0% !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: none !important;
  }
  [data-testid="stTabs"] [data-testid="stColumn"] [data-testid="stButton"],
  [data-testid="stTabs"] [data-testid="column"] [data-testid="stButton"] {
    width: 100% !important;
  }
  [data-testid="stTabs"] [data-testid="stButton"] button {
    width: 100% !important;
    min-height: 42px !important;
    padding: 0.32rem 0.09rem !important;
    border-radius: 11px !important;
    font-size: clamp(0.73rem, 3.3vw, 0.9rem) !important;
    line-height: 1.2 !important;
    white-space: normal !important;
    word-break: keep-all !important;
    overflow-wrap: anywhere !important;
  }
  [data-testid="stTabs"] [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] {
    gap: 0.3rem !important;
  }
}
/* 배포자가 밝은 색 배경을 사용하므로, 브라우저의 어두운 테마에서도
   문구와 입력 요소의 대비가 유지되도록 명시합니다. */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {color:#352c27 !important; color-scheme:light !important;}
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stSelectbox"] label,
.stApp [data-testid="stTextInput"] label,
.stApp [data-testid="stTextArea"] label {color:#46352d !important;}
.stApp div[data-baseweb="select"] > div,
.stApp div[data-baseweb="input"] > div,
.stApp div[data-baseweb="textarea"] > div {
  background:#fffdf9 !important; color:#302720 !important; border-color:#b6a69c !important;
}
.stApp input, .stApp textarea {color:#302720 !important; -webkit-text-fill-color:#302720 !important;}
.stApp input::placeholder, .stApp textarea::placeholder {color:#776b63 !important; -webkit-text-fill-color:#776b63 !important;}
.stApp [data-testid="stButton"] button[kind="secondary"] {background:#ffffff !important; color:#352c27 !important; border:1px solid #b6a69c !important;}
.stApp [data-testid="stButton"] button[kind="primary"] {background:#a4434b !important; color:#ffffff !important; border:1px solid #a4434b !important;}
.stApp [data-testid="stTabs"] button {color:#493b32 !important;}
.stApp [data-testid="stAlert"] {background:#edf4fc !important; color:#243247 !important;}
.stApp [data-testid="stAlert"] * {color:#243247 !important;}
.stApp [data-testid="stExpander"] {background:#fffdf9 !important; border-color:#b6a69c !important;}
@media (max-width:640px) {
  .block-container {padding-top:0.8rem !important;}
  .stApp h1 {font-size:1.85rem !important;}
}
</style>
""", unsafe_allow_html=True)

st.title("🍪 오늘의 마음쿠키")
st.caption("💡 화면이 잘 보이지 않으면 오른쪽 위 ⋮ 메뉴의 설정(Settings)에서 테마를 Light로 변경해 주세요. (기본 화면은 밝은 색으로 표시됩니다.)")
st.write("오늘 내 마음에 가장 가까운 감정을 **1~2개** 골라서 쿠키를 열어 봐요.")
st.caption("감정에는 정답이 없어요. 오늘의 마음을 있는 그대로 선택해 주세요.")

configured = sheet_is_configured()
if not configured:
    st.warning("선생님이 구글 스프레드시트 연결을 마치면 사용할 수 있어요. 아직 기록이 저장되지 않기 때문에 제출 기능을 잠시 닫아 두었어요.")

student_label = st.selectbox("📋 번호와 이름을 선택해 주세요", ["번호와 이름 선택"] + STUDENT_OPTIONS, index=0)
st.caption("감정과 남긴 말은 선생님 전용 구글 스프레드시트에 기록됩니다. 답장은 본인 인증 뒤에만 확인할 수 있어요.")

if "verified_student" not in st.session_state:
    st.session_state.verified_student = None
if st.session_state.verified_student is not None and student_label != STUDENT_OPTIONS[st.session_state.verified_student - 1]:
    st.session_state.verified_student = None

if student_label == "번호와 이름 선택":
    st.info("먼저 번호와 이름을 선택해 주세요.")
    st.stop()

number = STUDENT_OPTIONS.index(student_label) + 1
if not configured:
    st.stop()

if st.session_state.verified_student != number:
    st.markdown("### 🔐 나만의 비밀 코드")
    try:
        auth_sheet, auth_row, record = auth_record(number)
    except Exception:
        st.error("본인 확인 준비가 되지 않았어요. 선생님께 알려 주세요.")
        st.stop()
    if is_rate_limited(number):
        st.warning("인증 시도가 많아 잠시 이용할 수 없어요. 15분 뒤 다시 시도하거나 선생님께 알려 주세요.")
        st.stop()
    if not record[3]:
        st.info("처음 방문했나요? 선생님이 알려 준 1회용 등록 코드로 나만의 비밀 코드를 만들어요.")
        with st.form("create_account"):
            setup_code = st.text_input("선생님이 나눠 준 등록 코드", type="password")
            new_code = st.text_input("앞으로 사용할 비밀 코드 (영문+숫자, 8자 이상)", type="password")
            new_code_again = st.text_input("비밀 코드 다시 입력", type="password")
            submitted = st.form_submit_button("내 비밀 코드 등록하기", use_container_width=True)
        if submitted:
            # 재확인해 다른 접속에서 먼저 등록한 계정의 덮어쓰기를 방지합니다.
            auth_sheet, auth_row, record = auth_record(number)
            if record[3]:
                st.error("이미 등록된 계정입니다. 화면을 새로고침해 로그인해 주세요.")
            elif not hmac.compare_digest(setup_code, record[2]):
                note_failed_attempt(number)
                st.error("등록 코드가 맞지 않아요. 선생님께 받은 코드를 확인하세요.")
            elif not (8 <= len(new_code) <= 32 and any(c.isalpha() for c in new_code) and any(c.isdigit() for c in new_code)):
                st.error("영문과 숫자가 포함된 8~32자리 코드를 사용해 주세요.")
            elif new_code != new_code_again:
                st.error("두 비밀 코드가 서로 달라요.")
            else:
                try:
                    salt = secrets.token_hex(16)
                    auth_sheet.update(range_name=f"D{auth_row}:E{auth_row}", values=[[hash_code(new_code, salt), salt]], value_input_option="RAW")
                    auth_sheet.update_acell(f"C{auth_row}", "")
                    clear_failed_attempts(number)
                    st.session_state.verified_student = number
                    st.rerun()
                except Exception:
                    st.error("비밀 코드를 저장하지 못했어요. 선생님께 알려 주세요.")
    else:
        with st.form("login_account"):
            code = st.text_input("나만의 비밀 코드", type="password")
            login = st.form_submit_button("내 마음쿠키 열기 · 답장 확인", use_container_width=True)
        if login:
            if record[4] and hmac.compare_digest(hash_code(code, record[4]), record[3]):
                clear_failed_attempts(number)
                st.session_state.verified_student = number
                st.rerun()
            else:
                note_failed_attempt(number)
                st.error("비밀 코드가 일치하지 않아요.")
    st.caption("코드를 잊었다면 선생님께 직접 초기화를 요청하세요. 다른 친구의 코드를 사용하면 안 돼요.")
    st.stop()

st.success("🔓 본인 확인 완료")
with st.expander("💌 선생님의 답장 확인", expanded=True):
    if st.button("답장 새로고침", key="refresh_replies"):
        st.rerun()
    try:
        replies = student_replies(number)
    except Exception:
        st.warning("답장을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.")
        replies = []
    if replies:
        st.write(f"선생님이 남긴 답장 **{len(replies)}개**를 확인할 수 있어요.")
        for reply in replies:
            st.markdown(f"**📅 {escape(reply['date'])}에 보낸 마음**")
            if reply["note"]:
                st.caption("내가 보낸 말: " + reply["note"])
            st.info("💌 선생님의 답장\n\n" + reply["reply"])
    else:
        st.caption("아직 도착한 답장이 없어요. 선생님이 답장을 작성하면 이곳에서 볼 수 있어요.")

if st.session_state.pop("reset_requested", False):
    st.session_state.selected = []
    st.session_state.result = None
    st.session_state.recorded = False
    st.session_state["teacher_note"] = ""
    st.session_state["emotion_reason"] = ""

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
    st.session_state.recorded = False
    st.session_state.student_id = student_label
    st.session_state["teacher_note"] = ""
    st.session_state["emotion_reason"] = ""

st.markdown("### 🎨 오늘의 감정 카드")
search = st.text_input("감정 검색", placeholder="예: 짜증, 신남, 허전함, 설렘, 피곤해")
search_scores = search_emotions(search)
if search.strip():
    if search_scores:
        st.caption(f"'{search.strip()}'와 비슷한 감정 {len(search_scores)}개를 찾았어요. 가장 가까운 표현부터 보여줘요.")
    else:
        st.caption("비슷한 감정을 찾지 못했어요. 다른 말로 검색해 보거나 카드에서 골라 보세요.")
for tab, (category, title) in zip(st.tabs(list(TABS.values())), TABS.items()):
    with tab:
        subset = [e for e in DATA if e["category"] == category and e["name"] in search_scores]
        if search.strip():
            subset.sort(key=lambda e: -search_scores[e["name"]])
        if not subset:
            st.caption("해당하는 감정 카드가 없어요.")
        for start in range(0, len(subset), 3):
            for col, emotion in zip(st.columns(3, gap="small"), subset[start:start + 3]):
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
                        st.rerun()

st.write("**내가 고른 마음:** " + (" · ".join(st.session_state.selected) if st.session_state.selected else "아직 선택하지 않았어요"))
st.markdown("### ✏️ 이 감정을 고른 이유")
st.text_area(
    "오늘 이런 감정이 든 이유는 무엇인가요? (선택)",
    key="emotion_reason", height=110, max_chars=700,
    placeholder="예: 친구가 먼저 인사해 줘서 기뻤어요. / 발표를 앞두고 있어서 긴장돼요.",
    disabled=st.session_state.recorded,
)
st.caption("적지 않아도 괜찮아요. 적은 내용은 담임 선생님만 확인하는 구글 스프레드시트 기록에 함께 저장돼요.")
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
            save_submission(number, name, list(st.session_state.selected), st.session_state.teacher_note, st.session_state.emotion_reason, result)
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
    if st.button("새로 시작하기", use_container_width=True):
        st.session_state.selected = []
        st.session_state.result = None
        st.session_state.recorded = False
        st.session_state.reset_requested = True
        st.rerun()

st.divider()
st.caption("비밀 코드는 다른 친구에게 알려주지 마세요. 급한 일은 답장을 기다리지 말고 선생님께 직접 이야기하세요.")
