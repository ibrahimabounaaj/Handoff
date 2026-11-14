import html
import json
import os
import re
import tempfile
import uuid
from datetime import datetime

import streamlit as st

import handoff as hb

st.set_page_config(page_title="Handoff", page_icon="🤝", layout="wide")

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
DEMO_USERS = {
    "ibrahim@handoff.dev": "Ibrahim",
    "sarah@handoff.dev": "Sarah",
    "kevin@handoff.dev": "Kevin",
}


# ---------------------------------------------------------------- storage
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"users": {}, "projects": {}}


def save(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, default=str)


db = load()
ss = st.session_state
ss.setdefault("page", "landing")
ss.setdefault("email", None)
ss.setdefault("pid", None)
ss.setdefault("thread_id", None)
ss.setdefault("messages", [])
ss.setdefault("uploaded", set())
ss.setdefault("theme", "dark")


def me():
    return db["users"].get(ss.email, {}).get("name", "?")


@st.cache_data(ttl=120, show_spinner=False)
def memory(aid):
    """One Backboard call for notes + facts, cached so clicks don't refetch it."""
    return hb.get_memory(aid)


def keep_note(p, note):
    """The app keeps its own copy of every session note. Backboard gets one too (so every model
    sees it), but its auto-memory may later merge or rewrite memories, so the sidebar reads this copy."""
    if "notes" not in p:  # first save on an older project: start from what Backboard has
        try:
            p["notes"] = [dict(n) for n in memory(p["assistant_id"])[0]]
        except Exception:
            p["notes"] = []
    note = dict(note)
    note["id"] = note.get("id") or uuid.uuid4().hex
    if all(x["id"] != note["id"] for x in p["notes"]):
        p["notes"].append(note)
    save(db)


def auto_save():
    """Writes a session note automatically when someone leaves a project they worked in."""
    if ss.get("page") == "project" and ss.get("dirty") and ss.get("pid"):
        p = db["projects"].get(ss.pid)
        if p:
            model = ss.get("model") or list(hb.MODELS)[0]
            try:
                with st.spinner(f"Saving {me()}'s session note to the project memory..."):
                    if ss.get("thread_id"):
                        note = hb.end_session(p["assistant_id"], ss.thread_id, me(), model)
                    else:  # left before any reply arrived: save what they typed instead
                        note = hb.quick_note(p["assistant_id"], me(), model,
                                             [m["text"] for m in ss.messages if m["role"] == "user"])
                if isinstance(note, str):  # older backend returned just the text
                    note = {"id": "", "author": me(), "model": model,
                            "time": datetime.now().strftime("%b %d %H:%M"), "text": note}
                keep_note(p, note)
                memory.clear()
                ss.flash = f"{me()}'s session note was saved to the project memory."
                print("[handoff] session note saved", flush=True)
            except Exception as e:
                print(f"[handoff] session note failed: {type(e).__name__}: {e}", flush=True)
                ss.flash = "Couldn't save the session note (Backboard didn't respond)."
    ss.dirty = False


def go(page, **kw):
    if page != "project":
        auto_save()
    ss.page = page
    for k, v in kw.items():
        ss[k] = v
    st.rerun()


def open_project(pid):
    ss.pid, ss.thread_id, ss.messages = pid, None, []
    go("project")


def sign_in(email, name):
    auto_save()
    email = email.strip().lower()
    db["users"].setdefault(email, {"name": name.strip() or email.split("@")[0]})
    save(db)
    ss.email = email
    ss.pid, ss.thread_id, ss.messages = None, None, []


# ---------------------------------------------------------------- styling
# Brand: Espresso / Black / Sand / Off-White, Inter. Colours live in CSS variables
# so the light/dark toggle only swaps the variables. Text fields are Sand with black
# text in both themes, so they always look the same.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
  --black:#000000; --espresso:#332421; --sand:#EAE1CA; --offwhite:#F2F0EF;
  --bg:var(--espresso); --card:var(--sand); --text:var(--offwhite);
  --line:rgba(242,240,239,.16); --btn-bg:var(--sand); --btn-text:var(--black);
  --input-bg:var(--sand); --input-text:var(--black);
  --note:var(--sand); --note-line:var(--espresso); --toggle:var(--offwhite);
}
html, body, .stApp, [data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {background:var(--bg) !important;}
header[data-testid="stHeader"] {background:transparent !important;}
[data-testid="stDecoration"], [data-testid="InputInstructions"] {display:none !important;}
.stApp p, .stApp li, .stApp label, .stApp small, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp button, .stApp a, .stApp div, .stApp span:not([data-testid="stIconMaterial"]),
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] label, [data-testid="stPopoverBody"] div,
[data-testid="stPopoverBody"] span:not([data-testid="stIconMaterial"]), [data-testid="stPopoverBody"] button {
  font-family:'Inter', system-ui, sans-serif; color:var(--text);}
