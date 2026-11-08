"""오늘의 마음쿠키 | Streamlit Community Cloud entrypoint."""
import json
import random
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="오늘의 마음쿠키 🍪", page_icon="🍪", layout="centered")

@st.cache_data

def load_data():
    path = Path(__file__).parent / "emotions.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["emotions"]
    names = [x["name"] for x in items]
    if len(names) != len(set(names)):
        raise ValueError("감정 이름이 중복되어 있습니다.")
    for item in items:
        for field in ("acknowledge", "perspective", "action", "question"):
            if len(item.get(field, [])) < 3:
                raise ValueError(f"{item['name']}의 {field} 문장이 3개 미만입니다.")
    return items

EMOTIONS = load_data()
BY_NAME = {item["name"]: item for item in EMOTIONS}
LABELS = {"positive": "☀️ 밝은 마음", "negative": "🌧️ 무거운 마음", "mixed": "🌈 여러 빛깔의 마음"}

# 감정별로 직접 쓴 첫 문장과 의미군별 문장을 사용합니다.
# 두 감정을 단순히 '같이 느껴도 돼'로 연결하지 않고,
# 밝은 마음은 축하하고 무거운 마음은 존중하는 방향으로 구성합니다.

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


def mood_tone(emotion):
    if emotion["category"] == "positive":
        return "bright"
    if emotion["category"] == "negative":
        return "heavy"
    if emotion["family"] in {"걱정", "당황", "멍함"}:
        return "heavy"
    return "bright"


def make_message(selected):
    chosen = [BY_NAME[name] for name in selected]
    first = chosen[0]
    if len(chosen) == 1:
        tone = mood_tone(first)
        main = [
            first["acknowledge"][0],
            random.choice(first["perspective"]),
            random.choice(POSITIVE_CLOSINGS if tone == "bright" else LOW_CLOSINGS),
        ]
    else:
        second = chosen[1]
        a, b = mood_tone(first), mood_tone(second)
        if a == b == "bright":
            if set(selected) == {"든든한", "쾌활한"}:
                main = [
                    "오늘은 어떤 좋은 일이 있어서 이렇게 든든하고 쾌활한 마음이 들었을까?",
                    "마음이 든든하면 새로운 일을 시작할 힘이 생기고, 밝은 기운은 발걸음을 더 가볍게 해 주지.",
                    "오늘도 네 하루에 기분 좋은 일이 가득하길 바라. 아침의 밝은 에너지가 하루 종일 함께하길!",
                ]
            else:
                main = [
                    first["acknowledge"][0],
                    f"{second['name']} 마음까지 더해졌네. " + random.choice(second["perspective"]),
                    random.choice(POSITIVE_CLOSINGS),
                ]
        elif a == b == "heavy":
            if set(selected) == {"서운한", "화나는"}:
                main = [
                    "기대했던 마음이 있어서 서운했는데, 화까지 났다면 마음이 더 복잡했겠어.",
                    "그럴 때는 무엇이 가장 서운했는지, 무엇 때문에 화가 났는지 하나씩 살펴봐도 좋아.",
                    "지금 바로 해결하려 애쓰지 말고, 네 마음을 차근차근 정리해 보자.",
                ]
            else:
                main = [
                    first["acknowledge"][0],
                    f"{second['name']} 마음도 함께 느껴지는구나. " + random.choice(second["perspective"]),
                    random.choice(LOW_CLOSINGS),
                ]
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
                main = [
                    f"{bright['name']} 마음이 있으면서도 {heavy['name']} 마음이 함께 드는구나.",
                    random.choice(bright["perspective"]) + " " + random.choice(heavy["perspective"]),
                    random.choice(MIXED_CLOSINGS),
                ]
    # 선택한 감정과 어울리는 질문/행동만 보여 줍니다.
    extra_type = random.choice(["question", "action"])
    extra_source = random.choice(chosen)
    extra = random.choice(extra_source[extra_type])
    return "\n\n".join(main), extra_type, extra

