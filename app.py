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
    chosen = [BY_NAME[name] for name in selected]
    first = chosen[0]
    if len(chosen) == 1:
        main = [first["acknowledge"][0], random.choice(first["perspective"]),
                random.choice(POSITIVE_CLOSINGS if tone(first) == "bright" else LOW_CLOSINGS)]
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
                main = [first["acknowledge"][0], f"{second['name']} 마음까지 더해졌네. " + random.choice(second["perspective"]), random.choice(POSITIVE_CLOSINGS)]
        elif a == b == "heavy":
            if set(selected) == {"서운한", "화나는"}:
                main = [
                    "기대했던 마음이 있어서 서운했는데, 화까지 났다면 마음이 더 복잡했겠어.",
                    "그럴 때는 무엇이 가장 서운했는지, 무엇 때문에 화가 났는지 하나씩 살펴봐도 좋아.",
                    "지금 바로 해결하려 애쓰지 말고, 네 마음을 차근차근 정리해 보자.",
                ]
            else:
                main = [first["acknowledge"][0], f"{second['name']} 마음도 함께 느껴지는구나. " + random.choice(second["perspective"]), random.choice(LOW_CLOSINGS)]
        else:
            if set(selected) == {"기대되는", "긴장되는"}:
                main = [
                    "기대되는 일이 있으면서도 잘하고 싶은 마음에 긴장될 수 있지.",
                    "두근거리는 기대와 조심스러운 긴장이 함께 있다는 건 그만큼 마음이 쓰인다는 뜻일 수도 있어.",
                    "완벽하게 하려고 애쓰기보다, 네가 준비한 만큼 한 걸음씩 해 보길 바라!",
                ]
            else:
                bright = first if a == "bright" else second
                heavy = second if a == "bright" else first
                main = [f"{bright['name']} 마음이 있으면서도 {heavy['name']} 마음이 함께 드는구나.",
                        random.choice(bright["perspective"]) + " " + random.choice(heavy["perspective"]), random.choice(MIXED_CLOSINGS)]
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


st.markdown("""
<style>
.stApp { background: linear-gradient(155deg, #fff9f1 0%, #fff6f0 70%, #fffdfa 100%); }
.block-container {max-width: 840px; padding-top:1.6rem; padding-bottom:4rem;}
h1,h2,h3 {color:#654435;}
[data-testid="stButton"] button {border-radius:15px;min-height:49px;white-space:normal;}
.cookie-message {background:white;border:1px solid #f1d8bd;border-radius:22px;padding:24px;box-shadow:0 7px 20px #9a72551a;}
.cookie-message p {font-size:1.12rem;line-height:1.8;color:#573d2e;}
.cookie-stage {height:230px;position:relative;max-width:340px;margin:0 auto 6px;overflow:hidden;}
.cookie-half {position:absolute;left:50%;top:0; width:205px;height:205px;transform:translateX(-50%);background-size:205px 205px;background-repeat:no-repeat;}
.cookie-left {clip-path:inset(0 50% 0 0); animation:splitLeft 1.8s ease-in-out forwards;}
.cookie-right {clip-path:inset(0 0 0 50%);animation:splitRight 1.8s ease-in-out forwards;}
.cookie-note {position:absolute;z-index:-1;left:50%;top:88px;transform:translateX(-50%);background:#fff4d9;box-shadow:0 2px 12px #b08c6b55;border-radius:5px;padding:18px 25px;font-size:24px;animation:paper 1.8s ease forwards;}
@keyframes splitLeft {0%,28%{transform:translateX(-50%) rotate(0)} 65%,100%{transform:translateX(-81%) rotate(-12deg)}}
@keyframes splitRight {0%,28%{transform:translateX(-50%) rotate(0)} 65%,100%{transform:translateX(-19%) rotate(12deg)}}
@keyframes paper {0%,35%{opacity:0;transform:translate(-50%,12px) scale(.35)} 72%,100%{opacity:1;transform:translate(-50%,0) scale(1)}}
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
            time.sleep(1.85)
            stage.empty()
            st.rerun()

if st.session_state.recorded and st.session_state.result:
    main, extra_type, extra = st.session_state.result
    st.success("오늘의 마음이 선생님께 전달되었어요. 🍀")
    st.markdown("### 🍪 오늘의 마음 메시지")
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
st.caption("이름을 고르는 방식은 본인 확인 기능이 아니에요. 반드시 자기 이름을 선택해 주세요.")
