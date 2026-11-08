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

SAME_LINKS = [
    "비슷한 결의 마음이 겹치면서 감정이 더 또렷해졌을 수도 있어.",
    "두 마음이 함께 드는 건 이상한 일이 아니야.",
    "마음은 꼭 하나씩만 찾아오는 게 아니니까.",
]
DIFFERENT_LINKS = [
    "서로 다른 마음이 함께 드는 것도 자연스러운 일이야.",
    "한 가지 말로 딱 설명되지 않는 마음도 충분히 있을 수 있어.",
    "어떤 하루에는 서로 다른 감정이 나란히 찾아오기도 해.",
]

def make_message(selected):
    chosen = [BY_NAME[name] for name in selected]
    first = chosen[0]
    if len(chosen) == 1:
        message = "\n\n".join([
            random.choice(first["acknowledge"]),
            random.choice(first["perspective"]),
        ])
    else:
        second = chosen[1]
        # The 'mixed' category isn't treated as a positive or negative diagnosis.
        similar = first["family"] == second["family"] or (
            first["category"] == second["category"] and first["category"] != "mixed"
        )
        bridge = random.choice(SAME_LINKS if similar else DIFFERENT_LINKS)
        message = "\n\n".join([
            random.choice(first["acknowledge"]),
            bridge,
            random.choice(second["perspective"]),
        ])
    extra_type = random.choice(["question", "action"])
    extra_source = random.choice(chosen)
    extra = random.choice(extra_source[extra_type])
    return message, extra_type, extra

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
