"""
CardCraft — Multi-Agent Flashcard Generator
Premium Streamlit UI with teacher-gated review, full metrics, study mode.
"""

import os
import json
import time
import tempfile
from pathlib import Path
from typing import List

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="CardCraft AI",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════
# DESIGN SYSTEM
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #070910;
  --bg2:       #0d0f1a;
  --surface:   #111320;
  --surface2:  #181b2e;
  --surface3:  #1e2238;
  --border:    rgba(255,255,255,0.07);
  --border2:   rgba(255,255,255,0.12);
  --violet:    #8b5cf6;
  --violet2:   #a78bfa;
  --indigo:    #6366f1;
  --cyan:      #22d3ee;
  --emerald:   #10b981;
  --amber:     #f59e0b;
  --rose:      #f43f5e;
  --text:      #f1f5f9;
  --text2:     #94a3b8;
  --text3:     #475569;
  --radius:    16px;
  --radius-sm: 10px;
  --font-d: 'Syne', sans-serif;
  --font-b: 'Inter', sans-serif;
  --font-m: 'JetBrains Mono', monospace;
}

html, body, [class*="css"], .stApp {
  font-family: var(--font-b);
  background: var(--bg) !important;
  color: var(--text);
}

/* ── Hide ALL Streamlit chrome ── */
#MainMenu, footer, .stDeployButton,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
header { display: none !important; visibility: hidden !important; height: 0 !important; }

section[data-testid="stSidebar"] { display: none !important; }

/* ── Zero out ALL top padding/margin ── */
html, body { margin: 0 !important; padding: 0 !important; }
.stApp { margin-top: 0 !important; padding-top: 0 !important; overflow-x: hidden; }

/* This is the actual selector Streamlit uses for the main content padding */
.stMainBlockContainer { padding-top: 0rem !important; }
div[class*="main"] > div { padding-top: 0rem !important; }

[data-testid="stAppViewContainer"] { margin-top: 0 !important; padding-top: 0 !important; }
[data-testid="stAppViewContainer"] > section { padding-top: 0 !important; margin-top: 0 !important; }

.block-container,
[data-testid="stMainBlockContainer"] {
  padding-top:    0 !important;
  padding-bottom: 0 !important;
  margin-top:     0 !important;
  max-width:    100% !important;
}

[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] { padding: 0 !important; }

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--surface3); border-radius: 99px; }

/* Background mesh */
.bg-mesh {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
}
.bg-mesh::before {
  content: '';
  position: absolute; inset: -50%;
  background:
    radial-gradient(ellipse 60% 50% at 20% 20%, rgba(139,92,246,0.11) 0%, transparent 60%),
    radial-gradient(ellipse 50% 40% at 80% 80%, rgba(34,211,238,0.07) 0%, transparent 60%),
    radial-gradient(ellipse 40% 60% at 60% 10%, rgba(99,102,241,0.07) 0%, transparent 50%);
  animation: meshMove 22s ease-in-out infinite alternate;
}
.bg-mesh::after {
  content: ''; position: absolute; inset: 0;
  background-image: radial-gradient(circle, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 48px 48px;
}
@keyframes meshMove {
  from { transform: translate(0,0) scale(1); }
  to   { transform: translate(3%,3%) scale(1.05); }
}

/* Nav */
.topnav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 0 0.9rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2rem;
}
.nav-brand { display: flex; align-items: baseline; gap: 0.75rem; }
.nav-title {
  font-family: var(--font-d); font-size: 1.4rem; font-weight: 700;
  background: linear-gradient(90deg, #f1f5f9 0%, var(--violet2) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em; line-height: 1;
}
.nav-sub {
  font-family: var(--font-m); font-size: 0.65rem; color: var(--text3);
  letter-spacing: 0.06em; text-transform: uppercase;
}
.nav-pill {
  display: flex; gap: 0.2rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 99px; padding: 0.3rem;
}
.nav-step {
  font-family: var(--font-m); font-size: 0.68rem; font-weight: 500;
  padding: 0.28rem 0.9rem; border-radius: 99px; letter-spacing: 0.02em;
  color: var(--text3); transition: all 0.2s;
}
.nav-step.active {
  background: linear-gradient(135deg, var(--violet), var(--indigo));
  color: white; box-shadow: 0 2px 12px rgba(139,92,246,0.4);
}
.nav-step.done { color: var(--emerald); }

/* Hero */
.hero { text-align: center; padding: 1.5rem 0 2rem; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 0.4rem;
  background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.22);
  border-radius: 99px; padding: 0.35rem 1rem;
  font-size: 0.74rem; color: var(--violet2);
  font-family: var(--font-m); letter-spacing: 0.05em;
  margin-bottom: 1.5rem;
}
.hero-title {
  font-family: var(--font-d);
  font-size: clamp(2.4rem, 5vw, 3.8rem);
  font-weight: 800; line-height: 1.06;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #f1f5f9 0%, var(--violet2) 50%, var(--cyan) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 1rem;
}
.hero-sub {
  font-size: 1.08rem; color: var(--text2); max-width: 480px;
  margin: 0 auto 2.5rem; line-height: 1.65; font-weight: 300;
}

/* Cards */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.4rem 1.6rem;
  margin-bottom: 0.85rem;
  transition: border-color 0.25s;
}
.card:hover { border-color: var(--border2); }
.card-glow:hover { border-color: rgba(139,92,246,0.3); box-shadow: 0 0 30px rgba(139,92,246,0.12); }

/* Step items */
.step-item {
  display: flex; align-items: flex-start; gap: 0.85rem;
  padding: 0.9rem 1.1rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); transition: all 0.2s; margin-bottom: 0.5rem;
}
.step-item:hover { border-color: rgba(139,92,246,0.28); background: var(--surface2); }
.step-num {
  font-family: var(--font-m); font-size: 0.64rem; color: var(--violet);
  background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.2);
  border-radius: 5px; padding: 0.2rem 0.42rem;
  flex-shrink: 0; margin-top: 0.1rem; letter-spacing: 0.04em;
}
.step-title { font-size: 0.87rem; font-weight: 600; color: var(--text); margin-bottom: 0.18rem; }
.step-desc  { font-size: 0.74rem; color: var(--text3); line-height: 1.45; }

/* Pipeline steps */
.pipe-step {
  display: flex; align-items: center; gap: 1rem;
  padding: 0.9rem 1.1rem; border-radius: var(--radius-sm);
  margin-bottom: 0.5rem; border: 1px solid transparent;
}
.pipe-step.pending { background: var(--surface2); border-color: var(--border); opacity: 0.5; }
.pipe-step.active  { background: rgba(139,92,246,0.07); border-color: rgba(139,92,246,0.2); }
.pipe-step.done    { background: rgba(16,185,129,0.05); border-color: rgba(16,185,129,0.18); }
.pipe-step.error   { background: rgba(244,63,94,0.07); border-color: rgba(244,63,94,0.2); }
.pipe-icon {
  width: 36px; height: 36px; border-radius: 99px;
  display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0;
}
.pipe-icon.pending { background: var(--surface3); }
.pipe-icon.active  { background: rgba(139,92,246,0.18); }
.pipe-icon.done    { background: rgba(16,185,129,0.15); }
.pipe-label { font-size: 0.9rem; font-weight: 600; }
.pipe-detail { font-size: 0.76rem; color: var(--text3); margin-top: 0.1rem; }
.pipe-badge {
  font-family: var(--font-m); font-size: 0.66rem; padding: 0.22rem 0.65rem;
  border-radius: 99px; border: 1px solid;
}
.pipe-badge.pending { color: var(--text3); border-color: var(--border); background: var(--surface3); }
.pipe-badge.active  { color: var(--violet2); border-color: rgba(139,92,246,0.3); background: rgba(139,92,246,0.1); }
.pipe-badge.done    { color: var(--emerald); border-color: rgba(16,185,129,0.3); background: rgba(16,185,129,0.1); }

