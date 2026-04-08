import os
import json
import time
import uuid
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from providers.llm_provider import create_llm
from core.sm2 import SM2Card, RATING_BUTTONS, get_or_create_sm2, get_due_cards, get_sm2_summary

st.set_page_config(
    page_title="CardCraft AI",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════
# DESIGN SYSTEM  (unchanged — collapsed for readability)
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #070910; --bg2: #0d0f1a;
  --surface: #111320; --surface2: #181b2e; --surface3: #1e2238;
  --border: rgba(255,255,255,0.07); --border2: rgba(255,255,255,0.12);
  --violet: #8b5cf6; --violet2: #a78bfa; --indigo: #6366f1;
  --cyan: #22d3ee; --emerald: #10b981; --amber: #f59e0b; --rose: #f43f5e;
  --text: #f1f5f9; --text2: #94a3b8; --text3: #475569;
  --radius: 16px; --radius-sm: 10px;
  --font-d: 'Syne', sans-serif; --font-b: 'Inter', sans-serif; --font-m: 'JetBrains Mono', monospace;
}
html, body, [class*="css"], .stApp { font-family: var(--font-b); background: var(--bg) !important; color: var(--text); }
#MainMenu, footer, .stDeployButton, [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], header { display: none !important; visibility: hidden !important; height: 0 !important; }
section[data-testid="stSidebar"] { display: none !important; }
html, body { margin: 0 !important; padding: 0 !important; }
.stApp { margin-top: 0 !important; padding-top: 0 !important; overflow-x: hidden; }
.stMainBlockContainer { padding-top: 0rem !important; }
div[class*="main"] > div { padding-top: 0rem !important; }
[data-testid="stAppViewContainer"] { margin-top: 0 !important; padding-top: 0 !important; }
[data-testid="stAppViewContainer"] > section { padding-top: 0 !important; margin-top: 0 !important; }
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 0 !important; padding-bottom: 0 !important; margin-top: 0 !important; max-width: 100% !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] { padding: 0 !important; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--surface3); border-radius: 99px; }
.bg-mesh { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.bg-mesh::before { content: ''; position: absolute; inset: -50%; background: radial-gradient(ellipse 60% 50% at 20% 20%, rgba(139,92,246,0.11) 0%, transparent 60%), radial-gradient(ellipse 50% 40% at 80% 80%, rgba(34,211,238,0.07) 0%, transparent 60%), radial-gradient(ellipse 40% 60% at 60% 10%, rgba(99,102,241,0.07) 0%, transparent 50%); animation: meshMove 22s ease-in-out infinite alternate; }
.bg-mesh::after { content: ''; position: absolute; inset: 0; background-image: radial-gradient(circle, rgba(255,255,255,0.02) 1px, transparent 1px); background-size: 48px 48px; }
@keyframes meshMove { from { transform: translate(0,0) scale(1); } to { transform: translate(3%,3%) scale(1.05); } }
.topnav { display: flex; align-items: center; justify-content: space-between; padding: 1rem 0 0.9rem; border-bottom: 1px solid var(--border); margin-bottom: 2rem; }
.nav-brand { display: flex; align-items: baseline; gap: 0.75rem; }
.nav-title { font-family: var(--font-d); font-size: 1.4rem; font-weight: 700; background: linear-gradient(90deg, #f1f5f9 0%, var(--violet2) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.02em; line-height: 1; }
.nav-sub { font-family: var(--font-m); font-size: 0.65rem; color: var(--text3); letter-spacing: 0.06em; text-transform: uppercase; }
.nav-pill { display: flex; gap: 0.2rem; background: var(--surface); border: 1px solid var(--border); border-radius: 99px; padding: 0.3rem; }
.nav-step { font-family: var(--font-m); font-size: 0.68rem; font-weight: 500; padding: 0.28rem 0.9rem; border-radius: 99px; letter-spacing: 0.02em; color: var(--text3); transition: all 0.2s; }
.nav-step.active { background: linear-gradient(135deg, var(--violet), var(--indigo)); color: white; box-shadow: 0 2px 12px rgba(139,92,246,0.4); }
.nav-step.done { color: var(--emerald); }
.hero { text-align: center; padding: 1.5rem 0 2rem; }
.hero-badge { display: inline-flex; align-items: center; gap: 0.4rem; background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.22); border-radius: 99px; padding: 0.35rem 1rem; font-size: 0.74rem; color: var(--violet2); font-family: var(--font-m); letter-spacing: 0.05em; margin-bottom: 1.5rem; }
.hero-title { font-family: var(--font-d); font-size: clamp(2.4rem, 5vw, 3.8rem); font-weight: 800; line-height: 1.06; letter-spacing: -0.03em; background: linear-gradient(135deg, #f1f5f9 0%, var(--violet2) 50%, var(--cyan) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 1rem; }
.hero-sub { font-size: 1.08rem; color: var(--text2); max-width: 480px; margin: 0 auto 2.5rem; line-height: 1.65; font-weight: 300; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.4rem 1.6rem; margin-bottom: 0.85rem; transition: border-color 0.25s; }
.card:hover { border-color: var(--border2); }
.card-glow:hover { border-color: rgba(139,92,246,0.3); box-shadow: 0 0 30px rgba(139,92,246,0.12); }
.step-item { display: flex; align-items: flex-start; gap: 0.85rem; padding: 0.9rem 1.1rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm); transition: all 0.2s; margin-bottom: 0.5rem; }
.step-item:hover { border-color: rgba(139,92,246,0.28); background: var(--surface2); }
.step-num { font-family: var(--font-m); font-size: 0.64rem; color: var(--violet); background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.2); border-radius: 5px; padding: 0.2rem 0.42rem; flex-shrink: 0; margin-top: 0.1rem; letter-spacing: 0.04em; }
.step-title { font-size: 0.87rem; font-weight: 600; color: var(--text); margin-bottom: 0.18rem; }
.step-desc { font-size: 0.74rem; color: var(--text3); line-height: 1.45; }
.pipe-step { display: flex; align-items: center; gap: 1rem; padding: 0.9rem 1.1rem; border-radius: var(--radius-sm); margin-bottom: 0.5rem; border: 1px solid transparent; }
.pipe-step.pending { background: var(--surface2); border-color: var(--border); opacity: 0.5; }
.pipe-step.active { background: rgba(139,92,246,0.07); border-color: rgba(139,92,246,0.2); }
.pipe-step.done { background: rgba(16,185,129,0.05); border-color: rgba(16,185,129,0.18); }
.pipe-step.error { background: rgba(244,63,94,0.07); border-color: rgba(244,63,94,0.2); }
.pipe-icon { width: 36px; height: 36px; border-radius: 99px; display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0; }
.pipe-icon.pending { background: var(--surface3); }
.pipe-icon.active { background: rgba(139,92,246,0.18); }
.pipe-icon.done { background: rgba(16,185,129,0.15); }
.pipe-label { font-size: 0.9rem; font-weight: 600; }
.pipe-detail { font-size: 0.76rem; color: var(--text3); margin-top: 0.1rem; }
.pipe-badge { font-family: var(--font-m); font-size: 0.66rem; padding: 0.22rem 0.65rem; border-radius: 99px; border: 1px solid; }
.pipe-badge.pending { color: var(--text3); border-color: var(--border); background: var(--surface3); }
.pipe-badge.active { color: var(--violet2); border-color: rgba(139,92,246,0.3); background: rgba(139,92,246,0.1); }
.pipe-badge.done { color: var(--emerald); border-color: rgba(16,185,129,0.3); background: rgba(16,185,129,0.1); }
.metric-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(115px, 1fr)); gap: 0.7rem; margin-bottom: 1.75rem; }
.metric-tile { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 1.1rem 1.2rem; transition: border-color 0.2s; }
.metric-tile:hover { border-color: var(--border2); }
.m-val { font-family: var(--font-d); font-size: 2rem; font-weight: 700; line-height: 1; margin-bottom: 0.28rem; }
.m-lbl { font-family: var(--font-m); font-size: 0.63rem; color: var(--text3); letter-spacing: 0.08em; text-transform: uppercase; }
.m-sub { font-size: 0.7rem; color: var(--text3); margin-top: 0.18rem; }
.sbar { margin: 0.32rem 0; }
.sbar-hd { display: flex; justify-content: space-between; font-family: var(--font-m); font-size: 0.67rem; color: var(--text3); margin-bottom: 0.18rem; }
.sbar-track { background: var(--surface3); border-radius: 99px; height: 4px; overflow: hidden; }
.sbar-fill { height: 100%; border-radius: 99px; }
.chip { display: inline-flex; align-items: center; padding: 0.17em 0.6em; border-radius: 99px; font-size: 0.67rem; font-family: var(--font-m); letter-spacing: 0.03em; font-weight: 500; border: 1px solid; margin-right: 0.22rem; }
.chip-easy { color: #34d399; background: rgba(52,211,153,0.1); border-color: rgba(52,211,153,0.22); }
.chip-medium { color: #fbbf24; background: rgba(251,191,36,0.1); border-color: rgba(251,191,36,0.22); }
.chip-hard { color: #f87171; background: rgba(248,113,113,0.1); border-color: rgba(248,113,113,0.22); }
.chip-bloom { color: var(--violet2); background: rgba(139,92,246,0.1); border-color: rgba(139,92,246,0.22); }
.chip-type { color: var(--cyan); background: rgba(34,211,238,0.08); border-color: rgba(34,211,238,0.18); }
.chip-approve { color: #34d399; background: rgba(52,211,153,0.1); border-color: rgba(52,211,153,0.22); }
.chip-review { color: #fbbf24; background: rgba(251,191,36,0.1); border-color: rgba(251,191,36,0.22); }
.chip-reject { color: #f87171; background: rgba(248,113,113,0.1); border-color: rgba(248,113,113,0.22); }
.rcard { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.4rem 1.6rem; margin-bottom: 0.9rem; transition: border-color 0.25s; }
.rcard-q { font-size: 1rem; font-weight: 600; color: var(--text); line-height: 1.5; margin-bottom: 0.5rem; }
.rcard-a { font-size: 0.9rem; color: var(--cyan); line-height: 1.5; margin-bottom: 0.9rem; }
.rcard-just { font-size: 0.75rem; color: var(--text3); font-style: italic; border-top: 1px solid var(--border); padding-top: 0.55rem; margin-top: 0.55rem; line-height: 1.5; }
.fc-scene { perspective: 1200px; width: 100%; height: 210px; cursor: pointer; margin-bottom: 0.5rem; }
.fc-inner { position: relative; width: 100%; height: 100%; transform-style: preserve-3d; transition: transform 0.6s cubic-bezier(0.4,0,0.2,1); }
.fc-scene.flipped .fc-inner { transform: rotateY(180deg); }
.fc-face { position: absolute; inset: 0; backface-visibility: hidden; border-radius: var(--radius); display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 1.5rem; text-align: center; border: 1px solid var(--border); }
.fc-front { background: var(--surface); }
.fc-back { background: linear-gradient(135deg, #130f2a 0%, var(--surface) 100%); border-color: rgba(139,92,246,0.32); transform: rotateY(180deg); box-shadow: inset 0 0 60px rgba(139,92,246,0.07); }
.fc-label { font-family: var(--font-m); font-size: 0.6rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text3); margin-bottom: 0.65rem; }
.fc-text { font-size: 0.9rem; line-height: 1.55; color: var(--text); }
.fc-ans { color: var(--cyan); font-weight: 500; }
.fc-hint { position: absolute; bottom: 0.65rem; right: 0.9rem; font-size: 0.58rem; color: var(--text3); font-family: var(--font-m); opacity: 0.55; }
.pw-gate { max-width: 420px; margin: 3rem auto; text-align: center; }
.pw-icon { font-size: 3rem; margin-bottom: 1rem; display: block; filter: drop-shadow(0 0 20px rgba(139,92,246,0.4)); }
.pw-title { font-family: var(--font-d); font-size: 1.65rem; font-weight: 700; color: var(--text); margin-bottom: 0.5rem; }
.pw-sub { font-size: 0.87rem; color: var(--text3); margin-bottom: 2rem; line-height: 1.55; }
.pw-error { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.25); border-radius: var(--radius-sm); padding: 0.65rem 1rem; font-size: 0.8rem; color: #fda4af; text-align: center; margin-top: 0.75rem; }
.sec-title { font-family: var(--font-d); font-size: 1.5rem; font-weight: 700; color: var(--text); letter-spacing: -0.02em; margin-bottom: 0.3rem; }
.sec-sub { font-size: 0.82rem; color: var(--text3); margin-bottom: 1.4rem; line-height: 1.55; }
div[data-testid="stButton"] > button { background: linear-gradient(135deg, var(--violet) 0%, var(--indigo) 100%) !important; color: white !important; border: none !important; border-radius: var(--radius-sm) !important; font-family: var(--font-b) !important; font-weight: 500 !important; font-size: 0.87rem !important; padding: 0.58rem 1.3rem !important; box-shadow: 0 4px 15px rgba(139,92,246,0.28) !important; transition: all 0.2s !important; letter-spacing: 0.01em !important; }
div[data-testid="stButton"] > button:hover { transform: translateY(-1px) !important; box-shadow: 0 6px 22px rgba(139,92,246,0.42) !important; }
div[data-testid="stButton"] > button:active { transform: translateY(0) !important; }
div[data-testid="stButton"] > button:disabled { opacity: 0.38 !important; transform: none !important; box-shadow: none !important; }
.btn-ghost > div[data-testid="stButton"] > button { background: var(--surface) !important; border: 1px solid var(--border2) !important; box-shadow: none !important; color: var(--text2) !important; }
.btn-ghost > div[data-testid="stButton"] > button:hover { background: var(--surface2) !important; box-shadow: none !important; transform: none !important; }
.btn-approve > div[data-testid="stButton"] > button { background: linear-gradient(135deg,#065f46,#10b981) !important; box-shadow: 0 4px 14px rgba(16,185,129,0.28) !important; }
.btn-reject > div[data-testid="stButton"] > button { background: linear-gradient(135deg,#9f1239,#f43f5e) !important; box-shadow: 0 4px 14px rgba(244,63,94,0.25) !important; }
.btn-edit > div[data-testid="stButton"] > button { background: linear-gradient(135deg,#5b21b6,#8b5cf6) !important; }
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea { background: var(--surface2) !important; border: 1px solid var(--border2) !important; border-radius: var(--radius-sm) !important; color: var(--text) !important; font-family: var(--font-b) !important; font-size: 0.87rem !important; caret-color: var(--violet); }
div[data-testid="stTextInput"] input:focus, div[data-testid="stTextArea"] textarea:focus { border-color: rgba(139,92,246,0.5) !important; box-shadow: 0 0 0 3px rgba(139,92,246,0.11) !important; }
div[data-testid="stTextInput"] label, div[data-testid="stTextArea"] label, div[data-testid="stSelectbox"] label, div[data-testid="stSlider"] label, div[data-testid="stMultiSelect"] label { color: var(--text2) !important; font-size: 0.79rem !important; font-weight: 500 !important; }
div[data-testid="stSelectbox"] > div > div { background: var(--surface2) !important; border: 1px solid var(--border2) !important; border-radius: var(--radius-sm) !important; color: var(--text) !important; }
div[data-testid="stMultiSelect"] > div { background: var(--surface2) !important; border: 1px solid var(--border2) !important; border-radius: var(--radius-sm) !important; }
span[data-baseweb="tag"] { background: rgba(139,92,246,0.18) !important; border: 1px solid rgba(139,92,246,0.3) !important; border-radius: 99px !important; }
div[data-testid="stFileUploader"] > div { background: rgba(139,92,246,0.04) !important; border: 2px dashed rgba(139,92,246,0.28) !important; border-radius: var(--radius) !important; color: var(--text2) !important; }
div[data-testid="stFileUploader"] > div:hover { border-color: rgba(139,92,246,0.52) !important; background: rgba(139,92,246,0.07) !important; }
div[data-testid="stProgressBar"] > div { background: var(--surface3) !important; border-radius: 99px !important; height: 6px !important; }
div[data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, var(--violet), var(--cyan)) !important; border-radius: 99px !important; }
div[data-baseweb="tab-list"] { background: var(--surface) !important; border-radius: 12px !important; padding: 4px !important; gap: 2px !important; border: 1px solid var(--border) !important; }
button[data-baseweb="tab"] { border-radius: 9px !important; font-family: var(--font-b) !important; font-size: 0.81rem !important; font-weight: 500 !important; color: var(--text3) !important; padding: 0.44rem 1rem !important; transition: all 0.2s !important; }
button[data-baseweb="tab"][aria-selected="true"] { background: linear-gradient(135deg,rgba(139,92,246,0.18),rgba(99,102,241,0.12)) !important; color: var(--text) !important; border: 1px solid rgba(139,92,246,0.25) !important; }
div[data-testid="stExpander"] > div:first-child { background: var(--surface) !important; border-radius: var(--radius-sm) !important; border: 1px solid var(--border) !important; color: var(--text2) !important; font-size: 0.85rem !important; }
div[data-testid="stExpander"] > div:first-child:hover { border-color: var(--border2) !important; }
div[data-testid="stAlert"] { border-radius: var(--radius-sm) !important; font-size: 0.83rem !important; }
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1.5rem 0 !important; }

/* SM2 spaced repetition */
.sm2-summary { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
.sm2-pill { font-family: var(--font-m); font-size: 0.7rem; padding: 0.3rem 0.75rem; border-radius: 99px; border: 1px solid var(--border); background: var(--surface); }
.sm2-progress { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0.75rem 1rem; margin-bottom: 1rem; }
.sm2-repeat-badge { display: inline-flex; align-items: center; gap: 0.3rem; font-family: var(--font-m); font-size: 0.66rem; color: #f59e0b; background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.22); border-radius: 99px; padding: 0.18rem 0.65rem; margin-bottom: 0.5rem; }
.btn-again > div[data-testid="stButton"] > button { background: rgba(244,63,94,0.12) !important; border: 1px solid rgba(244,63,94,0.35) !important; color: #f43f5e !important; box-shadow: none !important; font-family: var(--font-m) !important; font-size: 0.78rem !important; }
.btn-again > div[data-testid="stButton"] > button:hover { background: rgba(244,63,94,0.2) !important; transform: none !important; box-shadow: 0 2px 10px rgba(244,63,94,0.2) !important; }
.btn-hard > div[data-testid="stButton"] > button { background: rgba(245,158,11,0.12) !important; border: 1px solid rgba(245,158,11,0.35) !important; color: #f59e0b !important; box-shadow: none !important; font-family: var(--font-m) !important; font-size: 0.78rem !important; }
.btn-hard > div[data-testid="stButton"] > button:hover { background: rgba(245,158,11,0.2) !important; transform: none !important; box-shadow: 0 2px 10px rgba(245,158,11,0.2) !important; }
.btn-good > div[data-testid="stButton"] > button { background: rgba(16,185,129,0.12) !important; border: 1px solid rgba(16,185,129,0.35) !important; color: #10b981 !important; box-shadow: none !important; font-family: var(--font-m) !important; font-size: 0.78rem !important; }
.btn-good > div[data-testid="stButton"] > button:hover { background: rgba(16,185,129,0.2) !important; transform: none !important; box-shadow: 0 2px 10px rgba(16,185,129,0.2) !important; }
.btn-easy > div[data-testid="stButton"] > button { background: rgba(34,211,238,0.12) !important; border: 1px solid rgba(34,211,238,0.35) !important; color: #22d3ee !important; box-shadow: none !important; font-family: var(--font-m) !important; font-size: 0.78rem !important; }
.btn-easy > div[data-testid="stButton"] > button:hover { background: rgba(34,211,238,0.2) !important; transform: none !important; box-shadow: 0 2px 10px rgba(34,211,238,0.2) !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# CONSTANTS & STATE
# ═══════════════════════════════════════════════════════════
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "cardcraft2024")
STUDENT_PASSWORD = os.getenv("STUDENT_PASSWORD", "student2024")

# ── File-based publishing (works across browser sessions) ──
PUBLISH_DIR = Path("published_decks")
PUBLISH_DIR.mkdir(exist_ok=True)
PUBLISHED_DECK_FILE = PUBLISH_DIR / "current_deck.json"

# ── Evaluation log directory ──
EVAL_LOG_DIR = Path("eval_logs")
EVAL_LOG_DIR.mkdir(exist_ok=True)


def init_state():
    defaults = {
        "role": None,
        "role_pw_error": False,
        "step": "upload",
        "chunks": [], "raw_cards": [], "scored_cards": [],
        "approved_cards": [], "human_queue": [], "rejected_cards": [],
        "content_type": "", "source_filename": "",
        "flip_states": {}, "review_decisions": {}, "edit_data": {},
        "auto_edit_data": {}, "auto_edit_decisions": {},
        "gold_count": 0, "gold_cards_session": [],
        "published_deck": [],
        "published_gold": [],
        "teacher_authed": False, "pw_error": False,
        "gen_provider": "gemini", "gen_model": "gemini-3.1-flash-lite-preview",
        "gen_num_cards": 5, "gen_api_key": "",
        # ── Evaluation metrics ──
        "flip_times": {},           # {card_idx: [timestamp, ...]}
        "sm2_cards": {},            # {card_idx: SM2Card} — spaced repetition state
        "sm2_current_idx": None,    # index of card currently being studied in SM2 mode
        "pipeline_metrics": {},     # logged after each pipeline run
        "study_session_id": None,   # unique ID per study session
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




# ── File-based deck publishing ──────────────────────────────────

def _publish_deck_to_file(final_cards, gold_cards, scored_cards, metadata: dict):
    """Write published deck to disk so students on different sessions can load it."""
    deck_data = {
        "published_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "metadata": metadata,
        "flashcards": [
            {"question": c.question, "answer": c.answer, "difficulty": c.difficulty,
             "bloom_level": c.bloom_level, "source_chunk_id": c.source_chunk_id,
             "question_type": c.question_type}
            for c in final_cards
        ],
        "gold_examples": gold_cards,
        "quality_scores": [
            {"question": s.card.question, "composite": round(s.composite_score, 4),
             "groundedness": round(s.groundedness, 4), "clarity": round(s.clarity, 4),
             "uniqueness": round(s.uniqueness, 4), "difficulty_calibration": round(s.difficulty_calibration, 4),
             "routing": s.routing_decision, "justification": s.justification}
            for s in scored_cards
        ] if scored_cards else [],
    }
    with open(PUBLISHED_DECK_FILE, "w", encoding="utf-8") as f:
        json.dump(deck_data, f, indent=2, ensure_ascii=False)
    return deck_data


def _load_published_deck() -> Optional[Dict[str, Any]]:
    """Load the published deck from disk. Returns None if no deck exists."""
    if not PUBLISHED_DECK_FILE.exists():
        return None
    try:
        with open(PUBLISHED_DECK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


# ── Evaluation metrics ──────────────────────────────────────────

def _log_pipeline_metrics(scored_cards, approved, human_queue, rejected,
                          raw_cards, gold_at_gen_time, duration_s):
    """Compute and persist system-level evaluation metrics after each pipeline run."""
    scores = [s.composite_score for s in scored_cards]
    total = len(scored_cards) or 1
    mean_score = sum(scores) / total if scores else 0

    metrics = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "session_id": st.session_state.get("study_session_id", ""),
        "source_file": st.session_state.source_filename,
        "content_type": st.session_state.content_type,
        "provider": st.session_state.gen_provider,
        "model": st.session_state.gen_model,
        "pipeline_duration_sec": round(duration_s, 1),
        # Generation
        "cards_requested": st.session_state.gen_num_cards,
        "cards_parsed_valid": len(raw_cards),
        "generation_success_rate": round(len(raw_cards) / max(st.session_state.gen_num_cards, 1), 3),
        # Quality distribution
        "composite_mean": round(mean_score, 4),
        "composite_min": round(min(scores), 4) if scores else 0,
        "composite_max": round(max(scores), 4) if scores else 0,
        "composite_std": round((sum((s - mean_score)**2 for s in scores) / total) ** 0.5, 4) if scores else 0,
        # Per-dimension means
        "groundedness_mean": round(sum(s.groundedness for s in scored_cards) / total, 4),
        "clarity_mean": round(sum(s.clarity for s in scored_cards) / total, 4),
        "uniqueness_mean": round(sum(s.uniqueness for s in scored_cards) / total, 4),
        "difficulty_cal_mean": round(sum(s.difficulty_calibration for s in scored_cards) / total, 4),
        # Routing rates
        "auto_approve_count": len(approved),
        "human_review_count": len(human_queue),
        "auto_reject_count": len(rejected),
        "auto_approve_rate": round(len(approved) / total, 3),
        "human_review_rate": round(len(human_queue) / total, 3),
        "auto_reject_rate": round(len(rejected) / total, 3),
        # Gold utilization
        "gold_examples_at_generation": gold_at_gen_time,
    }
    st.session_state.pipeline_metrics = metrics

    # Append to persistent log file (one JSON object per line)
    log_file = EVAL_LOG_DIR / "pipeline_metrics.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(metrics, ensure_ascii=False) + "\n")
    return metrics


def _build_eval_export(final_deck, scored_cards) -> dict:
    """Build comprehensive evaluation data for export (covers both pipeline + study)."""
    scores = [s.composite_score for s in scored_cards] if scored_cards else [0]
    flip_times = st.session_state.get("flip_times", {})

    # Compute per-card study time from flip timestamps
    card_study_times = {}
    for idx_key, timestamps in flip_times.items():
        idx = int(idx_key) if isinstance(idx_key, str) else idx_key
        if len(timestamps) >= 2:
            card_study_times[idx] = round(timestamps[-1] - timestamps[0], 2)
        elif len(timestamps) == 1:
            card_study_times[idx] = 0.0

    return {
        "session_id": st.session_state.get("study_session_id", "no_id"),
        "role": st.session_state.get("role", "unknown"),
        "export_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": st.session_state.source_filename,
        "content_type": st.session_state.content_type,
        # Pipeline metrics snapshot
        "pipeline_metrics": st.session_state.get("pipeline_metrics", {}),
        # Gold
        "gold_examples_total": st.session_state.gold_count,
        "gold_this_session": st.session_state.get("gold_cards_session", []),
        # Quality summary
        "quality_summary": {
            "total_scored": len(scored_cards),
            "mean": round(sum(scores) / len(scores), 4),
            "best": round(max(scores), 4),
            "worst": round(min(scores), 4),
            "high_count": sum(1 for s in scores if s >= 0.8),
            "mid_count": sum(1 for s in scores if 0.5 <= s < 0.8),
            "low_count": sum(1 for s in scores if s < 0.5),
        },
        # Per-card detail with study interaction data
        "flashcards": [
            {
                "index": i,
                "question": c.question, "answer": c.answer,
                "difficulty": c.difficulty, "bloom_level": c.bloom_level,
                "question_type": c.question_type, "source_chunk_id": c.source_chunk_id,
                # Quality scores
                **(lambda sc: {
                    "composite_score": round(sc.composite_score, 4),
                    "groundedness": round(sc.groundedness, 4),
                    "clarity": round(sc.clarity, 4),
                    "uniqueness": round(sc.uniqueness, 4),
                    "difficulty_calibration": round(sc.difficulty_calibration, 4),
                    "routing_decision": sc.routing_decision,
                } if sc else {"composite_score": None})(
                    next((s for s in scored_cards if s.card.question == c.question), None)
                ),
                # Study interaction
                "study_time_sec": card_study_times.get(i),
                "flip_count": len(flip_times.get(i, flip_times.get(str(i), []))),
            }
            for i, c in enumerate(final_deck)
        ],
        # Raw flip timestamps
        "flip_timestamps": {str(k): v for k, v in flip_times.items()},
        # SM2 spaced repetition data
        "sm2_state": {
            str(k): v.to_dict()
            for k, v in st.session_state.get("sm2_cards", {}).items()
        },
        "sm2_summary": get_sm2_summary(st.session_state, len(final_deck)),
        # Teacher review decisions
        "review_decisions": {str(k): v for k, v in st.session_state.get("review_decisions", {}).items()},
    }


# ── UI helpers ──────────────────────────────────────────────────

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
    return chip(d, "easy" if d == "easy" else ("medium" if d == "medium" else "hard"))

def routing_chip(decision):
    if decision == "auto_approve": return chip("✓ auto-approve", "approve")
    if decision == "human_review": return chip("⟳ needs review", "review")
    return chip("✗ auto-reject", "reject")

def nav_html():
    role = st.session_state.get("role")
    current = st.session_state.step
    if role == "teacher":
        order = ["upload", "generating", "review", "study"]
        labels = ["Upload", "Processing", "Review", "Study"]
        ci = order.index(current) if current in order else 0
        pills = "".join(
            f'<span class="nav-step {"active" if k == current else ("done" if i < ci else "")}">{labels[i]}</span>'
            for i, k in enumerate(order))
        role_badge = '<span style="font-family:var(--font-m);font-size:0.65rem;color:#10b981;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.22);border-radius:99px;padding:0.2rem 0.65rem;">Teacher</span>'
    elif role == "student":
        pills = '<span class="nav-step active">Study</span>'
        role_badge = '<span style="font-family:var(--font-m);font-size:0.65rem;color:var(--cyan);background:rgba(34,211,238,0.08);border:1px solid rgba(34,211,238,0.2);border-radius:99px;padding:0.2rem 0.65rem;">Student</span>'
    else:
        pills = '<span class="nav-step active">Welcome</span>'
        role_badge = ""
    return (
        '<div class="topnav"><div class="nav-brand"><span class="nav-title">CardCraft</span>'
        '<span class="nav-sub">by Northeastern Students</span></div>'
        '<div style="display:flex;align-items:center;gap:0.75rem;">'
        '<div class="nav-pill">' + pills + '</div>' + role_badge + '</div>'
        '<div style="font-family:var(--font-m);font-size:0.68rem;color:var(--text3);">AI · HITL · Adaptive</div></div>'
    )

def reset():
    keys = ["step", "chunks", "raw_cards", "scored_cards", "approved_cards", "human_queue",
            "rejected_cards", "content_type", "source_filename", "flip_states",
            "review_decisions", "edit_data", "auto_edit_data", "auto_edit_decisions",
            "gold_cards_session", "gold_count", "teacher_authed", "pw_error",
            "flip_times", "sm2_cards", "sm2_current_idx", "pipeline_metrics", "study_session_id"]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]
    init_state()

def full_reset():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    init_state()


# ── Page shell ──
st.markdown('<div class="bg-mesh"></div>', unsafe_allow_html=True)
st.markdown("""
<script>
(function() {
  function nuke() {
    ['[data-testid="stAppViewContainer"]','[data-testid="stAppViewContainer"] > section',
     '.block-container','.stMainBlockContainer','[data-testid="stMainBlockContainer"]',
     '.main > .block-container'].forEach(function(sel) {
      document.querySelectorAll(sel).forEach(function(el) {
        el.style.paddingTop = '0px'; el.style.marginTop = '0px';
      });
    });
    var hdr = document.querySelector('[data-testid="stHeader"]');
    if (hdr) { hdr.style.display = 'none'; hdr.style.height = '0'; }
  }
  nuke(); setTimeout(nuke, 100); setTimeout(nuke, 400); setTimeout(nuke, 1000);
})();
</script>
""", unsafe_allow_html=True)
st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
st.markdown(nav_html(), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# LANDING — ROLE SELECT
# ═══════════════════════════════════════════════════════════════════
if st.session_state.role is None:
    st.markdown("""
    <div class="hero" style="padding-bottom:0.5rem">
      <div class="hero-badge">✦ Multi-Agent Pipeline · Teacher-in-the-Loop</div>
      <div class="hero-title">Welcome to CardCraft</div>
      <div class="hero-sub">AI-powered flashcard generation with human expertise at the centre. Choose your role to get started.</div>
    </div>
    """, unsafe_allow_html=True)

    rc_l, rc_gap, rc_r = st.columns([1, 0.08, 1])
    with rc_l:
        st.markdown("""
        <div style="background:var(--surface);border:1px solid rgba(16,185,129,0.22);border-radius:var(--radius);padding:2rem 2rem 1.6rem;text-align:center;">
          <div style="font-family:var(--font-d);font-size:1.25rem;font-weight:700;color:var(--text);margin-bottom:0.4rem;">🎓 I'm a Teacher</div>
          <div style="font-size:0.8rem;color:var(--text3);line-height:1.65;margin-bottom:1.5rem;">Upload PDFs, run the AI pipeline, review and edit generated cards, and build a gold example library.</div>
          <div style="display:flex;flex-direction:column;gap:0.5rem;text-align:left;margin-bottom:1.5rem;">
            <div style="font-size:0.76rem;color:var(--text2);display:flex;gap:0.5rem;"><span style="color:#10b981">✓</span> Full pipeline access</div>
            <div style="font-size:0.76rem;color:var(--text2);display:flex;gap:0.5rem;"><span style="color:#10b981">✓</span> Quality scores &amp; AI judge breakdown</div>
            <div style="font-size:0.76rem;color:var(--text2);display:flex;gap:0.5rem;"><span style="color:#10b981">✓</span> Approve, edit, or reject every card</div>
            <div style="font-size:0.76rem;color:var(--text2);display:flex;gap:0.5rem;"><span style="color:#10b981">✓</span> Edits stored as gold few-shot examples</div>
          </div>
        </div>""", unsafe_allow_html=True)
        teacher_pw = st.text_input("Teacher password", type="password", placeholder="Enter teacher password…",
                                   key="landing_teacher_pw", label_visibility="collapsed")
        st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("Unlock Teacher Dashboard", use_container_width=True, key="btn_teacher"):
            if teacher_pw == TEACHER_PASSWORD:
                st.session_state.role = "teacher"; st.session_state.teacher_authed = True; st.session_state.role_pw_error = False; st.rerun()
            else:
                st.session_state.role_pw_error = "teacher"; st.rerun()
        if st.session_state.role_pw_error == "teacher":
            st.markdown('<div style="font-size:0.78rem;color:#f43f5e;margin-top:0.4rem;text-align:center;">Incorrect teacher password</div>', unsafe_allow_html=True)

    with rc_r:
        st.markdown("""
        <div style="background:var(--surface);border:1px solid rgba(34,211,238,0.2);border-radius:var(--radius);padding:2rem 2rem 1.6rem;text-align:center;">
          <div style="font-family:var(--font-d);font-size:1.25rem;font-weight:700;color:var(--text);margin-bottom:0.4rem;">📖 I'm a Student</div>
          <div style="font-size:0.8rem;color:var(--text3);line-height:1.65;margin-bottom:1.5rem;">Study the teacher-curated flashcard deck. Flip cards, filter by difficulty, and export to Anki.</div>
          <div style="display:flex;flex-direction:column;gap:0.5rem;text-align:left;margin-bottom:1.5rem;">
            <div style="font-size:0.76rem;color:var(--text2);display:flex;gap:0.5rem;"><span style="color:var(--cyan)">✓</span> Interactive flip-card study mode</div>
            <div style="font-size:0.76rem;color:var(--text2);display:flex;gap:0.5rem;"><span style="color:var(--cyan)">✓</span> Filter by difficulty &amp; Bloom's taxonomy</div>
            <div style="font-size:0.76rem;color:var(--text2);display:flex;gap:0.5rem;"><span style="color:var(--cyan)">✓</span> Export to Anki-compatible TSV</div>
            <div style="font-size:0.76rem;color:var(--text3);display:flex;gap:0.5rem;"><span style="color:#475569">✗</span> No pipeline, scores, or gold store access</div>
          </div>
        </div>""", unsafe_allow_html=True)
        student_pw = st.text_input("Student password", type="password", placeholder="Enter student password…",
                                   key="landing_student_pw", label_visibility="collapsed")
        st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("Enter Study Mode", use_container_width=True, key="btn_student"):
            if student_pw == STUDENT_PASSWORD:
                st.session_state.role = "student"; st.session_state.role_pw_error = False
                st.session_state.study_session_id = str(uuid.uuid4())[:8]
                st.rerun()
            else:
                st.session_state.role_pw_error = "student"; st.rerun()
        if st.session_state.role_pw_error == "student":
            st.markdown('<div style="font-size:0.78rem;color:#f43f5e;margin-top:0.4rem;text-align:center;">Incorrect student password</div>', unsafe_allow_html=True)

    # Show published deck status
    pub = _load_published_deck()
    if pub:
        st.markdown(f"""
        <div style="text-align:center;margin-top:2rem;font-size:0.78rem;color:var(--emerald);">
          ✓ A deck is published ({len(pub.get('flashcards',[]))} cards · {pub.get('published_at','')})
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;margin-top:2rem;font-size:0.78rem;color:var(--text3);">No deck published yet — teacher must generate and finalize first.</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin-top:0.75rem;font-size:0.71rem;color:var(--text3);line-height:1.8;">
      Set <code style="color:var(--violet2)">TEACHER_PASSWORD</code> and <code style="color:var(--violet2)">STUDENT_PASSWORD</code> in your <code>.env</code>
    </div>""", unsafe_allow_html=True)
    st.stop()


# ── Student gate — load from file ────────────────────────────────
elif st.session_state.role == "student":
    # Try loading from file first, fall back to session state
    pub = _load_published_deck()
    if pub and pub.get("flashcards"):
        from core.models import Flashcard as FC
        st.session_state.published_deck = [
            FC(**card_d) for card_d in pub["flashcards"]
        ]
        st.session_state.published_gold = pub.get("gold_examples", [])
        st.session_state.source_filename = pub.get("metadata", {}).get("source_filename", "")
        st.session_state.content_type = pub.get("metadata", {}).get("content_type", "")

    if not st.session_state.published_deck:
        st.markdown("""
        <div style="text-align:center;padding:4rem 1rem 2rem;">
          <div style="font-size:3rem;margin-bottom:1rem;">⏳</div>
          <div style="font-family:var(--font-d);font-size:1.4rem;font-weight:700;margin-bottom:0.5rem;">Waiting for your teacher</div>
          <div style="font-size:0.88rem;color:var(--text3);max-width:380px;margin:0 auto 2rem;line-height:1.65;">
            Your teacher hasn't published a deck yet. Once they finalize the review, you'll be able to study here.
          </div>
        </div>""", unsafe_allow_html=True)
        _, mid, _ = st.columns([1, 1, 1])
        with mid:
            if st.button("🔄 Refresh", use_container_width=True): st.rerun()
            st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
            if st.button("Switch Role", use_container_width=True): full_reset(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.stop()
    else:
        st.session_state.approved_cards = st.session_state.published_deck
        st.session_state.gold_cards_session = st.session_state.published_gold
        st.session_state.step = "study"


# ═══════════════════════════════════════════════════════════════════
# STEP 1 — UPLOAD  (teacher only)
# ═══════════════════════════════════════════════════════════════════
if st.session_state.role == "teacher" and st.session_state.step == "upload":
    st.markdown("""
    <div class="hero">
      <div class="hero-badge">✦ Multi-Agent Pipeline · Teacher-in-the-Loop </div>
      <div class="hero-title">Turn any PDF into<br>a smart flashcard deck</div>
      <div class="hero-sub">Upload lecture notes, textbooks, or research papers. AI generates, evaluates, and lets you refine every card.</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, _, col_r = st.columns([1.15, 0.07, 0.9])
    with col_l:
        st.markdown("""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.6rem 2rem 1.4rem;">
          <div style="font-family:var(--font-d);font-size:1.15rem;font-weight:700;margin-bottom:0.2rem;">Upload your PDF</div>
          <div style="font-size:0.79rem;color:var(--text3);margin-bottom:1.25rem;">Lectures, textbooks, research papers — anything with text</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded = st.file_uploader("", type=["pdf"], label_visibility="collapsed")
        if uploaded:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.85rem;background:rgba(139,92,246,0.07);border:1px solid rgba(139,92,246,0.22);border-radius:var(--radius-sm);padding:0.9rem 1.1rem;margin:0.5rem 0 0.75rem;">
              <span style="font-size:1.6rem;">📄</span>
              <div><div style="font-weight:600;font-size:0.92rem;">{uploaded.name}</div>
              <div style="font-size:0.74rem;color:var(--text3);margin-top:0.12rem;">{uploaded.size/1024:.1f} KB · PDF</div></div>
            </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        num_cards = st.slider("Number of cards to generate", 3, 20, st.session_state.gen_num_cards, key="cards_slider")
        st.session_state.gen_num_cards = num_cards
        st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
        if uploaded:
            if st.button("🚀 Generate Flashcards", use_container_width=True):
                st.session_state.source_filename = uploaded.name
                st.session_state.step = "generating"
                st.session_state.study_session_id = str(uuid.uuid4())[:8]
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded.read()); st.session_state._tmp_pdf = tmp.name
                st.rerun()
        else:
            st.button("🚀 Generate Flashcards", use_container_width=True, disabled=True)
        st.markdown("""
        <div style="margin-top:1.25rem;background:rgba(34,211,238,0.04);border:1px solid rgba(34,211,238,0.15);border-radius:var(--radius-sm);padding:0.85rem 1.1rem;">
          <div style="font-size:0.78rem;font-weight:600;color:var(--cyan);margin-bottom:0.3rem;">⚠ Having trouble?</div>
          <div style="font-size:0.74rem;color:var(--text3);line-height:1.55;">Your API key may be expired. Try replacing it in Settings below.</div>
        </div>""", unsafe_allow_html=True)

    with col_r:
        st.markdown('<div style="padding-top:0.25rem;"><div style="font-family:var(--font-d);font-size:1.12rem;font-weight:700;margin-bottom:1rem;">How it works</div>', unsafe_allow_html=True)
        for num, title, desc in [
            ("01", "Extract", "PDF text extraction with content-aware chunking"),
            ("02", "Generate", "LLM produces flashcards with Bloom's taxonomy guidance"),
            ("03", "Quality Check", "AI judge scores on groundedness, clarity, uniqueness & difficulty"),
            ("04", "Teacher Review", "Approve, edit, or reject borderline cards"),
            ("05", "Study", "Interactive flip-card study mode with export"),
        ]:
            st.markdown(f'<div class="step-item"><span class="step-num">{num}</span><div><div class="step-title">{title}</div><div class="step-desc">{desc}</div></div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

        with st.expander("⚙️ Generation Settings", expanded=False):
            PROVIDERS = {
                "gemini":      {"label": "Google Gemini",       "default_model": "gemini-3.1-flash-lite-preview",              "key_label": "Gemini API Key",    "key_link": "https://ai.google.dev/gemini-api/docs/api-key", "key_site": "ai.google.dev", "key_env": "GEMINI_API_KEY"},
                "huggingface": {"label": "HuggingFace (Llama)", "default_model": "meta-llama/Llama-3.1-8B-Instruct", "key_label": "HuggingFace Token", "key_link": "https://huggingface.co/settings/tokens",       "key_site": "huggingface.co","key_env": "HF_TOKEN"},
            }
            provider = st.radio("LLM Provider", options=list(PROVIDERS.keys()),
                                format_func=lambda x: PROVIDERS[x]["label"],
                                index=0 if st.session_state.gen_provider == "gemini" else 1,
                                horizontal=True, key="settings_provider_radio")
            if provider != st.session_state.gen_provider:
                st.session_state.gen_provider = provider
                st.session_state.gen_model = PROVIDERS[provider]["default_model"]
            cfg = PROVIDERS[provider]
            model = st.text_input("Model name", value=st.session_state.gen_model, placeholder=cfg["default_model"], key=f"settings_model_{provider}")
            api_key_in = st.text_input(cfg["key_label"], type="password", placeholder=f"Leave blank to use {cfg['key_env']} from .env", value=st.session_state.gen_api_key, key=f"settings_apikey_{provider}")
            st.session_state.gen_provider = provider
            st.session_state.gen_model = model
            st.session_state.gen_api_key = api_key_in


# ═══════════════════════════════════════════════════════════════════
# STEP 2 — GENERATING  (with pipeline timing + eval metrics)
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.role == "teacher" and st.session_state.step == "generating":
    st.markdown(f"""
    <div style="margin-bottom:1.75rem;">
      <div class="sec-title">Processing <span style="color:var(--violet2)">{st.session_state.source_filename}</span></div>
      <div class="sec-sub">Running 4-stage multi-agent pipeline — ~30–60 seconds</div>
    </div>""", unsafe_allow_html=True)

    prog = st.progress(0)
    PIPE = [("📄","Text Extraction","Extracting and cleaning text from PDF"),("🔍","Content Analysis","Detecting content type & creating semantic chunks"),("✨","Card Generation","LLM generating flashcards with Bloom's guidance"),("🎯","Quality Evaluation","AI judge scoring each card on 4 dimensions")]
    holders = []
    for icon, label, detail in PIPE:
        h = st.empty()
        h.markdown(f'<div class="pipe-step pending"><div class="pipe-icon pending">{icon}</div><div style="flex:1"><div class="pipe-label" style="color:var(--text3)">{label}</div><div class="pipe-detail">{detail}</div></div><span class="pipe-badge pending">waiting</span></div>', unsafe_allow_html=True)
        holders.append(h)

    def upd(idx, state, detail_override=""):
        icon, label, detail = PIPE[idx]; d = detail_override or detail
        badge = {"active":"running","done":"complete","error":"error","pending":"waiting"}[state]
        holders[idx].markdown(f'<div class="pipe-step {state}"><div class="pipe-icon {state}">{icon}</div><div style="flex:1"><div class="pipe-label">{label}</div><div class="pipe-detail">{d}</div></div><span class="pipe-badge {state}">{badge}</span></div>', unsafe_allow_html=True)

    try:
        pipeline_start = time.time()
        api_key = st.session_state.gen_api_key or None
        provider = st.session_state.gen_provider
        model = st.session_state.gen_model
        num_cards = st.session_state.gen_num_cards
        vs = get_vector_store()
        gold_at_gen_time = vs.get_gold_count()

        upd(0, "active"); prog.progress(8)
        from agents.content_extraction import extract_text_from_pdf, content_extraction_node
        pdf_text = extract_text_from_pdf(st.session_state._tmp_pdf)
        if not pdf_text.strip(): st.error("❌ No text extracted"); st.stop()
        upd(0, "done", f"Extracted {len(pdf_text):,} characters"); prog.progress(22)

        upd(1, "active"); prog.progress(27)
        llm = create_llm(provider=provider, model=model, temperature=0.7, api_key=api_key)
        state = {"pdf_content": pdf_text, "source_filename": st.session_state.source_filename}
        res = content_extraction_node(state, vs, llm); state.update(res)
        ctype = state.get("content_type", "theory"); chunks = state.get("chunks", [])
        if not chunks: st.error("❌ No chunks produced."); st.stop()
        st.session_state.content_type = ctype; st.session_state.chunks = chunks
        upd(1, "done", f"Type: {ctype} · {len(chunks)} chunks"); prog.progress(46)

        upd(2, "active"); prog.progress(50)
        from agents.flashcard_generation import flashcard_generation_node
        gen_res = flashcard_generation_node(state, vs, llm, cards_per_batch=num_cards); state.update(gen_res)
        raw_cards = state.get("raw_cards", [])
        if not raw_cards: st.error(f"❌ Generation failed: {state.get('error','')}"); st.stop()
        st.session_state.raw_cards = raw_cards
        upd(2, "done", f"Generated {len(raw_cards)} flashcards"); prog.progress(72)

        upd(3, "active"); prog.progress(77)
        from agents.quality_check import quality_check_node
        qllm = create_llm(provider=provider, model=model, temperature=0.2, api_key=api_key)
        qres = quality_check_node(state, qllm); state.update(qres)
        st.session_state.scored_cards = state.get("scored_cards", [])
        st.session_state.approved_cards = list(state.get("approved_cards", []))
        st.session_state.human_queue = state.get("human_queue", [])
        st.session_state.rejected_cards = state.get("rejected_cards", [])
        st.session_state.gold_count = vs.get_gold_count()
        na = len(st.session_state.approved_cards)
        nh = len(st.session_state.human_queue)
        nr = len(st.session_state.rejected_cards)
        upd(3, "done", f"{na} auto-approved · {nh} need review · {nr} rejected"); prog.progress(100)

        # ── Log evaluation metrics ──
        pipeline_duration = time.time() - pipeline_start
        _log_pipeline_metrics(st.session_state.scored_cards, st.session_state.approved_cards,
                              st.session_state.human_queue, st.session_state.rejected_cards,
                              raw_cards, gold_at_gen_time, pipeline_duration)

        try: os.unlink(st.session_state._tmp_pdf)
        except: pass
        time.sleep(0.7)
        st.session_state.step = "review"; st.rerun()

    except Exception as e:
        st.error(f"❌ Pipeline error: {e}")
        import traceback
        with st.expander("Full traceback"): st.code(traceback.format_exc())
        if st.button("↩ Back to Upload"): st.session_state.step = "upload"; st.rerun()


# ═══════════════════════════════════════════════════════════════════
# STEP 3 — TEACHER REVIEW
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.role == "teacher" and st.session_state.step == "review":

    if not st.session_state.teacher_authed:
        st.markdown("""
        <div class="pw-gate"><span class="pw-icon">🔐</span>
          <div class="pw-title">Teacher Access</div>
          <div class="pw-sub">Enter the teacher password to review cards.</div>
        </div>""", unsafe_allow_html=True)
        _, col_mid, _ = st.columns([1, 1.4, 1])
        with col_mid:
            pw = st.text_input("", type="password", placeholder="Enter teacher password…", label_visibility="collapsed")
            if st.button("🔓 Unlock Review Dashboard", use_container_width=True):
                if pw == TEACHER_PASSWORD:
                    st.session_state.teacher_authed = True; st.session_state.pw_error = False; st.rerun()
                else:
                    st.session_state.pw_error = True; st.rerun()
            if st.session_state.pw_error:
                st.markdown('<div class="pw-error">✗ Incorrect password.</div>', unsafe_allow_html=True)
            st.markdown('<div class="btn-ghost" style="margin-top:0.75rem">', unsafe_allow_html=True)
            if st.button("→ Skip to Study (auto-approve all)", use_container_width=True):
                all_cards = list(st.session_state.approved_cards)
                for sc in st.session_state.human_queue: all_cards.append(sc.card)
                st.session_state.approved_cards = all_cards; st.session_state.step = "study"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    # ── Authenticated Dashboard ──
    auto_approved = st.session_state.approved_cards
    human_queue = st.session_state.human_queue
    rejected = st.session_state.rejected_cards
    scored = st.session_state.scored_cards
    decisions = st.session_state.review_decisions
    edit_data = st.session_state.edit_data
    scores_list = [s.composite_score for s in scored] if scored else [0]
    avg_score = sum(scores_list) / len(scores_list)

    col_hd, col_hb = st.columns([3, 1])
    with col_hd:
        st.markdown(f'<div><div class="sec-title">Teacher Review Dashboard</div><div class="sec-sub"><b style="color:var(--text)">{st.session_state.source_filename}</b> · Content type: <b style="color:var(--violet2)">{st.session_state.content_type}</b></div></div>', unsafe_allow_html=True)
    with col_hb:
        st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
        if st.button("↩ New Upload", use_container_width=True): reset(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metric-strip">
      <div class="metric-tile"><div class="m-val">{len(scored)}</div><div class="m-lbl">Total Generated</div></div>
      <div class="metric-tile"><div class="m-val" style="color:#10b981">{len(auto_approved)}</div><div class="m-lbl">Auto-Approved</div></div>
      <div class="metric-tile"><div class="m-val" style="color:#f59e0b">{len(human_queue)}</div><div class="m-lbl">Needs Review</div></div>
      <div class="metric-tile"><div class="m-val" style="color:#f43f5e">{len(rejected)}</div><div class="m-lbl">Auto-Rejected</div></div>
      <div class="metric-tile"><div class="m-val" style="color:var(--violet2)">{avg_score:.2f}</div><div class="m-lbl">Avg Quality</div></div>
      <div class="metric-tile"><div class="m-val" style="color:var(--cyan)">{len(st.session_state.gold_cards_session)}</div><div class="m-lbl">Gold This Session</div></div>
    </div>""", unsafe_allow_html=True)

    tab_q, tab_met, tab_auto, tab_rej = st.tabs([
        f"👩‍🏫 Review Queue ({len(human_queue)})", f"📊 Quality Metrics ({len(scored)})",
        f"✅ Auto-Approved ({len(auto_approved)})", f"✗ Auto-Rejected ({len(rejected)})"])

    # ── TAB 1: REVIEW QUEUE ──
    with tab_q:
        if not human_queue:
            st.markdown(f'<div style="text-align:center;padding:3.5rem 1rem;"><div style="font-size:3rem;margin-bottom:0.75rem;">🎉</div><div style="font-family:var(--font-d);font-size:1.25rem;font-weight:700;">All {len(auto_approved)} cards auto-approved!</div><div style="color:var(--text3);font-size:0.85rem;">Click Finalize below.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:0.9rem;font-weight:600;margin-bottom:1rem;">Borderline Cards — {len(human_queue)} to review · {len(decisions)}/{len(human_queue)} reviewed</div>', unsafe_allow_html=True)
            for i, sc in enumerate(human_queue):
                card = sc.card; decision = decisions.get(i); comp = sc.composite_score
                border = {"approve":"rgba(16,185,129,0.38)","edit":"rgba(139,92,246,0.38)","reject":"rgba(244,63,94,0.3)"}.get(decision,"var(--border)")
                st.markdown(f"""
                <div class="rcard" style="border-color:{border}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.65rem;">
                    <div>{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                    <div style="display:flex;align-items:center;gap:0.5rem;">{routing_chip(sc.routing_decision)}
                      <span style="font-family:var(--font-m);font-size:0.85rem;font-weight:700;color:{'#10b981' if comp>=0.8 else '#f59e0b' if comp>=0.5 else '#f43f5e'}">{comp:.3f}</span></div>
                  </div>
                  <div class="rcard-q">Q: {card.question}</div><div class="rcard-a">A: {card.answer}</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 1.5rem;">{sbar("Groundedness ×0.4",sc.groundedness)}{sbar("Clarity ×0.3",sc.clarity)}{sbar("Uniqueness ×0.2",sc.uniqueness)}{sbar("Difficulty Cal. ×0.1",sc.difficulty_calibration)}</div>
                  <div class="rcard-just">💬 {sc.justification}</div>
                </div>""", unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown('<div class="btn-approve">', unsafe_allow_html=True)
                    if st.button("✓ Approve", key=f"app_{i}", use_container_width=True): decisions[i] = "approve"; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<div class="btn-edit">', unsafe_allow_html=True)
                    if st.button("✏️ Edit", key=f"edt_{i}", use_container_width=True): decisions[i] = "edit"; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c3:
                    st.markdown('<div class="btn-reject">', unsafe_allow_html=True)
                    if st.button("✗ Reject", key=f"rej_{i}", use_container_width=True): decisions[i] = "reject"; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                if decision == "edit":
                    qkey, akey = f"eq_{i}", f"ea_{i}"
                    if qkey not in st.session_state: st.session_state[qkey] = edit_data.get(i, {}).get("q", card.question)
                    if akey not in st.session_state: st.session_state[akey] = edit_data.get(i, {}).get("a", card.answer)
                    with st.expander("✏️ Edit card", expanded=True):
                        st.text_area("Question", key=qkey, height=80); st.text_area("Answer", key=akey, height=80)
                    edit_data[i] = {"q": st.session_state[qkey], "a": st.session_state[akey]}
                if decision:
                    lbl = {"approve":"✓ Approved","edit":"✏️ Editing","reject":"✗ Rejected"}[decision]
                    clr = {"approve":"#10b981","edit":"#a78bfa","reject":"#f43f5e"}[decision]
                    st.markdown(f'<div style="font-size:0.75rem;color:{clr};margin-bottom:0.5rem;">{lbl}</div>', unsafe_allow_html=True)

        # ── Finalize bar ──
        st.markdown("<hr>", unsafe_allow_html=True)
        auto_kept = len(auto_approved) - sum(1 for d in st.session_state.auto_edit_decisions.values() if d == "reject")
        total_final = auto_kept + sum(1 for d in decisions.values() if d in ("approve", "edit"))
        fc1, fc2 = st.columns([3, 1])
        with fc1:
            st.markdown(f'<div style="padding:0.4rem 0"><div style="font-size:0.9rem;font-weight:600">Final deck: <span style="color:var(--violet2)">{total_final} cards</span></div></div>', unsafe_allow_html=True)
        with fc2:
            if st.button("📚 Finalize & Publish →", use_container_width=True):
                from core.models import Flashcard as FC
                teacher_edits = []; final_approved = []
                # Process auto-approved
                for ai, card in enumerate(auto_approved):
                    dec = st.session_state.auto_edit_decisions.get(ai)
                    if dec == "reject": continue
                    elif dec == "edit":
                        ed = st.session_state.auto_edit_data.get(ai, {})
                        edited = FC(question=ed.get("q", card.question), answer=ed.get("a", card.answer),
                                    difficulty=card.difficulty, bloom_level=card.bloom_level,
                                    source_chunk_id=card.source_chunk_id, question_type=card.question_type)
                        final_approved.append(edited); teacher_edits.append(edited)
                    else:
                        final_approved.append(card)
                # Process review queue
                for i, sc in enumerate(human_queue):
                    card = sc.card; dec = decisions.get(i, "reject")
                    if dec == "approve": final_approved.append(card)
                    elif dec == "edit":
                        ed = edit_data.get(i, {})
                        edited = FC(question=ed.get("q", card.question), answer=ed.get("a", card.answer),
                                    difficulty=card.difficulty, bloom_level=card.bloom_level,
                                    source_chunk_id=card.source_chunk_id, question_type=card.question_type)
                        final_approved.append(edited); teacher_edits.append(edited)
                # Store gold examples
                if teacher_edits:
                    vs = get_vector_store()
                    for ed in teacher_edits:
                        vs.add_gold_flashcard({"question": ed.question, "answer": ed.answer,
                                               "difficulty": ed.difficulty, "bloom_level": ed.bloom_level,
                                               "question_type": ed.question_type})
                    st.session_state.gold_count = vs.get_gold_count()
                gold_session = [{"question": e.question, "answer": e.answer, "difficulty": e.difficulty,
                                 "bloom_level": e.bloom_level, "question_type": e.question_type}
                                for e in teacher_edits]

                # ── Publish to file (cross-session) ──
                _publish_deck_to_file(
                    final_approved, gold_session, scored,
                    metadata={
                        "source_filename": st.session_state.source_filename,
                        "content_type": st.session_state.content_type,
                        "provider": st.session_state.gen_provider,
                        "model": st.session_state.gen_model,
                        "session_id": st.session_state.get("study_session_id", ""),
                        "pipeline_metrics": st.session_state.get("pipeline_metrics", {}),
                    },
                )

                # Also store in session state for same-session access
                st.session_state.published_deck = final_approved
                st.session_state.published_gold = gold_session
                reset()
                st.session_state.role = None
                st.success("✅ Deck published! Students can now log in to study.")
                st.rerun()

    # ── TAB 2: QUALITY METRICS ──
    with tab_met:
        if not scored: st.info("No scored cards.")
        else:
            high_n = sum(1 for s in scores_list if s >= 0.8)
            mid_n = sum(1 for s in scores_list if 0.5 <= s < 0.8)
            low_n = sum(1 for s in scores_list if s < 0.5)
            st.markdown(f"""
            <div class="metric-strip" style="margin-bottom:1.6rem;">
              <div class="metric-tile"><div class="m-val" style="color:#10b981">{high_n}</div><div class="m-lbl">High ≥0.8</div></div>
              <div class="metric-tile"><div class="m-val" style="color:#f59e0b">{mid_n}</div><div class="m-lbl">Mid 0.5–0.8</div></div>
              <div class="metric-tile"><div class="m-val" style="color:#f43f5e">{low_n}</div><div class="m-lbl">Low &lt;0.5</div></div>
              <div class="metric-tile"><div class="m-val">{avg_score:.3f}</div><div class="m-lbl">Mean</div></div>
              <div class="metric-tile"><div class="m-val">{max(scores_list):.3f}</div><div class="m-lbl">Best</div></div>
              <div class="metric-tile"><div class="m-val">{min(scores_list):.3f}</div><div class="m-lbl">Worst</div></div>
            </div>""", unsafe_allow_html=True)
            for sc in sorted(scored, key=lambda x: x.composite_score, reverse=True):
                card = sc.card; comp = sc.composite_score; cc = "#10b981" if comp >= 0.8 else ("#f59e0b" if comp >= 0.5 else "#f43f5e")
                st.markdown(f"""
                <div class="rcard">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.45rem;">
                    <div style="font-size:0.88rem;font-weight:600;flex:1;margin-right:1rem;line-height:1.4">{card.question[:100]}{'…' if len(card.question)>100 else ''}</div>
                    <div style="display:flex;align-items:center;gap:0.45rem;">{routing_chip(sc.routing_decision)}<span style="font-family:var(--font-m);font-size:0.85rem;font-weight:700;color:{cc}">{comp:.3f}</span></div>
                  </div>
                  <div style="margin-bottom:0.55rem">{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 1.5rem">{sbar("Groundedness",sc.groundedness)}{sbar("Clarity",sc.clarity)}{sbar("Uniqueness",sc.uniqueness)}{sbar("Difficulty Cal.",sc.difficulty_calibration)}</div>
                  <div class="rcard-just">💬 {sc.justification}</div>
                </div>""", unsafe_allow_html=True)

    # ── TAB 3: AUTO-APPROVED ──
    with tab_auto:
        auto_edit_data = st.session_state.auto_edit_data
        auto_edit_decisions = st.session_state.auto_edit_decisions
        if not auto_approved: st.info("No cards were auto-approved.")
        else:
            st.markdown(f'<div class="sec-sub">{len(auto_approved)} cards scored ≥0.80. You can still edit or reject any card.</div>', unsafe_allow_html=True)
            for ai, card in enumerate(auto_approved):
                sc_m = next((s for s in scored if s.card.question == card.question), None)
                sc_txt = f"{sc_m.composite_score:.3f}" if sc_m else "—"
                decision = auto_edit_decisions.get(ai)
                border = {"edit": "rgba(139,92,246,0.38)", "reject": "rgba(244,63,94,0.3)"}.get(decision, "rgba(16,185,129,0.18)")
                st.markdown(f"""
                <div class="rcard" style="border-color:{border}">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                    <div>{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                    <span style="font-family:var(--font-m);font-size:0.78rem;color:#10b981;font-weight:600">{sc_txt}</span>
                  </div>
                  <div class="rcard-q">Q: {card.question}</div><div class="rcard-a">A: {card.answer}</div>
                </div>""", unsafe_allow_html=True)
                ac1, ac2, ac3 = st.columns(3)
                with ac1:
                    st.markdown('<div class="btn-approve">', unsafe_allow_html=True)
                    if st.button("✓ Keep", key=f"aacc_{ai}", use_container_width=True): auto_edit_decisions.pop(ai, None); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with ac2:
                    st.markdown('<div class="btn-edit">', unsafe_allow_html=True)
                    if st.button("✏️ Edit", key=f"aedt_{ai}", use_container_width=True): auto_edit_decisions[ai] = "edit"; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with ac3:
                    st.markdown('<div class="btn-reject">', unsafe_allow_html=True)
                    if st.button("✗ Reject", key=f"arej_{ai}", use_container_width=True): auto_edit_decisions[ai] = "reject"; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                if decision == "edit":
                    qkey, akey = f"aeq_{ai}", f"aea_{ai}"
                    if qkey not in st.session_state: st.session_state[qkey] = auto_edit_data.get(ai, {}).get("q", card.question)
                    if akey not in st.session_state: st.session_state[akey] = auto_edit_data.get(ai, {}).get("a", card.answer)
                    with st.expander("✏️ Edit card", expanded=True):
                        st.text_area("Question", key=qkey, height=80); st.text_area("Answer", key=akey, height=80)
                    auto_edit_data[ai] = {"q": st.session_state[qkey], "a": st.session_state[akey]}

    # ── TAB 4: AUTO-REJECTED ──
    with tab_rej:
        if not rejected: st.info("No cards were auto-rejected.")
        else:
            st.markdown(f'<div class="sec-sub">{len(rejected)} cards scored below 0.50.</div>', unsafe_allow_html=True)
            for sc in rejected:
                card = sc.card
                st.markdown(f"""
                <div class="rcard" style="border-color:rgba(244,63,94,0.14);opacity:0.72">
                  <div style="display:flex;justify-content:space-between;margin-bottom:0.4rem"><div>{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}</div>
                    <span style="font-family:var(--font-m);font-size:0.78rem;color:#f43f5e;font-weight:600">{sc.composite_score:.3f}</span></div>
                  <div style="font-size:0.88rem;color:var(--text2);margin-bottom:0.28rem">Q: {card.question}</div>
                  <div style="font-size:0.82rem;color:var(--text3)">A: {card.answer}</div>
                  <div class="rcard-just">💬 {sc.justification}</div>
                </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# STEP 4 — STUDY MODE  (with flip timestamps for eval)
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.step == "study":
    final_deck = st.session_state.approved_cards
    scored = st.session_state.scored_cards
    scores_list = [s.composite_score for s in scored] if scored else [0]
    avg_s = sum(scores_list) / len(scores_list)

    if not final_deck:
        st.warning("No approved cards.")
        if st.session_state.role == "teacher" and st.button("↩ Back to Review"):
            st.session_state.step = "review"; st.rerun()
        st.stop()

    sh, sb = st.columns([3, 1])
    with sh:
        st.markdown(f'<div><div class="sec-title">Study Mode</div><div class="sec-sub"><b style="color:var(--text)">{st.session_state.source_filename}</b> · {len(final_deck)} cards · {st.session_state.content_type}</div></div>', unsafe_allow_html=True)
    with sb:
        if st.session_state.role == "teacher":
            sb1, sb2 = st.columns(2)
            with sb1:
                st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
                if st.button("← Review", use_container_width=True): st.session_state.step = "review"; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with sb2:
                st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
                if st.button("↩ New Upload", use_container_width=True): reset(); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
            if st.button("Switch Role", use_container_width=True): full_reset(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.role == "teacher":
        st.markdown(f"""
        <div class="metric-strip" style="grid-template-columns:repeat(4,1fr);margin-bottom:1rem">
          <div class="metric-tile"><div class="m-val" style="color:var(--violet2)">{len(final_deck)}</div><div class="m-lbl">Final Cards</div></div>
          <div class="metric-tile"><div class="m-val" style="color:var(--cyan)">{st.session_state.content_type or "—"}</div><div class="m-lbl">Content Type</div></div>
          <div class="metric-tile"><div class="m-val" style="color:#f59e0b">{len(st.session_state.gold_cards_session)}</div><div class="m-lbl">Gold Examples</div></div>
          <div class="metric-tile"><div class="m-val">{avg_s:.2f}</div><div class="m-lbl">Avg Quality</div></div>
        </div>""", unsafe_allow_html=True)

    if st.session_state.role == "teacher":
        tab_fc, tab_list, tab_mets, tab_exp = st.tabs(["🃏 Flashcards", "📋 Card List", f"📊 Quality Metrics ({len(scored)})", "💾 Export"])
    else:
        tab_fc, tab_list, tab_exp = st.tabs(["🃏 Study", "📋 All Cards", "💾 Export"])
        tab_mets = None

    # ── Flashcards (SM2 Spaced Repetition) ──
    with tab_fc:
        # Filters — teachers only. Students study the full deck.
        is_teacher = st.session_state.role == "teacher"
        if is_teacher:
            fc1, fc2, fc3 = st.columns(3)
            with fc1: filter_diff = st.multiselect("Difficulty", ["easy","medium","hard"], default=["easy","medium","hard"])
            with fc2: filter_bloom = st.multiselect("Bloom Level", ["remember","understand","apply","analyze","evaluate","create"], default=["remember","understand","apply","analyze","evaluate","create"])
            with fc3: filter_type = st.multiselect("Type", ["definition","concept","application","comparison"], default=["definition","concept","application","comparison"])
            filtered = [c for c in final_deck if c.difficulty in filter_diff and c.bloom_level in filter_bloom and c.question_type in filter_type]
        else:
            filtered = list(final_deck)
        filtered_indices = [i for i, c in enumerate(final_deck) if c in filtered]

        if not filtered:
            st.info("No cards match your filters." if is_teacher else "No cards available.")
        else:
            sm2_stats = get_sm2_summary(st.session_state, len(final_deck))
            due_indices = [i for i in get_due_cards(st.session_state, len(final_deck)) if i in filtered_indices]

            # SM2 summary — compact for students, detailed for teachers
            if is_teacher:
                st.markdown(f"""
                <div class="sm2-summary">
                  <span class="sm2-pill" style="color:var(--violet2);border-color:rgba(139,92,246,0.3);">● {sm2_stats['new']} new</span>
                  <span class="sm2-pill" style="color:#f43f5e;border-color:rgba(244,63,94,0.3);">● {sm2_stats['due']} due</span>
                  <span class="sm2-pill" style="color:#f59e0b;border-color:rgba(245,158,11,0.3);">● {sm2_stats['learning']} learning</span>
                  <span class="sm2-pill" style="color:#10b981;border-color:rgba(16,185,129,0.3);">● {sm2_stats['mastered']} mastered</span>
                  <span class="sm2-pill">↻ {sm2_stats['total_reviews']} reviews</span>
                </div>""", unsafe_allow_html=True)
                study_mode = st.radio("Study mode", ["📚 SM2 Study", "📋 Grid View"], horizontal=True, key="study_mode_toggle", label_visibility="collapsed")
            else:
                # Students get a minimal one-line summary, no toggle (always SM2)
                studied_n = sm2_stats['learning'] + sm2_stats['mastered']
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;
                  padding:0.5rem 0.85rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);">
                  <span style="font-family:var(--font-m);font-size:0.72rem;color:var(--text2);">
                    {len(final_deck)} cards · {len(due_indices)} due · {studied_n} studied
                  </span>
                  <span style="font-family:var(--font-m);font-size:0.72rem;color:var(--text3);">
                    ↻ {sm2_stats['total_reviews']} reviews
                  </span>
                </div>""", unsafe_allow_html=True)
                study_mode = "📚 SM2 Study"  # students always get SM2

            if study_mode == "📚 SM2 Study":
                # ── SM2 single-card study mode ──
                if not due_indices:
                    st.markdown("""
                    <div style="text-align:center;padding:3rem 1rem;">
                      <div style="font-size:2.5rem;margin-bottom:0.75rem;">🎉</div>
                      <div style="font-family:var(--font-d);font-size:1.2rem;font-weight:700;margin-bottom:0.4rem;">All caught up!</div>
                      <div style="color:var(--text3);font-size:0.85rem;">No cards are due right now. Switch to Grid View to browse, or come back later.</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    # Pick current card
                    cur_idx = st.session_state.get("sm2_current_idx")
                    if cur_idx is None or cur_idx not in due_indices:
                        cur_idx = due_indices[0]
                        st.session_state.sm2_current_idx = cur_idx

                    card = final_deck[cur_idx]
                    sm2 = get_or_create_sm2(st.session_state, cur_idx)
                    flipped = st.session_state.flip_states.get(cur_idx, False)
                    is_repeat = len(sm2.review_history) > 0

                    # Progress bar
                    reviewed_n = sum(1 for i in filtered_indices
                                     if st.session_state.get("sm2_cards", {}).get(i)
                                     and st.session_state["sm2_cards"][i].last_reviewed)
                    pct = int(reviewed_n / len(filtered) * 100) if filtered else 0

                    st.markdown(f"""
                    <div class="sm2-progress">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">
                        <span style="font-family:var(--font-m);font-size:0.72rem;color:var(--text2);">
                          Card {due_indices.index(cur_idx) + 1} of {len(due_indices)} due
                        </span>
                        <span style="font-family:var(--font-m);font-size:0.72rem;color:var(--text3);">
                          {reviewed_n}/{len(filtered)} studied · {pct}%
                        </span>
                      </div>
                      <div style="background:var(--surface3);border-radius:99px;height:5px;overflow:hidden;">
                        <div style="width:{pct}%;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--violet),var(--cyan));transition:width 0.3s;"></div>
                      </div>
                    </div>""", unsafe_allow_html=True)

                    # Repeat badge
                    if is_repeat:
                        fail_count = sum(1 for _, q in sm2.review_history if q < 3)
                        if fail_count > 0:
                            if is_teacher:
                                st.markdown(f'<div class="sm2-repeat-badge">🔄 Seeing this again · failed {fail_count}× before</div>', unsafe_allow_html=True)
                            else:
                                st.markdown('<div class="sm2-repeat-badge">🔄 Let\'s try this one again</div>', unsafe_allow_html=True)

                    # Card display (centered, larger)
                    _, card_col, _ = st.columns([0.5, 2, 0.5])
                    with card_col:
                        front_label = f"Question · {diff_chip(card.difficulty)} {chip(card.bloom_level, 'bloom')}" if is_teacher else "Question"
                        st.markdown(f"""
                        <div class="fc-scene{"  flipped" if flipped else ""}" style="height:260px;">
                          <div class="fc-inner">
                            <div class="fc-face fc-front">
                              <div class="fc-label">{front_label}</div>
                              <div class="fc-text" style="font-size:1.05rem;">{card.question}</div>
                              <span class="fc-hint">tap to reveal →</span>
                            </div>
                            <div class="fc-face fc-back">
                              <div class="fc-label" style="color:var(--cyan)">Answer</div>
                              <div class="fc-text fc-ans" style="font-size:1.05rem;">{card.answer}</div>
                            </div>
                          </div>
                        </div>""", unsafe_allow_html=True)

                        if not flipped:
                            if st.button("👁 Show Answer", key=f"sm2_reveal_{cur_idx}", use_container_width=True):
                                st.session_state.flip_states[cur_idx] = True
                                st.session_state.flip_times.setdefault(cur_idx, []).append(time.time())
                                st.rerun()
                        else:
                            # Rating prompt — show technical details only for teachers
                            if is_teacher:
                                st.markdown(f"""
                                <div style="text-align:center;margin:0.6rem 0 0.5rem;">
                                  <div style="font-size:0.82rem;color:var(--text2);margin-bottom:0.15rem;">How well did you know this?</div>
                                  <div style="font-family:var(--font-m);font-size:0.62rem;color:var(--text3);">
                                    EF {sm2.easiness_factor:.2f} · {sm2.repetitions} reps · {len(sm2.review_history)} reviews
                                  </div>
                                </div>""", unsafe_allow_html=True)
                            else:
                                st.markdown('<div style="text-align:center;margin:0.6rem 0 0.5rem;font-size:0.82rem;color:var(--text2);">How well did you know this?</div>', unsafe_allow_html=True)

                            # Compute preview intervals for each rating
                            def _preview_interval(quality):
                                ef = max(1.3, sm2.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
                                if quality < 3: return "again now"
                                elif sm2.repetitions == 0: return "1 day"
                                elif sm2.repetitions == 1: return "6 days"
                                else: return f"{round(sm2.interval * ef)} days"

                            # Rating buttons — 4 columns, styled with CSS wrappers
                            r1, r2, r3, r4 = st.columns(4)
                            with r1:
                                st.markdown('<div class="btn-again">', unsafe_allow_html=True)
                                if st.button(f"✗ Again · {_preview_interval(1)}", key=f"sm2r_again_{cur_idx}", use_container_width=True):
                                    sm2.review(1)
                                    st.session_state.flip_times.setdefault(cur_idx, []).append(time.time())
                                    st.session_state.flip_states[cur_idx] = False
                                    remaining = [i for i in due_indices if i != cur_idx and get_or_create_sm2(st.session_state, i).is_due]
                                    remaining.append(cur_idx)  # failed card goes to back
                                    st.session_state.sm2_current_idx = remaining[0]
                                    st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
                            with r2:
                                st.markdown('<div class="btn-hard">', unsafe_allow_html=True)
                                if st.button(f"⚡ Hard · {_preview_interval(3)}", key=f"sm2r_hard_{cur_idx}", use_container_width=True):
                                    sm2.review(3)
                                    st.session_state.flip_times.setdefault(cur_idx, []).append(time.time())
                                    st.session_state.flip_states[cur_idx] = False
                                    remaining = [i for i in due_indices if i != cur_idx and get_or_create_sm2(st.session_state, i).is_due]
                                    st.session_state.sm2_current_idx = remaining[0] if remaining else None
                                    st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
                            with r3:
                                st.markdown('<div class="btn-good">', unsafe_allow_html=True)
                                if st.button(f"✓ Good · {_preview_interval(4)}", key=f"sm2r_good_{cur_idx}", use_container_width=True):
                                    sm2.review(4)
                                    st.session_state.flip_times.setdefault(cur_idx, []).append(time.time())
                                    st.session_state.flip_states[cur_idx] = False
                                    remaining = [i for i in due_indices if i != cur_idx and get_or_create_sm2(st.session_state, i).is_due]
                                    st.session_state.sm2_current_idx = remaining[0] if remaining else None
                                    st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
                            with r4:
                                st.markdown('<div class="btn-easy">', unsafe_allow_html=True)
                                if st.button(f"★ Easy · {_preview_interval(5)}", key=f"sm2r_easy_{cur_idx}", use_container_width=True):
                                    sm2.review(5)
                                    st.session_state.flip_times.setdefault(cur_idx, []).append(time.time())
                                    st.session_state.flip_states[cur_idx] = False
                                    remaining = [i for i in due_indices if i != cur_idx and get_or_create_sm2(st.session_state, i).is_due]
                                    st.session_state.sm2_current_idx = remaining[0] if remaining else None
                                    st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)

            else:
                # ── Grid view (original behavior) ──
                st.markdown(f'<div style="font-size:0.77rem;color:var(--text3);margin-bottom:1.25rem">{len(filtered)} cards · click to flip</div>', unsafe_allow_html=True)
                for row_start in range(0, len(filtered), 3):
                    cols = st.columns(3)
                    for ci, card in enumerate(filtered[row_start:row_start+3]):
                        idx = row_start + ci; flipped = st.session_state.flip_states.get(idx, False)
                        sm2 = get_or_create_sm2(st.session_state, idx)
                        with cols[ci]:
                            st.markdown(f"""
                            <div class="fc-scene{"  flipped" if flipped else ""}"><div class="fc-inner">
                              <div class="fc-face fc-front"><div class="fc-label">Question</div><div class="fc-text">{card.question}</div><span class="fc-hint">tap to reveal →</span></div>
                              <div class="fc-face fc-back"><div class="fc-label" style="color:var(--cyan)">Answer</div><div class="fc-text fc-ans">{card.answer}</div><span class="fc-hint">← tap to hide</span></div>
                            </div></div>""", unsafe_allow_html=True)
                            lbl = "↩ Hide" if flipped else "👁 Reveal"
                            if st.button(lbl, key=f"flip_{idx}", use_container_width=True):
                                st.session_state.flip_states[idx] = not flipped
                                st.session_state.flip_times.setdefault(idx, []).append(time.time())
                                st.rerun()
                            status_color = {"new":"var(--violet2)","due":"#f43f5e"}.get(sm2.status, "var(--text3)")
                            st.markdown(f'<div style="text-align:center;margin:0.3rem 0 0.85rem">{diff_chip(card.difficulty)}{chip(card.bloom_level,"bloom")} <span style="font-family:var(--font-m);font-size:0.6rem;color:{status_color};">{sm2.status}</span></div>', unsafe_allow_html=True)

    # ── Card List ──
    with tab_list:
        gold_questions = {g["question"] for g in st.session_state.gold_cards_session}
        st.markdown('<div class="sec-sub">All approved flashcards in list view.</div>', unsafe_allow_html=True)
        for i, card in enumerate(final_deck):
            is_gold = card.question in gold_questions
            with st.expander(f"Card {i+1}{' ★' if is_gold else ''} — {card.question[:72]}{'…' if len(card.question)>72 else ''}"):
                gold_badge = '<span style="font-family:var(--font-m);font-size:0.62rem;color:#f59e0b;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.25);border-radius:99px;padding:0.1rem 0.5rem;margin-right:0.4rem;">★ gold</span>' if is_gold else ""
                st.markdown(f"""
                <div style="margin-bottom:0.5rem">{gold_badge}{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                <div style="font-weight:600;margin-bottom:0.4rem;line-height:1.5">Q: {card.question}</div>
                <div style="color:var(--cyan);line-height:1.5">A: {card.answer}</div>
                <div style="font-size:0.7rem;color:var(--text3);margin-top:0.4rem;font-family:var(--font-m)">source: {card.source_chunk_id}</div>""", unsafe_allow_html=True)

    # ── Quality Metrics (teacher only) ──
    if tab_mets is not None:
     with tab_mets:
        if not scored: st.info("No quality scores.")
        else:
            high_s = sum(1 for s in scores_list if s >= 0.8); mid_s = sum(1 for s in scores_list if 0.5 <= s < 0.8); low_s = sum(1 for s in scores_list if s < 0.5)
            st.markdown(f"""
            <div class="metric-strip" style="margin-bottom:1.6rem">
              <div class="metric-tile"><div class="m-val" style="color:#10b981">{high_s}</div><div class="m-lbl">High ≥0.8</div></div>
              <div class="metric-tile"><div class="m-val" style="color:#f59e0b">{mid_s}</div><div class="m-lbl">Mid 0.5–0.8</div></div>
              <div class="metric-tile"><div class="m-val" style="color:#f43f5e">{low_s}</div><div class="m-lbl">Low &lt;0.5</div></div>
              <div class="metric-tile"><div class="m-val">{avg_s:.3f}</div><div class="m-lbl">Mean</div></div>
            </div>""", unsafe_allow_html=True)
            for sc in sorted(scored, key=lambda x: x.composite_score, reverse=True):
                card = sc.card; comp = sc.composite_score; cc = "#10b981" if comp >= 0.8 else ("#f59e0b" if comp >= 0.5 else "#f43f5e")
                st.markdown(f"""
                <div class="rcard">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.45rem;">
                    <div style="font-size:0.88rem;font-weight:600;flex:1;margin-right:1rem">{card.question[:100]}{'…' if len(card.question)>100 else ''}</div>
                    <span style="font-family:var(--font-m);font-size:0.85rem;font-weight:700;color:{cc}">{comp:.3f}</span>
                  </div>
                  <div style="margin-bottom:0.55rem">{diff_chip(card.difficulty)}{chip(card.bloom_level,'bloom')}{chip(card.question_type,'type')}</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 1.5rem">{sbar("Groundedness",sc.groundedness)}{sbar("Clarity",sc.clarity)}{sbar("Uniqueness",sc.uniqueness)}{sbar("Difficulty Cal.",sc.difficulty_calibration)}</div>
                  <div class="rcard-just">💬 {sc.justification}</div>
                </div>""", unsafe_allow_html=True)

    # ── Export (with eval data) ──
    with tab_exp:
        st.markdown('<div class="sec-sub">Download your flashcard deck and evaluation data.</div>', unsafe_allow_html=True)

        # Basic deck export
        export_data = {
            "source": st.session_state.source_filename, "content_type": st.session_state.content_type,
            "total_cards": len(final_deck), "gold_examples_stored": st.session_state.gold_count,
            "quality_summary": {"mean": round(avg_s, 3), "best": round(max(scores_list), 3), "worst": round(min(scores_list), 3)},
            "flashcards": [{"question": c.question, "answer": c.answer, "difficulty": c.difficulty,
                            "bloom_level": c.bloom_level, "question_type": c.question_type,
                            "source_chunk_id": c.source_chunk_id} for c in final_deck],
        }
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        tsv_lines = ["Question\tAnswer\tDifficulty\tBloom Level\tType"] + \
                    [f"{c.question}\t{c.answer}\t{c.difficulty}\t{c.bloom_level}\t{c.question_type}" for c in final_deck]
        stem = Path(st.session_state.source_filename).stem if st.session_state.source_filename else "deck"

        dc1, dc2 = st.columns(2)
        with dc1:
            st.download_button("⬇️ Download JSON", data=json_str,
                               file_name=f"{stem}_flashcards.json", mime="application/json", use_container_width=True)
        with dc2:
            st.download_button("⬇️ Download TSV (Anki)", data="\n".join(tsv_lines),
                               file_name=f"{stem}_flashcards.tsv", mime="text/tab-separated-values", use_container_width=True)

        # ── Evaluation data export ──
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.87rem;font-weight:600;margin-bottom:0.4rem;">📊 Evaluation Data Export</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.76rem;color:var(--text3);margin-bottom:0.75rem;">Includes pipeline metrics, per-card quality scores, flip timestamps, and study interaction data for your user study.</div>', unsafe_allow_html=True)

        eval_data = _build_eval_export(final_deck, scored)
        eval_json = json.dumps(eval_data, indent=2, ensure_ascii=False)
        sid = st.session_state.get("study_session_id", "session")

        st.download_button(
            "⬇️ Download Eval Data (JSON)",
            data=eval_json,
            file_name=f"{stem}_eval_{sid}.json",
            mime="application/json",
            use_container_width=True,
        )

        # Also auto-save to eval_logs for the researcher
        eval_file = EVAL_LOG_DIR / f"study_{sid}_{stem}.json"
        with open(eval_file, "w", encoding="utf-8") as f:
            f.write(eval_json)

        st.markdown(f'<div style="font-size:0.7rem;color:var(--text3);margin-top:0.5rem;">Auto-saved to <code>eval_logs/study_{sid}_{stem}.json</code></div>', unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        with st.expander("Preview eval data"):
            st.code(eval_json[:3000] + ("\n…" if len(eval_json) > 3000 else ""), language="json")

st.markdown('</div>', unsafe_allow_html=True)