.stApp p, .stApp li, .stApp label, .stApp small, [data-testid="stPopoverBody"] p {font-weight:500;}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {font-weight:700; letter-spacing:-.02em;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {opacity:1 !important; color:var(--text) !important;}

/* hide Streamlit chrome */
[data-testid="stToolbar"], [data-testid="stMainMenu"], [data-testid="stDeployButton"],
[data-testid="stAppDeployButton"], #MainMenu, [data-testid="stHeaderActionElements"],
.stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a, .stMarkdown h4 a,
[data-testid="stHeadingWithActionElements"] a {display:none !important;}
.block-container {padding-top:4rem !important; padding-bottom:3rem !important;}

/* buttons */
button {border-radius:8px !important; font-weight:600 !important; transition:transform .12s ease, filter .12s ease;}
button[kind="primary"], button[kind="primaryFormSubmit"] {background:var(--btn-bg) !important; border:1px solid var(--btn-bg) !important;}
button[kind="primary"] p, button[kind="primaryFormSubmit"] p {color:var(--btn-text) !important; font-weight:600;}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {filter:brightness(.93); transform:translateY(-1px);}
button[kind="secondary"], button[kind="secondaryFormSubmit"] {background:transparent !important; border:1px solid var(--line) !important;}
button[kind="secondary"]:hover {border-color:var(--text) !important;}
button:disabled {opacity:.45;}

/* text fields: Sand with black text everywhere, including popovers and dropdowns */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"],
[data-testid="stTextInputRootElement"], [data-baseweb="select"] > div,
[data-testid="stChatInput"], [data-testid="stChatInput"] > div {
  background:var(--input-bg) !important; border-color:var(--line) !important;}
input, textarea {background:var(--input-bg) !important; color:var(--input-text) !important;
  -webkit-text-fill-color:var(--input-text) !important; font-family:'Inter', system-ui, sans-serif !important; font-weight:500 !important;}
input::placeholder, textarea::placeholder {color:var(--input-text) !important; -webkit-text-fill-color:var(--input-text) !important; opacity:.5 !important;}
[data-baseweb="input"] button, [data-baseweb="base-input"] button {background:transparent !important; border:none !important;}
[data-baseweb="input"] button svg, [data-baseweb="select"] svg {fill:var(--input-text) !important; color:var(--input-text) !important;}
[data-baseweb="select"] div, [data-baseweb="select"] span {color:var(--input-text) !important; background-color:transparent !important;}
[data-baseweb="select"] > div {background-color:var(--input-bg) !important;}
.react-aria-ComboBox > div {background:var(--input-bg) !important; border-color:var(--line) !important;}
.react-aria-ComboBox button, .react-aria-ComboBox button svg {background:transparent !important; color:var(--input-text) !important;}
.react-aria-ComboBox svg path[d^="M0 0h24"] {fill:none !important;}
.react-aria-ComboBox svg path:not([d^="M0 0h24"]) {fill:var(--input-text) !important;}
[role="listbox"], [data-baseweb="menu"] {background:var(--input-bg) !important;}
[role="option"], [role="option"] * {color:var(--input-text) !important; background-color:transparent;
  font-family:'Inter', system-ui, sans-serif !important; font-weight:500;}
[role="option"]:hover, [role="option"][aria-selected="true"], [role="option"][data-focused="true"] {background:rgba(0,0,0,.08) !important;}
[data-testid="stChatInputSubmitButton"] {background:var(--espresso) !important; border:none !important;}
[data-testid="stChatInputSubmitButton"] svg {color:var(--offwhite) !important; fill:var(--offwhite) !important;}

/* panels: always beige with black text in both themes (no black boxes anywhere).
   The variables are redefined inside each panel, so everything in it switches automatically. */
[data-testid="stForm"], [data-testid="stExpander"] details, [data-testid="stPopoverBody"],
[data-testid="stFileUploaderDropzone"], [class*="st-key-pcard"], .st-key-democard, .card, .umsg {
  --text:var(--black); --line:rgba(0,0,0,.16); --btn-bg:var(--espresso); --btn-text:var(--offwhite);
  --input-bg:var(--offwhite); --input-text:var(--black);
  background:var(--sand) !important; color:var(--black); border:1px solid var(--line) !important; border-radius:8px !important;}
[class*="st-key-pcard"], .st-key-democard {padding:16px !important;}
[data-testid="stPopoverBody"] [data-testid="stForm"], [data-testid="stExpander"] [data-testid="stForm"] {border:none !important; padding:0 !important;}
[data-testid="stFileUploaderDropzone"] {border-style:dashed !important; border-width:1.5px !important;}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {color:var(--black) !important;}
[data-testid="stExpander"] summary svg {fill:var(--black) !important;}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] details[open] > summary {background:transparent !important;}
[data-testid="stCheckbox"] span {border-color:var(--text) !important;}
.stTabs [data-baseweb="tab-highlight"] {background-color:var(--text) !important;}
.stTabs [data-baseweb="tab-border"] {background-color:var(--line) !important;}
.stTabs [data-baseweb="tab"] p {font-weight:600;}

/* top bar: solid strip so content scrolls under it; logo + word are one home button */
.topbar {position:fixed; top:0; left:0; right:0; height:3.6rem; background:var(--bg); border-bottom:1px solid var(--line); z-index:999980;}
.mini-logo {position:fixed; top:.45rem; left:1rem; z-index:1000000; color:var(--text); pointer-events:none; overflow:visible;}
.fly {animation:fly 3.2s ease-in-out infinite; transform-box:fill-box; transform-origin:center;}
@keyframes fly {0%,18% {transform:translate(0,0) rotate(0); opacity:1;}
  55% {transform:translate(9px,-7px) rotate(14deg); opacity:.85;}
  70% {transform:translate(11px,-8px) rotate(16deg); opacity:0;}
  71% {transform:translate(0,4px) rotate(0); opacity:0;}
  85%,100% {transform:translate(0,0) rotate(0); opacity:1;}}