/* Metrics */
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(115px, 1fr));
  gap: 0.7rem; margin-bottom: 1.75rem;
}
.metric-tile {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 1.1rem 1.2rem;
  transition: border-color 0.2s;
}
.metric-tile:hover { border-color: var(--border2); }
.m-val {
  font-family: var(--font-d); font-size: 2rem; font-weight: 700;
  line-height: 1; margin-bottom: 0.28rem;
}
.m-lbl { font-family: var(--font-m); font-size: 0.63rem; color: var(--text3); letter-spacing: 0.08em; text-transform: uppercase; }
.m-sub { font-size: 0.7rem; color: var(--text3); margin-top: 0.18rem; }

/* Score bars */
.sbar { margin: 0.32rem 0; }
.sbar-hd {
  display: flex; justify-content: space-between;
  font-family: var(--font-m); font-size: 0.67rem; color: var(--text3); margin-bottom: 0.18rem;
}
.sbar-track { background: var(--surface3); border-radius: 99px; height: 4px; overflow: hidden; }
.sbar-fill  { height: 100%; border-radius: 99px; }

/* Chips */
.chip {
  display: inline-flex; align-items: center;
  padding: 0.17em 0.6em; border-radius: 99px;
  font-size: 0.67rem; font-family: var(--font-m);
  letter-spacing: 0.03em; font-weight: 500;
  border: 1px solid; margin-right: 0.22rem;
}
.chip-easy    { color: #34d399; background: rgba(52,211,153,0.1);  border-color: rgba(52,211,153,0.22); }
.chip-medium  { color: #fbbf24; background: rgba(251,191,36,0.1);  border-color: rgba(251,191,36,0.22); }
.chip-hard    { color: #f87171; background: rgba(248,113,113,0.1); border-color: rgba(248,113,113,0.22); }
.chip-bloom   { color: var(--violet2); background: rgba(139,92,246,0.1); border-color: rgba(139,92,246,0.22); }
.chip-type    { color: var(--cyan);    background: rgba(34,211,238,0.08); border-color: rgba(34,211,238,0.18); }
.chip-approve { color: #34d399; background: rgba(52,211,153,0.1);  border-color: rgba(52,211,153,0.22); }
.chip-review  { color: #fbbf24; background: rgba(251,191,36,0.1);  border-color: rgba(251,191,36,0.22); }
.chip-reject  { color: #f87171; background: rgba(248,113,113,0.1); border-color: rgba(248,113,113,0.22); }

/* Review card */
.rcard {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 1.4rem 1.6rem;
  margin-bottom: 0.9rem; transition: border-color 0.25s;
}
.rcard-q { font-size: 1rem; font-weight: 600; color: var(--text); line-height: 1.5; margin-bottom: 0.5rem; }
.rcard-a { font-size: 0.9rem; color: var(--cyan); line-height: 1.5; margin-bottom: 0.9rem; }
.rcard-just {
  font-size: 0.75rem; color: var(--text3); font-style: italic;
  border-top: 1px solid var(--border); padding-top: 0.55rem; margin-top: 0.55rem; line-height: 1.5;
}

/* Flashcard flip */
.fc-scene { perspective: 1200px; width: 100%; height: 210px; cursor: pointer; margin-bottom: 0.5rem; }
.fc-inner {
  position: relative; width: 100%; height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.6s cubic-bezier(0.4,0,0.2,1);
}
.fc-scene.flipped .fc-inner { transform: rotateY(180deg); }
.fc-face {
  position: absolute; inset: 0; backface-visibility: hidden;
  border-radius: var(--radius); display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  padding: 1.5rem; text-align: center; border: 1px solid var(--border);
}
.fc-front { background: var(--surface); }
.fc-back  {
  background: linear-gradient(135deg, #130f2a 0%, var(--surface) 100%);
  border-color: rgba(139,92,246,0.32); transform: rotateY(180deg);
  box-shadow: inset 0 0 60px rgba(139,92,246,0.07);
}
.fc-label { font-family: var(--font-m); font-size: 0.6rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text3); margin-bottom: 0.65rem; }
.fc-text  { font-size: 0.9rem; line-height: 1.55; color: var(--text); }
.fc-ans   { color: var(--cyan); font-weight: 500; }
.fc-hint  { position: absolute; bottom: 0.65rem; right: 0.9rem; font-size: 0.58rem; color: var(--text3); font-family: var(--font-m); opacity: 0.55; }

/* Password gate */
.pw-gate { max-width: 420px; margin: 3rem auto; text-align: center; }
.pw-icon { font-size: 3rem; margin-bottom: 1rem; display: block; filter: drop-shadow(0 0 20px rgba(139,92,246,0.4)); }
.pw-title { font-family: var(--font-d); font-size: 1.65rem; font-weight: 700; color: var(--text); margin-bottom: 0.5rem; }
.pw-sub   { font-size: 0.87rem; color: var(--text3); margin-bottom: 2rem; line-height: 1.55; }
.pw-error { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.25); border-radius: var(--radius-sm); padding: 0.65rem 1rem; font-size: 0.8rem; color: #fda4af; text-align: center; margin-top: 0.75rem; }

/* Section text */
.sec-title { font-family: var(--font-d); font-size: 1.5rem; font-weight: 700; color: var(--text); letter-spacing: -0.02em; margin-bottom: 0.3rem; }
.sec-sub   { font-size: 0.82rem; color: var(--text3); margin-bottom: 1.4rem; line-height: 1.55; }

/* ── Streamlit overrides ── */
div[data-testid="stButton"] > button {
  background: linear-gradient(135deg, var(--violet) 0%, var(--indigo) 100%) !important;
  color: white !important; border: none !important;
  border-radius: var(--radius-sm) !important;
  font-family: var(--font-b) !important; font-weight: 500 !important;
  font-size: 0.87rem !important; padding: 0.58rem 1.3rem !important;
  box-shadow: 0 4px 15px rgba(139,92,246,0.28) !important;
  transition: all 0.2s !important; letter-spacing: 0.01em !important;
}
div[data-testid="stButton"] > button:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 22px rgba(139,92,246,0.42) !important;
}
div[data-testid="stButton"] > button:active { transform: translateY(0) !important; }
div[data-testid="stButton"] > button:disabled { opacity: 0.38 !important; transform: none !important; box-shadow: none !important; }

.btn-ghost > div[data-testid="stButton"] > button {
  background: var(--surface) !important; border: 1px solid var(--border2) !important;
  box-shadow: none !important; color: var(--text2) !important;
}
.btn-ghost > div[data-testid="stButton"] > button:hover {
  background: var(--surface2) !important; box-shadow: none !important; transform: none !important;
}
.btn-approve > div[data-testid="stButton"] > button { background: linear-gradient(135deg,#065f46,#10b981) !important; box-shadow: 0 4px 14px rgba(16,185,129,0.28) !important; }
.btn-reject  > div[data-testid="stButton"] > button { background: linear-gradient(135deg,#9f1239,#f43f5e) !important; box-shadow: 0 4px 14px rgba(244,63,94,0.25) !important; }
.btn-edit    > div[data-testid="stButton"] > button { background: linear-gradient(135deg,#5b21b6,#8b5cf6) !important; }

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
  background: var(--surface2) !important; border: 1px solid var(--border2) !important;
  border-radius: var(--radius-sm) !important; color: var(--text) !important;
  font-family: var(--font-b) !important; font-size: 0.87rem !important; caret-color: var(--violet);
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
  border-color: rgba(139,92,246,0.5) !important; box-shadow: 0 0 0 3px rgba(139,92,246,0.11) !important;
}
div[data-testid="stTextInput"] label, div[data-testid="stTextArea"] label,
div[data-testid="stSelectbox"] label, div[data-testid="stSlider"] label,
div[data-testid="stMultiSelect"] label {
  color: var(--text2) !important; font-size: 0.79rem !important; font-weight: 500 !important;
}
div[data-testid="stSelectbox"] > div > div {
  background: var(--surface2) !important; border: 1px solid var(--border2) !important;
  border-radius: var(--radius-sm) !important; color: var(--text) !important;
}
div[data-testid="stMultiSelect"] > div {
  background: var(--surface2) !important; border: 1px solid var(--border2) !important; border-radius: var(--radius-sm) !important;
}
span[data-baseweb="tag"] { background: rgba(139,92,246,0.18) !important; border: 1px solid rgba(139,92,246,0.3) !important; border-radius: 99px !important; }
div[data-testid="stFileUploader"] > div {
  background: rgba(139,92,246,0.04) !important; border: 2px dashed rgba(139,92,246,0.28) !important;
  border-radius: var(--radius) !important; color: var(--text2) !important;
}
div[data-testid="stFileUploader"] > div:hover { border-color: rgba(139,92,246,0.52) !important; background: rgba(139,92,246,0.07) !important; }
div[data-testid="stProgressBar"] > div { background: var(--surface3) !important; border-radius: 99px !important; height: 6px !important; }
div[data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, var(--violet), var(--cyan)) !important; border-radius: 99px !important; }
div[data-baseweb="tab-list"] {
  background: var(--surface) !important; border-radius: 12px !important;
  padding: 4px !important; gap: 2px !important; border: 1px solid var(--border) !important;
}
button[data-baseweb="tab"] {
  border-radius: 9px !important; font-family: var(--font-b) !important;
  font-size: 0.81rem !important; font-weight: 500 !important;
  color: var(--text3) !important; padding: 0.44rem 1rem !important; transition: all 0.2s !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(135deg,rgba(139,92,246,0.18),rgba(99,102,241,0.12)) !important;
  color: var(--text) !important; border: 1px solid rgba(139,92,246,0.25) !important;
}
div[data-testid="stExpander"] > div:first-child {
  background: var(--surface) !important; border-radius: var(--radius-sm) !important;
  border: 1px solid var(--border) !important; color: var(--text2) !important; font-size: 0.85rem !important;
}
div[data-testid="stExpander"] > div:first-child:hover { border-color: var(--border2) !important; }
div[data-testid="stAlert"] { border-radius: var(--radius-sm) !important; font-size: 0.83rem !important; }
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# CONSTANTS & STATE
# ═══════════════════════════════════════════════════════════
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "cardcraft2024")

def init_state():
    defaults = {
        "step": "upload",
        "chunks": [], "raw_cards": [], "scored_cards": [],
        "approved_cards": [], "human_queue": [], "rejected_cards": [],
        "content_type": "", "source_filename": "",
        "flip_states": {}, "review_decisions": {}, "edit_data": {},
        "gold_count": 0, "teacher_authed": False, "pw_error": False,
        "gen_provider": "gemini", "gen_model": "gemini-2.5-flash",
        "gen_num_cards": 5, "gen_api_key": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
@st.cache_resource
def get_vector_store():
    from vector_store import VectorStoreManager
    vs = VectorStoreManager()
    vs.bootstrap_reference_docs()
    return vs

def get_llm(provider, model, api_key, temperature):
    provider = provider.lower()
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key: st.error("No Gemini API key. Add GEMINI_API_KEY to .env"); st.stop()
        return ChatGoogleGenerativeAI(model=model, temperature=temperature,
                                       google_api_key=key, convert_system_message_to_human=True)
    elif provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        token = api_key or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not token: st.error("No HuggingFace token. Add HF_TOKEN to .env"); st.stop()
        ep = HuggingFaceEndpoint(repo_id=model, huggingfacehub_api_token=token,
                                  temperature=temperature, max_new_tokens=2048, task="text-generation")
        return ChatHuggingFace(llm=ep, huggingfacehub_api_token=token)
    st.error(f"Unknown provider: {provider}"); st.stop()

def sbar(label, value):
    pct = int(value * 100)
    color = "#10b981" if value >= 0.75 else ("#f59e0b" if value >= 0.5 else "#f43f5e")
    return f"""<div class="sbar">
      <div class="sbar-hd"><span>{label}</span><span style="color:{color}">{pct}%</span></div>
      <div class="sbar-track"><div class="sbar-fill" style="width:{pct}%;background:{color}"></div></div>
    </div>"""

def chip(text, kind):
    return f'<span class="chip chip-{kind}">{text}</span>'

def diff_chip(d):
    return chip(d, "easy" if d=="easy" else ("medium" if d=="medium" else "hard"))

def routing_chip(decision):
    if decision == "auto_approve": return chip("✓ auto-approve","approve")
    if decision == "human_review":  return chip("⟳ needs review","review")
    return chip("✗ auto-reject","reject")

def nav_html():
    order   = ["upload","generating","review","study"]
    current = st.session_state.step
    ci      = order.index(current) if current in order else 0
    labels  = ["Upload","Processing","Review","Study"]
    pills   = "".join(
        f'<span class="nav-step {"active" if k==current else ("done" if i<ci else "")}">{labels[i]}</span>'
        for i, k in enumerate(order)
    )
    return f"""<div class="topnav">
      <div class="nav-brand">
        <span class="nav-title">CardCraft</span>
        <span class="nav-sub">by Northeastern Students</span>
      </div>
      <div class="nav-pill">{pills}</div>
      <div style="font-family:var(--font-m);font-size:0.68rem;color:var(--text3);">AI · HITL · Adaptive</div>
    </div>"""

def reset():
    keys = ["step","chunks","raw_cards","scored_cards","approved_cards","human_queue",
            "rejected_cards","content_type","source_filename","flip_states",
            "review_decisions","edit_data","teacher_authed","pw_error"]
    for k in keys:
        if k in st.session_state: del st.session_state[k]
    init_state()

# ── Page shell ──
st.markdown('<div class="bg-mesh"></div>', unsafe_allow_html=True)

# JS: remove the padding-top Streamlit injects at runtime into the main container
st.markdown("""
<script>
(function() {
  function nuke() {
    // Target every element that could add top space
    var selectors = [
      '[data-testid="stAppViewContainer"]',
      '[data-testid="stAppViewContainer"] > section',
      '.block-container',
      '.stMainBlockContainer',
      '[data-testid="stMainBlockContainer"]',
      '.main > .block-container',
    ];
    selectors.forEach(function(sel) {
      document.querySelectorAll(sel).forEach(function(el) {
        el.style.paddingTop    = '0px';
        el.style.marginTop     = '0px';
      });
    });
    // Hide header if still visible
    var hdr = document.querySelector('[data-testid="stHeader"]');
    if (hdr) { hdr.style.display = 'none'; hdr.style.height = '0'; }
  }
  // Run immediately, then after short delays for Streamlit's async renders
  nuke();
  setTimeout(nuke, 100);
  setTimeout(nuke, 400);
  setTimeout(nuke, 1000);
})();
</script>
""", unsafe_allow_html=True)

st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
st.markdown(nav_html(), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# STEP 1 — UPLOAD
# ═══════════════════════════════════════════════════════════════════
if st.session_state.step == "upload":

    st.markdown("""
    <div class="hero">
      <div class="hero-badge">✦ Multi-Agent Pipeline · Teacher-in-the-Loop </div>
      <div class="hero-title">Turn any PDF into<br>a smart flashcard deck</div>
      <div class="hero-sub">Upload lecture notes, textbooks, or research papers. AI generates, evaluates, and lets you refine every card.</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, _, col_r = st.columns([1.15, 0.07, 0.9])

    with col_l:
        # ── Upload card (file uploader always visible, outside expander) ──
        st.markdown("""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.6rem 2rem 1.4rem;">
          <div style="font-family:var(--font-d);font-size:1.15rem;font-weight:700;margin-bottom:0.2rem;">Upload your PDF</div>
          <div style="font-size:0.79rem;color:var(--text3);margin-bottom:1.25rem;">Lectures, textbooks, research papers — anything with text</div>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader("", type=["pdf"], label_visibility="collapsed")

        if uploaded:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.85rem;
                        background:rgba(139,92,246,0.07);border:1px solid rgba(139,92,246,0.22);
                        border-radius:var(--radius-sm);padding:0.9rem 1.1rem;margin:0.5rem 0 0.75rem;">
              <span style="font-size:1.6rem;">📄</span>
              <div>
                <div style="font-weight:600;font-size:0.92rem;">{uploaded.name}</div>
                <div style="font-size:0.74rem;color:var(--text3);margin-top:0.12rem;">{uploaded.size/1024:.1f} KB · PDF</div>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # ── Cards to generate slider — right below uploader ──
        num_cards = st.slider("Number of cards to generate", 3, 20,
                              st.session_state.gen_num_cards, key="cards_slider")
        st.session_state.gen_num_cards = num_cards

        st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)

        if uploaded:
            if st.button("🚀 Generate Flashcards", use_container_width=True):
                st.session_state.source_filename = uploaded.name
                st.session_state.step = "generating"
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded.read())
                    st.session_state._tmp_pdf = tmp.name
                st.rerun()
        else:
            st.button("🚀 Generate Flashcards", use_container_width=True, disabled=True)

        # ── Support notice ──
        st.markdown("""
        <div style="margin-top:1.25rem;background:rgba(34,211,238,0.04);border:1px solid rgba(34,211,238,0.15);
                    border-radius:var(--radius-sm);padding:0.85rem 1.1rem;">
          <div style="font-size:0.78rem;font-weight:600;color:var(--cyan);margin-bottom:0.3rem;">⚠ Having trouble generating cards?</div>
          <div style="font-size:0.74rem;color:var(--text3);line-height:1.55;margin-bottom:0.65rem;">
            If the platform isn't working, your API key may be expired or invalid.
            Try replacing it in the Settings below, or contact us and we'll help you get started.
          </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("✉ Contact Support", use_container_width=True, key="support_btn"):
            st.markdown("""
            <script>window.location.href = 'mailto:cardcraft-support@northeastern.edu?subject=CardCraft%20Issue&body=Hi%20team%2C%20I%20am%20having%20trouble%20with%20the%20CardCraft%20platform.%0A%0AIssue%3A%20';</script>
            """, unsafe_allow_html=True)
            st.info("Opening your email client… If it doesn't open, email us at **cardcraft-support@northeastern.edu**")

    with col_r:
        # ── How it works ──
        st.markdown("""
        <div style="padding-top:0.25rem;">
          <div style="font-family:var(--font-d);font-size:1.12rem;font-weight:700;margin-bottom:1rem;">How it works</div>
        """, unsafe_allow_html=True)
        for num, title, desc in [
            ("01","Extract",       "PDF text extraction with content-aware chunking for code, math & theory"),
            ("02","Generate",      "LLM produces flashcards grounded in your material with Bloom's taxonomy"),
            ("03","Quality Check", "AI judge scores every card on groundedness, clarity, uniqueness & difficulty"),
            ("04","Teacher Review","Password-protected — approve, edit, or reject borderline cards"),
            ("05","Study",         "Interactive flip-card study mode with filters & Anki-compatible export"),
        ]:
            st.markdown(f"""
            <div class="step-item">
              <span class="step-num">{num}</span>
              <div><div class="step-title">{title}</div><div class="step-desc">{desc}</div></div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

        # ── Settings (collapsed by default, below how it works) ──
        with st.expander("⚙️ Generation Settings", expanded=False):

            # Provider selector — drives everything else reactively
            PROVIDERS = {
                "gemini":      {"label": "Google Gemini",      "default_model": "gemini-2.5-flash",                    "key_label": "Gemini API Key",      "key_link": "https://ai.google.dev/gemini-api/docs/api-key",      "key_site": "ai.google.dev",      "key_env": "GEMINI_API_KEY"},
                "huggingface": {"label": "HuggingFace (Llama)","default_model": "meta-llama/Llama-3.1-8B-Instruct",    "key_label": "HuggingFace Token",   "key_link": "https://huggingface.co/settings/tokens",             "key_site": "huggingface.co",     "key_env": "HF_TOKEN"},
            }

            provider = st.radio(
                "LLM Provider",
                options=list(PROVIDERS.keys()),
                format_func=lambda x: PROVIDERS[x]["label"],
                index=0 if st.session_state.gen_provider == "gemini" else 1,
                horizontal=True,
                key="settings_provider_radio",
            )

            # When provider changes, reset the stored model to the new default
            if provider != st.session_state.gen_provider:
                st.session_state.gen_provider = provider
                st.session_state.gen_model = PROVIDERS[provider]["default_model"]

            cfg = PROVIDERS[provider]

            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.5rem;margin:0.6rem 0 0.4rem;
                        padding:0.55rem 0.85rem;background:var(--surface2);
                        border:1px solid var(--border);border-radius:var(--radius-sm);">
              <span style="font-size:0.9rem;">{"🔵" if provider=="gemini" else "🤗"}</span>
              <div>
                <div style="font-size:0.78rem;font-weight:600;color:var(--text);">{cfg["label"]}</div>
                <div style="font-size:0.7rem;color:var(--text3);">Default model: <code style="color:var(--violet2)">{cfg["default_model"]}</code></div>
              </div>
            </div>""", unsafe_allow_html=True)

            model = st.text_input(
                "Model name",
                value=st.session_state.gen_model,
                placeholder=cfg["default_model"],
                key=f"settings_model_{provider}",   # key changes with provider → forces fresh widget
            )

            api_key_in = st.text_input(
                cfg["key_label"],
                type="password",
                placeholder=f"Leave blank to use {cfg['key_env']} from .env",
                value=st.session_state.gen_api_key,
                key=f"settings_apikey_{provider}",
            )

            st.markdown(f"""
            <div style="font-size:0.71rem;color:var(--text3);margin-top:0.5rem;line-height:1.6;
                        border-top:1px solid var(--border);padding-top:0.55rem;">
              💡 Get a free {cfg["key_label"]} at
              <a href="{cfg["key_link"]}" target="_blank"
                 style="color:var(--violet2);text-decoration:none;">{cfg["key_site"]}</a>
              &nbsp;·&nbsp; or set <code style="color:var(--violet2)">{cfg["key_env"]}</code> in your <code>.env</code>
            </div>""", unsafe_allow_html=True)

            # Persist to session state immediately
            st.session_state.gen_provider = provider
            st.session_state.gen_model    = model
            st.session_state.gen_api_key  = api_key_in


# ═══════════════════════════════════════════════════════════════════
# STEP 2 — GENERATING
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.step == "generating":

    st.markdown(f"""
    <div style="margin-bottom:1.75rem;">
      <div class="sec-title">Processing <span style="color:var(--violet2)">{st.session_state.source_filename}</span></div>
      <div class="sec-sub">Running 4-stage multi-agent pipeline — ~30–60 seconds</div>
    </div>""", unsafe_allow_html=True)

    prog   = st.progress(0)
    status = st.empty()

    PIPE = [
        ("📄","Text Extraction",    "Extracting and cleaning text from PDF"),
        ("🔍","Content Analysis",   "Detecting content type & creating semantic chunks"),
        ("✨","Card Generation",    "LLM generating flashcards with Bloom's guidance"),
        ("🎯","Quality Evaluation", "AI judge scoring each card on 4 dimensions"),
    ]
    holders = []
    for icon, label, detail in PIPE:
        h = st.empty()
        h.markdown(f"""<div class="pipe-step pending">
          <div class="pipe-icon pending">{icon}</div>
          <div style="flex:1"><div class="pipe-label" style="color:var(--text3)">{label}</div><div class="pipe-detail">{detail}</div></div>
          <span class="pipe-badge pending">waiting</span></div>""", unsafe_allow_html=True)
        holders.append(h)

    def upd(idx, state, detail_override=""):
        icon, label, detail = PIPE[idx]
        d = detail_override or detail
        badge_txt = {"active":"running","done":"complete","error":"error","pending":"waiting"}[state]
        holders[idx].markdown(f"""<div class="pipe-step {state}">
          <div class="pipe-icon {state}">{icon}</div>
          <div style="flex:1"><div class="pipe-label">{label}</div><div class="pipe-detail">{d}</div></div>
          <span class="pipe-badge {state}">{badge_txt}</span></div>""", unsafe_allow_html=True)

    try:
        api_key   = st.session_state.gen_api_key or None
        provider  = st.session_state.gen_provider
        model     = st.session_state.gen_model
        num_cards = st.session_state.gen_num_cards
        vs        = get_vector_store()

        upd(0,"active"); prog.progress(8)
        from agents.content_extraction import extract_text_from_pdf, content_extraction_node
        pdf_text = extract_text_from_pdf(st.session_state._tmp_pdf)
        if not pdf_text.strip():
            st.error("❌ No text extracted — is this a scanned/image-only PDF?"); st.stop()
        upd(0,"done", f"Extracted {len(pdf_text):,} characters"); prog.progress(22)

        upd(1,"active"); prog.progress(27)
        llm   = get_llm(provider, model, api_key, 0.7)
        state = {"pdf_content": pdf_text, "source_filename": st.session_state.source_filename}
        res   = content_extraction_node(state, vs, llm); state.update(res)
        ctype  = state.get("content_type","theory")
        chunks = state.get("chunks",[])
        if not chunks: st.error("❌ No chunks produced."); st.stop()
        st.session_state.content_type = ctype; st.session_state.chunks = chunks
        upd(1,"done", f"Type: {ctype} · {len(chunks)} chunks"); prog.progress(46)

        upd(2,"active"); prog.progress(50)
        from agents.flashcard_generation import flashcard_generation_node
        gen_res   = flashcard_generation_node(state, vs, llm, cards_per_batch=num_cards); state.update(gen_res)
        raw_cards = state.get("raw_cards",[])
        if not raw_cards: st.error(f"❌ Generation failed: {state.get('error','')}"); st.stop()
        st.session_state.raw_cards = raw_cards
        upd(2,"done", f"Generated {len(raw_cards)} flashcards"); prog.progress(72)

        upd(3,"active"); prog.progress(77)
        from agents.quality_check import quality_check_node
        qllm  = get_llm(provider, model, api_key, 0.2)
        qres  = quality_check_node(state, qllm); state.update(qres)
        st.session_state.scored_cards   = state.get("scored_cards",[])
        st.session_state.approved_cards = list(state.get("approved_cards",[]))
        st.session_state.human_queue    = state.get("human_queue",[])
        st.session_state.rejected_cards = state.get("rejected_cards",[])
        st.session_state.gold_count     = vs.get_gold_count()
        na, nh, nr = len(st.session_state.approved_cards), len(st.session_state.human_queue), len(st.session_state.rejected_cards)
        upd(3,"done", f"{na} auto-approved · {nh} need review · {nr} rejected"); prog.progress(100)

        try: os.unlink(st.session_state._tmp_pdf)
        except: pass
        time.sleep(0.7)
        st.session_state.step = "review"; st.rerun()

    except Exception as e:
        st.error(f"❌ Pipeline error: {e}")
        import traceback
        with st.expander("Full traceback"): st.code(traceback.format_exc())
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("↩ Back to Upload"): st.session_state.step = "upload"; st.rerun()


# ═══════════════════════════════════════════════════════════════════
# STEP 3 — TEACHER REVIEW  (Password Gated)
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.step == "review":

    # ── Password gate ──────────────────────────────────────────────
    if not st.session_state.teacher_authed:
        st.markdown("""
        <div class="pw-gate">
          <span class="pw-icon">🔐</span>
          <div class="pw-title">Teacher Access</div>
          <div class="pw-sub">This review dashboard is restricted to educators.<br>Enter the teacher password to access quality metrics, approve or edit cards, and build your gold example library.</div>
        </div>""", unsafe_allow_html=True)

        _, col_mid, _ = st.columns([1,1.4,1])
        with col_mid:
            pw = st.text_input("", type="password", placeholder="Enter teacher password…",
                               label_visibility="collapsed")
            if st.button("🔓 Unlock Review Dashboard", use_container_width=True):
                if pw == TEACHER_PASSWORD:
                    st.session_state.teacher_authed = True
                    st.session_state.pw_error = False
                    st.rerun()
                else:
                    st.session_state.pw_error = True; st.rerun()

            if st.session_state.pw_error:
                st.markdown('<div class="pw-error">✗ Incorrect password. Please try again.</div>', unsafe_allow_html=True)

            st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
            st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
            if st.button("→ Skip to Study Mode (auto-approve all)", use_container_width=True):
                all_cards = list(st.session_state.approved_cards)
                for sc in st.session_state.human_queue: all_cards.append(sc.card)
                st.session_state.approved_cards = all_cards
                st.session_state.step = "study"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown(f"""
            <div style="margin-top:1.25rem;text-align:center;font-size:0.71rem;color:var(--text3);line-height:1.6;">
              Default password: <code style="color:var(--violet2);background:rgba(139,92,246,0.1);padding:0.1em 0.45em;border-radius:4px;">{TEACHER_PASSWORD}</code><br>
              Set <code>TEACHER_PASSWORD</code> in your <code>.env</code> to change it
            </div>""", unsafe_allow_html=True)
        st.stop()

    # ── Authenticated Dashboard ────────────────────────────────────
    auto_approved = st.session_state.approved_cards
    human_queue   = st.session_state.human_queue
    rejected      = st.session_state.rejected_cards
    scored        = st.session_state.scored_cards
    decisions     = st.session_state.review_decisions
    edit_data     = st.session_state.edit_data

    scores_list = [s.composite_score for s in scored] if scored else [0]
    avg_score   = sum(scores_list)/len(scores_list)
    high_n      = sum(1 for s in scores_list if s>=0.8)
    mid_n       = sum(1 for s in scores_list if 0.5<=s<0.8)
    low_n       = sum(1 for s in scores_list if s<0.5)

    # Header row
    col_hd, col_hb = st.columns([3,1])
    with col_hd:
        st.markdown(f"""
        <div>
          <div class="sec-title">Teacher Review Dashboard</div>
          <div class="sec-sub">
            <b style="color:var(--text)">{st.session_state.source_filename}</b> ·
            Content type: <b style="color:var(--violet2)">{st.session_state.content_type}</b>
          </div>
        </div>""", unsafe_allow_html=True)
    with col_hb:
        st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
        if st.button("↩ New Upload", use_container_width=True): reset(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Metrics
    st.markdown(f"""
    <div class="metric-strip">
      <div class="metric-tile"><div class="m-val">{len(scored)}</div><div class="m-lbl">Total Generated</div></div>
      <div class="metric-tile"><div class="m-val" style="color:#10b981">{len(auto_approved)}</div><div class="m-lbl">Auto-Approved</div><div class="m-sub">score ≥ 0.80</div></div>
      <div class="metric-tile"><div class="m-val" style="color:#f59e0b">{len(human_queue)}</div><div class="m-lbl">Needs Review</div><div class="m-sub">score 0.50–0.80</div></div>
      <div class="metric-tile"><div class="m-val" style="color:#f43f5e">{len(rejected)}</div><div class="m-lbl">Auto-Rejected</div><div class="m-sub">score &lt; 0.50</div></div>
      <div class="metric-tile"><div class="m-val" style="color:var(--violet2)">{avg_score:.2f}</div><div class="m-lbl">Avg Quality</div></div>
      <div class="metric-tile"><div class="m-val" style="color:var(--cyan)">{st.session_state.gold_count}</div><div class="m-lbl">Gold Examples</div></div>
    </div>""", unsafe_allow_html=True)

    tab_q, tab_met, tab_auto, tab_rej = st.tabs([
        f"👩‍🏫 Review Queue ({len(human_queue)})",
        f"📊 Quality Metrics ({len(scored)})",
        f"✅ Auto-Approved ({len(auto_approved)})",
        f"✗ Auto-Rejected ({len(rejected)})",
    ])

    # ── TAB 1: REVIEW QUEUE ─────────────────────────────────────
    with tab_q:
        if not human_queue:
            st.markdown(f"""
            <div style="text-align:center;padding:3.5rem 1rem;">
              <div style="font-size:3rem;margin-bottom:0.75rem;">🎉</div>
              <div style="font-family:var(--font-d);font-size:1.25rem;font-weight:700;margin-bottom:0.4rem;">All {len(auto_approved)} cards auto-approved!</div>
              <div style="color:var(--text3);font-size:0.85rem;">No borderline cards to review. Click Finalize below.</div>
            </div>""", unsafe_allow_html=True)
        else:
            reviewed_n = len(decisions)
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem;">
              <div>
                <div style="font-size:0.9rem;font-weight:600;">Borderline Cards — {len(human_queue)} to review</div>
                <div style="font-size:0.77rem;color:var(--text3);margin-top:0.12rem;">Scored 0.50–0.80. Approve, edit, or reject each card. Edits become gold examples.</div>
              </div>
              <div style="font-family:var(--font-m);font-size:0.76rem;color:var(--text3);
                          background:var(--surface2);border:1px solid var(--border);
                          border-radius:99px;padding:0.28rem 0.85rem;flex-shrink:0;">
                {reviewed_n}/{len(human_queue)} reviewed
              </div>
            </div>""", unsafe_allow_html=True)

            for i, sc in enumerate(human_queue):
                card     = sc.card
                decision = decisions.get(i)
                comp     = sc.composite_score
                border   = {"approve":"rgba(16,185,129,0.38)","edit":"rgba(139,92,246,0.38)",
                            "reject":"rgba(244,63,94,0.3)"}.get(decision,"var(--border)")

                st.markdown(f"""
                <div class="rcard" style="border-color:{border}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.65rem;">
                    <div>{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                    <div style="display:flex;align-items:center;gap:0.5rem;flex-shrink:0;">
                      {routing_chip(sc.routing_decision)}
                      <span style="font-family:var(--font-m);font-size:0.85rem;font-weight:700;
                                   color:{'#10b981' if comp>=0.8 else '#f59e0b' if comp>=0.5 else '#f43f5e'}">{comp:.3f}</span>
                    </div>
                  </div>
                  <div class="rcard-q">Q: {card.question}</div>
                  <div class="rcard-a">A: {card.answer}</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 1.5rem;">
                    {sbar("Groundedness ×0.4",sc.groundedness)}
                    {sbar("Clarity ×0.3",sc.clarity)}
                    {sbar("Uniqueness ×0.2",sc.uniqueness)}
                    {sbar("Difficulty Cal. ×0.1",sc.difficulty_calibration)}
                  </div>
                  <div class="rcard-just">💬 {sc.justification}</div>
                </div>""", unsafe_allow_html=True)

                c1,c2,c3 = st.columns(3)
                with c1:
                    st.markdown('<div class="btn-approve">', unsafe_allow_html=True)
                    if st.button("✓ Approve", key=f"app_{i}", use_container_width=True):
                        decisions[i]="approve"; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<div class="btn-edit">', unsafe_allow_html=True)
                    if st.button("✏️ Edit", key=f"edt_{i}", use_container_width=True):
                        decisions[i]="edit"; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c3:
                    st.markdown('<div class="btn-reject">', unsafe_allow_html=True)
                    if st.button("✗ Reject", key=f"rej_{i}", use_container_width=True):
                        decisions[i]="reject"; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                if decision == "edit":
                    ed = edit_data.get(i, {"q":card.question,"a":card.answer})
                    with st.expander("✏️ Edit card", expanded=True):
                        nq = st.text_area("Question", value=ed.get("q",card.question), key=f"eq_{i}", height=80)
                        na = st.text_area("Answer",   value=ed.get("a",card.answer),   key=f"ea_{i}", height=80)
                        edit_data[i] = {"q":nq,"a":na}

                if decision:
                    labels = {"approve":"✓ Approved","edit":"✏️ Marked for editing","reject":"✗ Rejected"}
                    colors = {"approve":"#10b981","edit":"#a78bfa","reject":"#f43f5e"}
                    st.markdown(f'<div style="font-size:0.75rem;color:{colors[decision]};margin-bottom:0.5rem;padding-left:0.2rem;">{labels[decision]}</div>', unsafe_allow_html=True)
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        # ── Finalize bar ──
        st.markdown("<hr>", unsafe_allow_html=True)
        total_final = len(auto_approved) + sum(1 for d in decisions.values() if d in ("approve","edit"))
        fc1, fc2 = st.columns([3,1])
        with fc1:
            st.markdown(f"""
            <div style="padding:0.4rem 0">
              <div style="font-size:0.9rem;font-weight:600">
                Final deck: <span style="color:var(--violet2)">{total_final} cards</span>
              </div>
              <div style="font-size:0.74rem;color:var(--text3);margin-top:0.15rem">
                {len(auto_approved)} auto-approved + {sum(1 for d in decisions.values() if d in ("approve","edit"))} from review queue
              </div>
            </div>""", unsafe_allow_html=True)
        with fc2:
            if st.button("📚 Finalize & Study →", use_container_width=True):
                from core.models import Flashcard as FC
                teacher_edits = []
                final_approved = list(auto_approved)
                for i, sc in enumerate(human_queue):
                    card = sc.card
                    dec  = decisions.get(i,"reject")
                    if dec == "approve":
                        final_approved.append(card)
                    elif dec == "edit":
                        ed = edit_data.get(i,{})
                        edited = FC(question=ed.get("q",card.question), answer=ed.get("a",card.answer),
                                    difficulty=card.difficulty, bloom_level=card.bloom_level,
                                    source_chunk_id=card.source_chunk_id, question_type=card.question_type)
                        final_approved.append(edited)
                        teacher_edits.append(edited)
                if teacher_edits:
                    vs = get_vector_store()
                    for ed in teacher_edits:
                        vs.add_gold_flashcard({"question":ed.question,"answer":ed.answer,
                                               "difficulty":ed.difficulty,"bloom_level":ed.bloom_level,
                                               "question_type":ed.question_type})
                    st.session_state.gold_count = vs.get_gold_count()
                st.session_state.approved_cards = final_approved
                st.session_state.step = "study"; st.rerun()

    # ── TAB 2: QUALITY METRICS ───────────────────────────────────
    with tab_met:
        if not scored:
            st.info("No scored cards.")
        else:
            st.markdown(f"""
            <div style="margin-bottom:1.1rem;">
              <div style="font-size:0.87rem;font-weight:600;margin-bottom:0.2rem;">Quality Distribution</div>
              <div style="font-size:0.76rem;color:var(--text3);">
                Composite = 0.4 × Groundedness + 0.3 × Clarity + 0.2 × Uniqueness + 0.1 × Difficulty Cal.
              </div>
            </div>
            <div class="metric-strip" style="margin-bottom:1.6rem;">
              <div class="metric-tile"><div class="m-val" style="color:#10b981">{high_n}</div><div class="m-lbl">High ≥0.8</div></div>
              <div class="metric-tile"><div class="m-val" style="color:#f59e0b">{mid_n}</div><div class="m-lbl">Mid 0.5–0.8</div></div>
              <div class="metric-tile"><div class="m-val" style="color:#f43f5e">{low_n}</div><div class="m-lbl">Low &lt;0.5</div></div>
              <div class="metric-tile"><div class="m-val">{avg_score:.3f}</div><div class="m-lbl">Mean Score</div></div>
              <div class="metric-tile"><div class="m-val">{max(scores_list):.3f}</div><div class="m-lbl">Best</div></div>
              <div class="metric-tile"><div class="m-val">{min(scores_list):.3f}</div><div class="m-lbl">Worst</div></div>
            </div>""", unsafe_allow_html=True)

            for sc in sorted(scored, key=lambda x: x.composite_score, reverse=True):
                card  = sc.card; comp = sc.composite_score
                cc    = "#10b981" if comp>=0.8 else ("#f59e0b" if comp>=0.5 else "#f43f5e")
                st.markdown(f"""
                <div class="rcard">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.45rem;">
                    <div style="font-size:0.88rem;font-weight:600;flex:1;margin-right:1rem;line-height:1.4">
                      {card.question[:100]}{'…' if len(card.question)>100 else ''}
                    </div>
                    <div style="display:flex;align-items:center;gap:0.45rem;flex-shrink:0">
                      {routing_chip(sc.routing_decision)}
                      <span style="font-family:var(--font-m);font-size:0.85rem;font-weight:700;color:{cc}">{comp:.3f}</span>
                    </div>
                  </div>
                  <div style="margin-bottom:0.55rem">{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 1.5rem">
                    {sbar("Groundedness",sc.groundedness)}{sbar("Clarity",sc.clarity)}
                    {sbar("Uniqueness",sc.uniqueness)}{sbar("Difficulty Cal.",sc.difficulty_calibration)}
                  </div>
                  <div class="rcard-just">💬 {sc.justification}</div>
                </div>""", unsafe_allow_html=True)

    # ── TAB 3: AUTO-APPROVED ─────────────────────────────────────
    with tab_auto:
        if not auto_approved:
            st.info("No cards were auto-approved.")
        else:
            st.markdown(f'<div class="sec-sub">{len(auto_approved)} cards scored ≥0.80 and passed automatically.</div>', unsafe_allow_html=True)
            for card in auto_approved:
                sc_m  = next((s for s in scored if s.card.question==card.question), None)
                sc_txt = f"{sc_m.composite_score:.3f}" if sc_m else "—"
                st.markdown(f"""
                <div class="rcard card-glow">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                    <div>{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                    <span style="font-family:var(--font-m);font-size:0.78rem;color:#10b981;font-weight:600">{sc_txt}</span>
                  </div>
                  <div class="rcard-q">Q: {card.question}</div>
                  <div class="rcard-a">A: {card.answer}</div>
                </div>""", unsafe_allow_html=True)

    # ── TAB 4: AUTO-REJECTED ─────────────────────────────────────
    with tab_rej:
        if not rejected:
            st.info("No cards were auto-rejected.")
        else:
            st.markdown(f'<div class="sec-sub">{len(rejected)} cards scored below 0.50 and were automatically rejected.</div>', unsafe_allow_html=True)
            for sc in rejected:
                card = sc.card
                st.markdown(f"""
                <div class="rcard" style="border-color:rgba(244,63,94,0.14);opacity:0.72">
                  <div style="display:flex;justify-content:space-between;margin-bottom:0.4rem">
                    <div>{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}</div>
                    <span style="font-family:var(--font-m);font-size:0.78rem;color:#f43f5e;font-weight:600">{sc.composite_score:.3f}</span>
                  </div>
                  <div style="font-size:0.88rem;color:var(--text2);margin-bottom:0.28rem">Q: {card.question}</div>
                  <div style="font-size:0.82rem;color:var(--text3)">A: {card.answer}</div>
                  <div class="rcard-just">💬 {sc.justification}</div>
                </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# STEP 4 — STUDY MODE
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.step == "study":

    final_deck  = st.session_state.approved_cards
    scored      = st.session_state.scored_cards
    scores_list = [s.composite_score for s in scored] if scored else [0]
    avg_s       = sum(scores_list)/len(scores_list)

    if not final_deck:
        st.warning("No approved cards.")
        if st.button("↩ Back to Review"): st.session_state.step="review"; st.rerun()
        st.stop()

    sh, sb = st.columns([3,1])
    with sh:
        st.markdown(f"""
        <div>
          <div class="sec-title">Study Mode</div>
          <div class="sec-sub"><b style="color:var(--text)">{st.session_state.source_filename}</b> · {len(final_deck)} cards · {st.session_state.content_type}</div>
        </div>""", unsafe_allow_html=True)
    with sb:
        sb1, sb2 = st.columns(2)
        with sb1:
            st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
            if st.button("← Review", use_container_width=True): st.session_state.step="review"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with sb2:
            st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
            if st.button("↩ New", use_container_width=True): reset(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metric-strip" style="grid-template-columns:repeat(4,1fr);margin-bottom:1.5rem">
      <div class="metric-tile"><div class="m-val" style="color:var(--violet2)">{len(final_deck)}</div><div class="m-lbl">Final Cards</div></div>
      <div class="metric-tile"><div class="m-val" style="color:var(--cyan)">{st.session_state.content_type or "—"}</div><div class="m-lbl">Content Type</div></div>
      <div class="metric-tile"><div class="m-val" style="color:#f59e0b">{st.session_state.gold_count}</div><div class="m-lbl">Gold Examples</div></div>
      <div class="metric-tile"><div class="m-val">{avg_s:.2f}</div><div class="m-lbl">Avg Quality</div></div>
    </div>""", unsafe_allow_html=True)

    tab_fc, tab_list, tab_mets, tab_exp = st.tabs([
        "🃏 Flashcards", "📋 Card List",
        f"📊 Quality Metrics ({len(scored)})", "💾 Export"
    ])

    # ── Flashcards ──────────────────────────────────────────────
    with tab_fc:
        fc1,fc2,fc3 = st.columns(3)
        with fc1: filter_diff  = st.multiselect("Difficulty",["easy","medium","hard"],default=["easy","medium","hard"])
        with fc2: filter_bloom = st.multiselect("Bloom Level",["remember","understand","apply","analyze","evaluate","create"],default=["remember","understand","apply","analyze","evaluate","create"])
        with fc3: filter_type  = st.multiselect("Type",["definition","concept","application","comparison"],default=["definition","concept","application","comparison"])

        filtered = [c for c in final_deck if c.difficulty in filter_diff and c.bloom_level in filter_bloom and c.question_type in filter_type]

        if not filtered:
            st.info("No cards match your filters.")
        else:
            st.markdown(f'<div style="font-size:0.77rem;color:var(--text3);margin-bottom:1.25rem">{len(filtered)} cards · click to flip</div>', unsafe_allow_html=True)
            for row_start in range(0, len(filtered), 3):
                row_cards = filtered[row_start:row_start+3]
                cols = st.columns(3)
                for ci, card in enumerate(row_cards):
                    idx     = row_start+ci
                    flipped = st.session_state.flip_states.get(idx,False)
                    with cols[ci]:
                        st.markdown(f"""
                        <div class="fc-scene{"  flipped" if flipped else ""}">
                          <div class="fc-inner">
                            <div class="fc-face fc-front">
                              <div class="fc-label">Question</div>
                              <div class="fc-text">{card.question}</div>
                              <span class="fc-hint">tap to reveal →</span>
                            </div>
                            <div class="fc-face fc-back">
                              <div class="fc-label" style="color:var(--cyan)">Answer</div>
                              <div class="fc-text fc-ans">{card.answer}</div>
                              <span class="fc-hint">← tap to hide</span>
                            </div>
                          </div>
                        </div>""", unsafe_allow_html=True)
                        lbl = "↩ Hide" if flipped else "👁 Reveal"
                        if st.button(lbl, key=f"flip_{idx}", use_container_width=True):
                            st.session_state.flip_states[idx] = not flipped; st.rerun()
                        st.markdown(f'<div style="text-align:center;margin:0.3rem 0 0.85rem">{diff_chip(card.difficulty)}{chip(card.bloom_level,"bloom")}</div>', unsafe_allow_html=True)

    # ── Card List ────────────────────────────────────────────────
    with tab_list:
        st.markdown('<div class="sec-sub">All approved flashcards in list view.</div>', unsafe_allow_html=True)
        for i, card in enumerate(final_deck):
            with st.expander(f"Card {i+1} — {card.question[:75]}{'…' if len(card.question)>75 else ''}"):
                st.markdown(f"""
                <div style="margin-bottom:0.5rem">{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                <div style="font-weight:600;margin-bottom:0.4rem;line-height:1.5">Q: {card.question}</div>
                <div style="color:var(--cyan);line-height:1.5">A: {card.answer}</div>
                <div style="font-size:0.7rem;color:var(--text3);margin-top:0.4rem;font-family:var(--font-m)">source: {card.source_chunk_id}</div>""", unsafe_allow_html=True)

    # ── Quality Metrics ──────────────────────────────────────────
    with tab_mets:
        if not scored:
            st.info("No quality scores.")
        else:
            high_s = sum(1 for s in scores_list if s>=0.8)
            mid_s  = sum(1 for s in scores_list if 0.5<=s<0.8)
            low_s  = sum(1 for s in scores_list if s<0.5)
            st.markdown(f"""
            <div class="sec-sub">Composite = 0.4×Groundedness + 0.3×Clarity + 0.2×Uniqueness + 0.1×Difficulty Cal.</div>
            <div class="metric-strip" style="margin-bottom:1.6rem">
              <div class="metric-tile"><div class="m-val" style="color:#10b981">{high_s}</div><div class="m-lbl">High ≥0.8</div></div>
              <div class="metric-tile"><div class="m-val" style="color:#f59e0b">{mid_s}</div><div class="m-lbl">Mid 0.5–0.8</div></div>
              <div class="metric-tile"><div class="m-val" style="color:#f43f5e">{low_s}</div><div class="m-lbl">Low &lt;0.5</div></div>
              <div class="metric-tile"><div class="m-val">{avg_s:.3f}</div><div class="m-lbl">Mean</div></div>
              <div class="metric-tile"><div class="m-val">{max(scores_list):.3f}</div><div class="m-lbl">Best</div></div>
              <div class="metric-tile"><div class="m-val">{min(scores_list):.3f}</div><div class="m-lbl">Worst</div></div>
            </div>""", unsafe_allow_html=True)
            for sc in sorted(scored, key=lambda x: x.composite_score, reverse=True):
                card=sc.card; comp=sc.composite_score
                cc="#10b981" if comp>=0.8 else ("#f59e0b" if comp>=0.5 else "#f43f5e")
                st.markdown(f"""
                <div class="rcard">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem">
                    <div style="font-size:0.87rem;font-weight:600;flex:1;margin-right:1rem">{card.question[:95]}{'…' if len(card.question)>95 else ''}</div>
                    <div style="display:flex;gap:0.4rem;align-items:center;flex-shrink:0">
                      {routing_chip(sc.routing_decision)}
                      <span style="font-family:var(--font-m);font-size:0.85rem;font-weight:700;color:{cc}">{comp:.3f}</span>
                    </div>
                  </div>
                  <div style="margin-bottom:0.5rem">{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 1.5rem">
                    {sbar("Groundedness",sc.groundedness)}{sbar("Clarity",sc.clarity)}
                    {sbar("Uniqueness",sc.uniqueness)}{sbar("Difficulty Cal.",sc.difficulty_calibration)}
                  </div>
                  <div class="rcard-just">💬 {sc.justification}</div>
                </div>""", unsafe_allow_html=True)

    # ── Export ───────────────────────────────────────────────────
    with tab_exp:
        st.markdown('<div class="sec-sub">Download your flashcard deck in multiple formats.</div>', unsafe_allow_html=True)
        export_data = {
            "source": st.session_state.source_filename,
            "content_type": st.session_state.content_type,
            "total_cards": len(final_deck),
            "gold_examples_stored": st.session_state.gold_count,
            "quality_summary": {"mean": round(avg_s,3),"best": round(max(scores_list),3),"worst": round(min(scores_list),3)},
            "flashcards": [{"question":c.question,"answer":c.answer,"difficulty":c.difficulty,
                            "bloom_level":c.bloom_level,"question_type":c.question_type,
                            "source_chunk_id":c.source_chunk_id} for c in final_deck]
        }
        json_str  = json.dumps(export_data, indent=2, ensure_ascii=False)
        tsv_lines = ["Question\tAnswer\tDifficulty\tBloom Level\tType"] + \
                    [f"{c.question}\t{c.answer}\t{c.difficulty}\t{c.bloom_level}\t{c.question_type}" for c in final_deck]
        stem = Path(st.session_state.source_filename).stem

        dc1, dc2 = st.columns(2)
        with dc1:
            st.download_button("⬇️ Download JSON", data=json_str,
                               file_name=f"{stem}_flashcards.json", mime="application/json", use_container_width=True)
        with dc2:
            st.download_button("⬇️ Download TSV (Anki)", data="\n".join(tsv_lines),
                               file_name=f"{stem}_flashcards.tsv", mime="text/tab-separated-values", use_container_width=True)

        st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.79rem;color:var(--text3);margin-bottom:0.5rem">JSON Preview</div>', unsafe_allow_html=True)
        st.code(json_str[:2500]+("\n…" if len(json_str)>2500 else ""), language="json")

st.markdown('</div>', unsafe_allow_html=True)