st.markdown("""
<style>
.stApp { background: linear-gradient(160deg,#fffaf2 0%,#fff7f1 55%,#fffdfa 100%); }
.block-container { max-width: 820px; padding-top: 2rem; padding-bottom: 4rem; }
h1, h2, h3 { color: #654435; }
[data-testid="stButton"] button { border-radius: 16px; min-height: 49px; white-space: normal; }
div[data-testid="stAlert"] { border-radius: 18px; }
.cookie-output {background:#fff; border:1px solid #f1d8bd; border-radius:22px;
    padding:24px 24px 16px; box-shadow: 0 8px 28px rgba(120,75,40,.06); }
.cookie-output p {font-size:1.12rem; line-height:1.85; color:#523a2c;}
.small-note {font-size:.91rem; color:#786559;}
</style>
""", unsafe_allow_html=True)

st.title("🍪 오늘의 마음쿠키")
st.write("오늘 내 마음은 어떤 모습인가요? 마음에 가까운 카드를 **1~2개** 골라 보세요.")
st.caption("어떤 감정을 골라도 괜찮아요. 정답도, 틀린 감정도 없어요.")

if "selected" not in st.session_state:
    st.session_state.selected = []
if "result" not in st.session_state:
    st.session_state.result = None

search = st.text_input("감정 찾기", placeholder="예: 서운한, 설레는, 긴장되는", label_visibility="visible")
tabs = st.tabs(list(LABELS.values()))
for tab, (category, title) in zip(tabs, LABELS.items()):
    with tab:
        subset = [e for e in EMOTIONS if e["category"] == category and search.strip() in e["name"]]
        if not subset:
            st.info("검색한 감정이 이 목록에는 없어요.")
        for start in range(0, len(subset), 3):
            cols = st.columns(3)
            for col, emotion in zip(cols, subset[start:start+3]):
                name = emotion["name"]
                active = name in st.session_state.selected
                with col:
                    if st.button(("✓ " if active else "") + name, key=f"emotion-{name}",
                                 type="primary" if active else "secondary", use_container_width=True):
                        if active:
                            st.session_state.selected.remove(name)
                        elif len(st.session_state.selected) < 2:
                            st.session_state.selected.append(name)
                        else:
                            st.toast("감정 카드는 두 장까지만 고를 수 있어요.")
                        st.session_state.result = None
                        st.rerun()

selected = st.session_state.selected
st.write("**내가 고른 마음:** " + (" · ".join(selected) if selected else "아직 선택하지 않았어요"))
col1, col2 = st.columns([3, 1])
with col1:
    if st.button("🍪 마음쿠키 열기", disabled=not selected, type="primary", use_container_width=True):
        st.session_state.result = make_message(selected)
with col2:
    if st.button("다시 고르기", use_container_width=True):
        st.session_state.selected = []
        st.session_state.result = None
        st.rerun()

if st.session_state.result:
    main, extra_type, extra = st.session_state.result
    st.markdown("### 🍪 오늘의 마음 메시지")
    st.markdown('<div class="cookie-output">' +
                ''.join(f'<p>{part}</p>' for part in main.split("\n\n")) +
                '</div>', unsafe_allow_html=True)
    st.write("")
    if extra_type == "question":
        st.info("🔎 **마음 질문**\n\n" + extra)
    else:
        st.success("🌱 **오늘의 작은 한 걸음**\n\n" + extra)
    if st.button("🍪 같은 마음으로 다른 메시지 보기", use_container_width=True):
        st.session_state.result = make_message(selected)
        st.rerun()

st.divider()
st.caption("이곳에서는 이름이나 마음 기록을 저장하지 않아요. 선택은 이 화면에서만 사용돼요.")
st.caption("마음이 너무 힘들거나 안전이 걱정된다면, 믿을 만한 어른이나 선생님에게 직접 이야기해 주세요.")