.st-key-home_btn {position:fixed; top:.55rem; left:.6rem; z-index:999999; width:auto !important;}
.st-key-home_btn button {border:none !important; background:transparent !important; padding:0 10px 0 50px !important; min-height:40px !important;}
.st-key-home_btn button p {font-weight:800 !important; font-size:1.1rem; letter-spacing:-.02em;}
.st-key-theme_btn {position:fixed; top:1rem; right:1.4rem; z-index:999999; width:auto !important;}
.st-key-theme_btn button {width:28px !important; height:28px !important; min-height:28px !important; padding:0 !important;
  border-radius:50% !important; background:var(--toggle) !important; border:2px solid var(--line) !important;}
.st-key-acct {position:fixed; top:.6rem; right:4rem; z-index:999999; width:auto !important;}
.st-key-acct button {border-radius:999px !important; min-height:36px !important; padding:0 14px !important;}
.welcome {font-size:1rem; font-weight:500; line-height:1.5; margin:.2rem 0 .8rem 0;}
.grp {font-weight:700; font-size:.8rem; margin:.5rem 0 .2rem 0;}
.bb-footer {position:fixed; bottom:.4rem; left:.8rem; font-size:.75rem; font-weight:500; z-index:1000;
  background:var(--bg); padding:2px 6px; border-radius:6px;}
.bb-footer a {color:inherit; font-weight:700;}

/* landing + login */
.hero {text-align:center;}
.hero-center {padding-top:14vh; margin-bottom:1.6rem;}
.hero h1 {font-size:4.6rem; font-weight:800; letter-spacing:-.045em; margin:.4rem 0 .1rem 0; line-height:1;}
.hero h2 {font-weight:800; letter-spacing:-.03em;}
.hero .tag {font-size:1.25rem; font-weight:600; margin-top:.6rem;}
.or {text-align:center; font-weight:600; margin:1.1rem 0 .3rem 0;}

/* hand-off logo animation: the note travels from one hand to the other and back */
.logo {color:var(--text); overflow:visible;}
.note {animation:pass 4.2s ease-in-out infinite; transform-box:fill-box; transform-origin:center;}
.armA {animation:reachA 4.2s ease-in-out infinite;}
.armB {animation:reachB 4.2s ease-in-out infinite;}
@keyframes pass {
  0%, 12%   {transform:translate(0,0) rotate(0deg);}
  29%       {transform:translate(40px,-34px) rotate(10deg);}
  46%, 62%  {transform:translate(80px,0) rotate(0deg);}
  79%       {transform:translate(40px,-34px) rotate(-10deg);}
  96%, 100% {transform:translate(0,0) rotate(0deg);}
}
@keyframes reachA {0%,6% {transform:translateX(0);} 12% {transform:translateX(6px);} 20%,88% {transform:translateX(0);} 96% {transform:translateX(6px);} 100% {transform:translateX(0);}}
@keyframes reachB {0%,38% {transform:translateX(0);} 46% {transform:translateX(-6px);} 54% {transform:translateX(0);} 62% {transform:translateX(-6px);} 70%,100% {transform:translateX(0);}}

/* project page */
.member {display:inline-block; padding:2px 8px; border-radius:6px; background:var(--line); margin:2px; font-size:.8rem; font-weight:600;}
.sec {display:flex; align-items:center; gap:8px; font-weight:700; font-size:1rem; margin:1.1rem 0 .45rem 0;}
.sec svg {flex:none;}
.card {background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px 12px; margin:0 0 8px 0; font-size:.87rem; line-height:1.4;}
.card.mine {border:1.5px solid var(--text);}
.card .who {font-weight:700;} .card .meta {font-weight:600; font-size:.76rem; margin-left:6px;}
.card .lab {font-weight:700; display:block; margin-top:6px; font-size:.78rem;}
.dec {padding:6px 0; border-bottom:1px solid var(--line); font-size:.86rem; line-height:1.4;}
.dec:last-child {border-bottom:none;}
.dec .meta {font-weight:600; font-size:.74rem; margin-left:4px;}
.avatar {display:flex; justify-content:center; padding-top:2px;}
[class*="st-key-amsg"] h1, [class*="st-key-amsg"] h2 {font-size:1.25rem !important; font-weight:700; margin:.2rem 0 .6rem 0;}
[class*="st-key-amsg"] h3, [class*="st-key-amsg"] h4 {font-size:1.05rem !important; font-weight:700;}
[class*="st-key-amsg"] p, [class*="st-key-amsg"] li {font-size:.95rem; line-height:1.55;}
.umsg {margin:6px 0 14px auto; width:fit-content; max-width:85%; background:var(--card); border:1px solid var(--line);
       border-radius:14px 14px 4px 14px; padding:9px 14px; font-size:.95rem; font-weight:500; line-height:1.45;}
.umsg .uname {font-weight:700; font-size:.75rem; margin-bottom:2px;}
.typing span {display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--text); margin-right:5px; animation:dot 1.1s infinite ease-in-out;}
.typing span:nth-child(2) {animation-delay:.15s;} .typing span:nth-child(3) {animation-delay:.3s;}
@keyframes dot {0%,80%,100% {opacity:.25; transform:translateY(0);} 40% {opacity:1; transform:translateY(-4px);}}
.chip {max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; vertical-align:top; display:inline-block;padding:3px 9px; border:1px solid var(--line); border-radius:999px; font-size:.78rem; font-weight:600; margin:0 4px 4px 0;}
</style>""", unsafe_allow_html=True)
if ss.theme == "light":
    st.markdown("""
<style>
:root {
  --bg:var(--offwhite); --card:var(--sand); --text:var(--black);
  --line:rgba(0,0,0,.14); --btn-bg:var(--espresso); --btn-text:var(--offwhite);
  --note:var(--espresso); --note-line:var(--sand); --toggle:var(--espresso);
}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- graphics
# open hand (palm, four fingers, thumb) with a note that lifts off the fingertips and settles back
MINI_LOGO = """
<svg class="mini-logo" viewBox="0 -6 50 54" width="40" height="43" xmlns="http://www.w3.org/2000/svg">
  <g transform="rotate(35 23 30)" style="fill:currentColor">
    <rect x="12.5" y="14" width="4.6" height="17" rx="2.3"/>
    <rect x="18" y="11" width="4.6" height="19" rx="2.3"/>
    <rect x="23.5" y="12" width="4.6" height="18" rx="2.3"/>
    <rect x="29" y="16" width="4.6" height="14" rx="2.3"/>
    <path d="M18 36 L8.5 26.5" style="stroke:currentColor;stroke-width:5.2;stroke-linecap:round;fill:none"/>
    <rect x="12" y="25" width="22" height="16" rx="7"/>
    <rect x="15" y="36" width="16" height="10" rx="2"/>
  </g>
  <g class="fly"><g transform="rotate(18 33 7)">
    <rect x="26" y="-1" width="14" height="17" rx="2" style="fill:var(--note);stroke:var(--bg);stroke-width:1.2"/>
    <line x1="28.5" y1="3.5" x2="37.5" y2="3.5" style="stroke:var(--note-line);stroke-width:1.5"/>
    <line x1="28.5" y1="7" x2="37.5" y2="7" style="stroke:var(--note-line);stroke-width:1.5"/>
    <line x1="28.5" y1="10.5" x2="33.5" y2="10.5" style="stroke:var(--note-line);stroke-width:1.5"/>
  </g></g>
</svg>"""

LOGO = """
<svg class="logo" width="320" height="160" viewBox="0 0 320 160" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="60" cy="42" r="18"/>
    <path d="M22 150 Q22 82 60 82 Q98 82 98 150"/>
    <g class="armA"><path d="M84 96 Q100 114 116 104"/><circle cx="120" cy="102" r="5" style="fill:currentColor"/></g>
    <circle cx="260" cy="42" r="18"/>
    <path d="M222 150 Q222 82 260 82 Q298 82 298 150"/>
    <g class="armB"><path d="M236 96 Q220 114 204 104"/><circle cx="200" cy="102" r="5" style="fill:currentColor"/></g>
  </g>
  <g class="note">
    <rect x="109" y="70" width="22" height="28" rx="3" style="fill:var(--note)"/>
    <line x1="113" y1="78" x2="127" y2="78" style="stroke:var(--note-line);stroke-width:2"/>
    <line x1="113" y1="84" x2="127" y2="84" style="stroke:var(--note-line);stroke-width:2"/>
    <line x1="113" y1="90" x2="122" y2="90" style="stroke:var(--note-line);stroke-width:2"/>
  </g>
</svg>
"""

# simplified marks for each model family
MODEL_MARKS = {
    "Claude": '<g stroke="#D97757" stroke-width="2.6" stroke-linecap="round">'
              '<line x1="12" y1="2.5" x2="12" y2="21.5"/><line x1="2.5" y1="12" x2="21.5" y2="12"/>'
              '<line x1="5.3" y1="5.3" x2="18.7" y2="18.7"/><line x1="18.7" y1="5.3" x2="5.3" y2="18.7"/></g>',
    "GPT": '<g fill="none" stroke="currentColor" stroke-width="1.7">'
           '<rect x="8.2" y="2.5" width="7.6" height="19" rx="3.8"/>'
           '<rect x="8.2" y="2.5" width="7.6" height="19" rx="3.8" transform="rotate(60 12 12)"/>'
           '<rect x="8.2" y="2.5" width="7.6" height="19" rx="3.8" transform="rotate(120 12 12)"/></g>',
    "Gemini": '<defs><linearGradient id="gem" x1="0" y1="0" x2="1" y2="1">'
              '<stop offset="0" stop-color="#4285F4"/><stop offset="1" stop-color="#9B72CB"/></linearGradient></defs>'
              '<path fill="url(#gem)" d="M12 2C12.8 7.5 16.5 11.2 22 12C16.5 12.8 12.8 16.5 12 22C11.2 16.5 7.5 12.8 2 12C7.5 11.2 11.2 7.5 12 2Z"/>',
}

ICONS = {
    "files": '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5"/>',
    "status": '<path d="M5 21V4"/><path d="M5 4h11l-2 4 2 4H5"/>',
    "handoff": '<path d="M4 12h12"/><path d="M12 7l5 5-5 5"/><path d="M20 5v14"/>',
    "people": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M16 11h5M18.5 8.5v5"/>',
}


def model_mark(model, size=26):
    inner = next((v for k, v in MODEL_MARKS.items() if k in model), '<circle cx="12" cy="12" r="8" fill="currentColor"/>')
    return f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'


def sec(icon, title):
    st.markdown(f'<div class="sec"><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" '
                f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[icon]}</svg>'
                f'<span>{title}</span></div>', unsafe_allow_html=True)


def esc(text):
    return html.escape(text).replace("\n", "<br>")


def theme_toggle():
    """Top bar: logo + word go home, account menu (invites + sign out), theme circle."""
    st.markdown('<div class="topbar"></div><div class="bb-footer">Memory powered by '
                '<a href="https://backboard.io" target="_blank">Backboard.io</a></div>',
                unsafe_allow_html=True)
    signed_in = ss.email and ss.page in ("projects", "project")
    if ss.page != "landing":
        st.markdown(MINI_LOGO, unsafe_allow_html=True)
        if st.button("Handoff", key="home_btn", help="Your projects" if signed_in else "Back to start"):
            if signed_in:
                go("projects", pid=None)
            go("landing")
    if signed_in:
        invites = [(pid, p) for pid, p in db["projects"].items() if ss.email in p.get("invites", [])]
        label = f":material/account_circle: {me()}" + (f"  ·  {len(invites)} invite{'s' if len(invites) > 1 else ''}"
                                                        if invites else "")
        with st.container(key="acct"):
            with st.popover(label):
                st.markdown(f'<div style="font-size:.85rem">Signed in as <b>{esc(ss.email)}</b></div>',
                            unsafe_allow_html=True)
                if invites:
                    st.markdown("**Invites**")
                for pid, p in invites:
                    owner = db["users"].get(p["owner"], {}).get("name", p["owner"])
                    st.markdown(f"{p['name']}  \nfrom {owner}")
                    a, d = st.columns(2)
                    if a.button("Accept", key=f"acc_{pid}", type="primary", use_container_width=True):
                        p["invites"].remove(ss.email)
                        p["members"].append(ss.email)
                        save(db)
                        st.rerun()
                    if d.button("Decline", key=f"dec_{pid}", use_container_width=True):
                        p["invites"].remove(ss.email)
                        save(db)
                        st.rerun()
                if st.button("Sign out", key="signout", use_container_width=True):
                    go("landing", email=None, pid=None)
    if st.button(" ", key="theme_btn", help="Switch light / dark"):
        ss.theme = "light" if ss.theme == "dark" else "dark"
        st.rerun()


# ---------------------------------------------------------------- session notes
EMPTY = {"", "none", "n/a", "na", "-", "nothing", "none yet", "nothing yet"}
FIELDS = r"(?:DONE|DECIDED|IN PROGRESS|NEXT TASK|HANDOFFS)"
SUGGESTIONS = ["Catch me up since my last session", "What's waiting on me?", "Does my part match our decisions?"]


def parse_note(text):
    """Splits a 'DONE: / DECIDED: / IN PROGRESS: / NEXT TASK: / HANDOFFS:' note into a dict."""
    pat = rf"(DONE|DECIDED|IN PROGRESS|NEXT TASK|HANDOFFS)\s*:\s*(.*?)(?={FIELDS}\s*:|\Z)"
    return {k: v.strip(" \n-*.") for k, v in re.findall(pat, text, re.S)
            if v.strip(" \n-*.").lower() not in EMPTY and not v.strip(" \n-*.").lower().startswith("nothing")}


def note_time(n):
    try:
        return datetime.strptime(f'{datetime.now().year} {n.get("time", "")}', "%Y %b %d %H:%M")
    except ValueError:
        return datetime.min


def ago(n):
    t = note_time(n)
    secs = (datetime.now() - t).total_seconds() if t != datetime.min else -1
    if secs < 0:
        return n.get("time", "")
    if secs < 3600:
        return f"{max(1, int(secs // 60))} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    return f"{int(secs // 86400)} d ago"


def note_card(n, fields, label=None, mine=False):
    parts = parse_note(n["text"])
    meta = " · ".join(x for x in [n.get("model"), ago(n)] if x)
    body = "".join(f'<span class="lab">{f.capitalize()}</span>{esc(parts[f])}' for f in fields if parts.get(f))
    if not parts:
        body = esc(n["text"].split("\n", 1)[-1])
    return (f'<div class="card{" mine" if mine else ""}"><span class="who">{esc(label or n["author"])}</span>'
            f'<span class="meta">{esc(meta)}</span>{body}</div>')


def team_names(p):
    """Members plus invited teammates, so you can hand work to someone who hasn't joined yet."""
    return [db["users"].get(m, {}).get("name", m) for m in p["members"] + p.get("invites", [])]


def record_handoffs(p, text):
    """'@Kevin finish the discussion' in the chat hands that task to Kevin. Returns who got one."""
    names = {n.lower(): n for n in team_names(p) if n != me()}
    got = []
    for tag in re.findall(r"@(\w+)", text):
        name = names.get(tag.lower())
        if name and name not in got:
            got.append(name)
    if got:
        # keep only the sentence(s) that mention someone, without the @name itself
        picked = [s for s in re.split(r"(?<=[.!?])\s+", text) if "@" in s] or [text]
        task = re.sub(r"\s+", " ", re.sub(r"@\w+[,:]?", "", " ".join(picked))).strip(" ,:-") or text
        task = task[:1].upper() + task[1:]
        for name in got:
            p.setdefault("handoffs", []).append({
                "id": uuid.uuid4().hex[:8], "from": me(), "to": name, "task": task,
                "time": datetime.now().strftime("%b %d %H:%M"), "done": False})
        save(db)
    return got


# ---------------------------------------------------------------- demo switcher
def demo_switcher(where):
    users = list(db["users"].keys())[:6]
    if not users:
        return
    cols = st.columns(len(users))
    for col, e in zip(cols, users):
        name = db["users"][e]["name"]
        if col.button(name, key=f"sw_{where}_{e}", use_container_width=True, disabled=e == ss.email,
                      help="You're signed in as this teammate" if e == ss.email else f"Switch to {name}"):
            keep = ss.pid
            sign_in(e, name)
            p = db["projects"].get(keep)
            if p and e in p["members"]:
                open_project(keep)
            go("projects")


# ---------------------------------------------------------------- pages
def landing():
    theme_toggle()
    st.markdown(f'<div class="hero hero-center">{LOGO}<h1>Handoff</h1>'
                '<p class="tag">One project memory. Any teammate. Any model.</p></div>',
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1.4, 1, 1.4])
    if mid.button("Start", type="primary", use_container_width=True):
        go("login")


def _enter_demo(email, name):
    for e, n in DEMO_USERS.items():
        db["users"].setdefault(e, {"name": n})
    save(db)
    sign_in(email, name)
    go("projects")


def login_page():
    """Demo login: any email and password works, nothing is checked."""
    theme_toggle()
    st.markdown(f'<div class="hero">{LOGO}<h2>Welcome to Handoff</h2></div>', unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        with st.container(key="democard"):
            st.markdown("**Try the demo**")
            st.caption("Jump into a ready-made team project and switch between teammates anytime.")
            cols = st.columns(len(DEMO_USERS))
            for col, (e, n) in zip(cols, DEMO_USERS.items()):
                if col.button(n, key=f"demo_{e}", type="primary", use_container_width=True):
                    _enter_demo(e, n)

        st.markdown('<p class="or">or use any email</p>', unsafe_allow_html=True)
        tab_in, tab_up = st.tabs(["Log in", "Sign up"])
        with tab_in:
            with st.form("login", enter_to_submit=False):
                email = st.text_input("Email")
                st.text_input("Password", type="password")
                if st.form_submit_button("Log in", type="primary", use_container_width=True):
                    e = email.strip().lower()
                    if "@" not in e:
                        st.error("Enter an email address.")
                    else:
                        u = db["users"].get(e)
                        sign_in(e, u["name"] if u else e.split("@")[0].capitalize())
                        go("projects")
        with tab_up:
            with st.form("signup", enter_to_submit=False):
                name = st.text_input("Full name")
                email2 = st.text_input("Email ")
                st.text_input("Password ", type="password")
                if st.form_submit_button("Create account", type="primary", use_container_width=True):
                    e = email2.strip().lower()
                    if "@" not in e:
                        st.error("Enter an email address.")
                    else:
                        db["users"][e] = {"name": name.strip() or e.split("@")[0].capitalize()}
                        save(db)
                        sign_in(e, db["users"][e]["name"])
                        go("projects")
        st.caption("Demo build: any email and password works.")
        if st.button("Back", use_container_width=True):
            go("landing")


def projects_page():
    theme_toggle()
    st.markdown(f"## Hi {me()}")
    st.markdown("### Your projects")
    mine = [(pid, p) for pid, p in db["projects"].items() if ss.email in p["members"]]
    if not mine:
        st.caption("No projects yet. Create one below, or accept an invite from the menu under your name.")
    cols = st.columns(3)
    for i, (pid, p) in enumerate(mine):
        with cols[i % 3].container(key=f"pcard_{pid}"):
            st.markdown(f"#### {p['name']}")
            st.markdown(" ".join(f'<span class="member">{esc(db["users"].get(m, {}).get("name", m))}</span>'
                                 for m in p["members"]), unsafe_allow_html=True)
            st.caption(f"Created {p['created']}")
            if st.button("Open", key=f"open_{pid}", type="primary", use_container_width=True):
                open_project(pid)

    with st.expander("+  New project"):
        with st.form("newproj", clear_on_submit=True, enter_to_submit=False):
            name = st.text_input("Project name", placeholder="e.g. Campus Coffee Cart Pitch")
            if st.form_submit_button("Create", type="primary") and name.strip():
                pid = uuid.uuid4().hex[:8]
                with st.spinner("Setting up the project memory on Backboard..."):
                    aid = str(hb.get_or_create_project(f"{name.strip()} [{pid}]"))
                db["projects"][pid] = {
                    "name": name.strip(), "assistant_id": aid, "owner": ss.email,
                    "members": [ss.email], "invites": [],
                    "created": datetime.now().strftime("%b %d, %H:%M"),
                }
                save(db)
                st.rerun()

    st.divider()
    sec("people", "Demo: switch teammate")
    demo_switcher("projects")


def render_msg(m, i):
    """AI replies keep the mark of the model that actually wrote them."""
    if m["role"] == "assistant":
        a, b = st.container(key=f"amsg_{i}").columns([1, 16], gap="small")
        a.markdown(f'<div class="avatar" title="{esc(m["model"])}">{model_mark(m["model"])}</div>',
                   unsafe_allow_html=True)
        b.markdown(m["text"])
    else:
        st.markdown(f'<div class="umsg"><div class="uname">{esc(m["who"])}</div>{esc(m["text"])}</div>',
                    unsafe_allow_html=True)


def typing(slot, model):
    with slot.container():
        a, b = st.columns([1, 16], gap="small")
        a.markdown(f'<div class="avatar">{model_mark(model)}</div>', unsafe_allow_html=True)
        b.markdown('<div class="typing"><span></span><span></span><span></span></div>', unsafe_allow_html=True)


def side_panel(p, aid, notes, facts):
    """Each section answers one different question:
    Where things stand = now / next, Handoffs = tasks sent with @name,
    History = what got done (+ raw Backboard memory)."""
    # files: always-open drop zone, uploads as soon as a file is dropped
    sec("files", "Files")
    ups = st.file_uploader("Drop files here", type=["pdf", "docx", "txt", "md", "pptx"],
                           accept_multiple_files=True, label_visibility="collapsed", key=f"up_{ss.pid}")
    for up in ups or []:
        sig = f"{ss.pid}:{up.name}:{up.size}"
        if sig in ss.uploaded:
            continue
        ss.uploaded.add(sig)
        path = os.path.join(tempfile.gettempdir(), up.name)
        with open(path, "wb") as f:
            f.write(up.getbuffer())
        with st.spinner(f"Reading {up.name}..."):
            try:
                status = hb.upload_draft(aid, path)
            except Exception:
                status = "error"
        if status == "error":
            st.error(f"Couldn't add {up.name}.")
        else:
            p.setdefault("docs", []).append({"name": up.name, "by": me()})
            save(db)
    if p.get("docs"):
        st.markdown("".join(f'<span class="chip">{esc(d["name"])} · {esc(d["by"])}</span>' for d in p["docs"]),
                    unsafe_allow_html=True)

    # handoffs: tasks teammates sent each other by typing @Name in the chat
    hand = [h for h in p.get("handoffs", []) if not h.get("done")]
    to_me = [h for h in hand if h["to"] == me()]
    by_me = [h for h in hand if h["from"] == me()]
    # a fold-out list that opens by itself when something is waiting on you
    with st.expander(f"Handoffs{f'  ·  {len(to_me)} for you' if to_me else ''}", expanded=bool(to_me)):
        if to_me:
            st.markdown('<div class="grp">Waiting on you</div>', unsafe_allow_html=True)
            for h in to_me:
                st.markdown(f'<div class="card">{esc(h["task"])}<span class="meta">· from {esc(h["from"])}, {esc(h["time"])}</span></div>',
                            unsafe_allow_html=True)
                if st.button("Mark done", key=f"hd_{h['id']}", type="primary", use_container_width=True,
                             icon=":material/check:"):
                    h["done"] = True
                    save(db)
                    st.rerun()
        if by_me:
            st.markdown('<div class="grp">You handed off</div>' + "".join(
                f'<div class="card">{esc(h["task"])}<span class="meta">· to {esc(h["to"])}, {esc(h["time"])}</span></div>'
                for h in by_me), unsafe_allow_html=True)
        if not to_me and not by_me:
            others = [n for n in team_names(p) if n != me()]
            example = others[0] if others else "Name"
            st.caption(f"Nothing for you right now. To hand a task to a teammate, type it in the chat with @, "
                       f"like \"@{example} finish the discussion section\".")

    # where things stand: each teammate's latest note, you first
    sec("status", "Where things stand")
    latest = {}
    for n in notes:
        latest[n["author"]] = n
    order = sorted(latest.values(), key=lambda n: (n["author"] != me(), -note_time(n).timestamp()
                                                   if note_time(n) != datetime.min else 0))
    if order:
        st.markdown("".join(note_card(n, ["IN PROGRESS", "NEXT TASK"],
                                      label="You" if n["author"] == me() else None, mine=n["author"] == me())
                            for n in order), unsafe_allow_html=True)
    else:
        st.caption("Nothing yet. A card appears here when someone ends a session.")

    # history: what each session finished, plus the raw memory behind it
    with st.expander(f"History ({len(notes)} session{'' if len(notes) == 1 else 's'})"):
        people = sorted({n["author"] for n in notes})
        who = st.selectbox("Show work by", ["Everyone"] + people, key="who_filter")
        for n in reversed(notes):
            if who != "Everyone" and n["author"] != who:
                continue
            st.markdown(note_card(n, ["DONE"]), unsafe_allow_html=True)
            if st.button("Remove", key=f"dn_{n['id']}", help="Remove this session from the project memory"):
                if "notes" in p:
                    p["notes"] = [x for x in p["notes"] if x["id"] != n["id"]]
                    save(db)
                try:
                    hb.delete_memory(aid, n["id"])
                except Exception:
                    pass  # already gone from Backboard (or merged away by its auto-memory)
                memory.clear()
                st.rerun()
        if not notes:
            st.caption("No sessions saved yet.")

        show = ss.get("show_mem", False)
        if st.button(("Hide" if show else "Open") + f" Backboard memory ({len(facts)} facts)", key="mem_btn",
                     icon=":material/memory:", type="primary", use_container_width=True):
            ss.show_mem = not show
            st.rerun()
        if show:
            st.caption("Facts Backboard picked up from everyone's chats. Remove anything wrong or outdated.")
            for fid, text in facts:
                a, b = st.columns([9, 1])
                a.markdown(f'<div style="font-size:.86rem">{esc(text)}</div>', unsafe_allow_html=True)
                if b.button("×", key=f"df_{fid}", help="Forget this"):
                    hb.delete_memory(aid, fid)
                    memory.clear()
                    st.rerun()
            if facts or notes:
                sure = st.checkbox("I understand this erases everything the project remembers")
                if st.button("Clear all project memory", disabled=not sure):
                    hb.reset_memories(aid)
                    memory.clear()
                    st.rerun()

    sec("people", "Demo: switch teammate")
    demo_switcher("project")


def project_page(prompt):
    p = db["projects"].get(ss.pid)
    if not p or ss.email not in p["members"]:
        go("projects")
    aid = p["assistant_id"]

    theme_toggle()
    top_l, top_r = st.columns([3, 2])
    with top_l:
        if st.button("← All projects"):
            go("projects", pid=None)
        st.markdown(f"## {p['name']}")
        st.markdown("Team: " + " ".join(
            f'<span class="member">{esc(db["users"].get(m, {}).get("name", m))}</span>' for m in p["members"])
            + ("  ·  invited: " + ", ".join(esc(db["users"].get(e, {}).get("name", e)).replace("@", "&#8203;@")
                                           for e in p["invites"]) if p["invites"] else ""),
            unsafe_allow_html=True)
    with top_r:
        c1, c2 = st.columns(2)
        with c1.popover("Invite teammate", use_container_width=True):
            with st.form("invite", clear_on_submit=True, enter_to_submit=False):
                em = st.text_input("Teammate's email")
                if st.form_submit_button("Send invite", type="primary", use_container_width=True):
                    em = em.strip().lower()
                    if "@" in em and em not in p["members"] and em not in p["invites"]:
                        p["invites"].append(em)
                        save(db)
                        st.rerun()
        if c2.button("End session", use_container_width=True, disabled=not ss.get("dirty"),
                     help="Save a session note for your team and leave"):
            go("projects", pid=None)
        model = st.selectbox("Your AI model", list(hb.MODELS.keys()), key="model")

    if prompt:
        ss.messages.append({"role": "user", "who": me(), "text": prompt})
        ss.dirty = True
        got = record_handoffs(p, prompt)
        if got:
            st.toast(f"Handed off to {', '.join(got)}. They'll see it when they open the project.")

    try:
        bb_notes, facts = memory(aid)
    except Exception:
        bb_notes, facts = [], []
    # the app's own copy of session notes wins; older projects fall back to what Backboard has
    notes = sorted(p["notes"] if "notes" in p else bb_notes, key=note_time)

    chat_col, side = st.columns([2, 1], gap="large")
    with chat_col:
        if not ss.messages:
            # instant welcome instead of an AI recap: the sidebar already shows the status
            waiting = [h for h in p.get("handoffs", []) if h["to"] == me() and not h.get("done")]
            heads_up = (f' <b>{esc(waiting[0]["from"])}</b> handed you a task: "{esc(waiting[0]["task"])}".'
                        + (f" ({len(waiting) - 1} more in Handoffs.)" if len(waiting) > 1 else "")) if waiting else ""
            st.markdown(f'<div class="welcome"><b>Hi {esc(me())}.</b>{heads_up} Every model you pick here reads the '
                        'same project memory: your team\'s notes and files. Type <b>@name</b> to hand a teammate a '
                        'task. Ask anything, or start with:</div>', unsafe_allow_html=True)
            for i, s in enumerate(SUGGESTIONS):
                if st.button(s, key=f"sugg_{i}"):
                    ss.queued = s
                    st.rerun()
        for i, m in enumerate(ss.messages):
            render_msg(m, i)
        slot = st.empty()
    with side:
        side_panel(p, aid, notes, facts)

    # the slow Backboard call runs last, so the whole page is already on screen
    if prompt:
        typing(slot, model)
        try:
            reply, ss.thread_id = hb.chat(aid, ss.thread_id, me(), model, prompt)
        except Exception as e:
            print(f"[handoff] chat failed: {type(e).__name__}: {e}", flush=True)
            reply = "_No reply came back in time. Try sending that again._"
        ss.messages.append({"role": "assistant", "who": model, "model": model, "text": reply})
        memory.clear()
        st.rerun()


# ---------------------------------------------------------------- router
if ss.get("flash"):
    st.toast(ss.pop("flash"))
# each page lives in its own keyed container, so switching pages clears the old one at once
# instead of leaving it faded on screen while a slow Backboard call runs.
# The chat box stays outside it so Streamlit keeps it pinned to the bottom.
on_project = ss.page == "project" and ss.pid and ss.email
prompt = None
if on_project:
    prompt = st.chat_input(f"Message as {me()} via {ss.get('model') or list(hb.MODELS)[0]}") or ss.pop("queued", None)
with st.container(key=f"page_{ss.page}_{ss.pid or ''}_{ss.email or ''}"):
    if ss.page == "landing":
        landing()
    elif ss.page == "login" or not ss.email:
        login_page()
    elif on_project:
        project_page(prompt)
    else:
        projects_page()
