import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime

import streamlit as st

import handoff as hb

# faster models for live demos (reasoning models can time out)
hb.MODELS.pop("GPT-5 mini", None)
hb.MODELS.setdefault("GPT-4.1 mini", ("openai", "gpt-4.1-mini"))

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
ss.setdefault("briefed", False)


def me():
    return db["users"].get(ss.email, {}).get("name", "?")


def auto_save():
    """Writes a session note automatically when someone leaves a project they worked in."""
    if ss.get("page") == "project" and ss.get("dirty") and ss.get("thread_id") and ss.get("pid"):
        p = db["projects"].get(ss.pid)
        if p:
            try:
                hb.end_session(p["assistant_id"], ss.thread_id, me(), ss.get("model") or list(hb.MODELS)[0])
                st.toast("Your session was saved to the project memory.")
            except Exception:
                pass
    ss.dirty = False


def go(page, **kw):
    if page != "project":
        auto_save()
    ss.page = page
    for k, v in kw.items():
        ss[k] = v
    st.rerun()


def open_project(pid):
    ss.pid, ss.thread_id, ss.messages, ss.briefed = pid, None, [], False
    go("project")


def sign_in(email, name):
    auto_save()
    email = email.strip().lower()
    db["users"].setdefault(email, {"name": name.strip() or email.split("@")[0]})
    save(db)
    ss.email = email
    ss.pid, ss.thread_id, ss.messages, ss.briefed = None, None, [], False


# ---------------------------------------------------------------- styling
st.markdown(
    """
<style>
.block-container {padding-top: 2rem;}
.hero {text-align:center; margin-top: 2rem;}
.hero h1 {font-size: 3.2rem; margin: .5rem 0 0 0; letter-spacing: -1px;}
.hero p {opacity: .7; font-size: 1.15rem;}
.badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem;
        font-weight:600; margin-right:6px;}
.member {display:inline-block; padding:2px 8px; border-radius:6px; background:rgba(127,127,127,.15);
         margin:2px; font-size:.8rem;}
@keyframes pass {
  0%   { transform: translateX(0px)   translateY(0px); }
  25%  { transform: translateX(55px)  translateY(-28px); }
  50%  { transform: translateX(110px) translateY(0px); }
  75%  { transform: translateX(55px)  translateY(-28px); }
  100% { transform: translateX(0px)   translateY(0px); }
}
@keyframes glowA { 0%,100% {opacity:1;} 50% {opacity:.35;} }
@keyframes glowB { 0%,100% {opacity:.35;} 50% {opacity:1;} }
.baton {animation: pass 3s ease-in-out infinite;}
.pA {animation: glowA 3s ease-in-out infinite;}
.pB {animation: glowB 3s ease-in-out infinite;}
</style>
""",
    unsafe_allow_html=True,
)

ss.setdefault("theme", "dark")
st.markdown("""
<style>
[data-testid="stToolbar"], [data-testid="stMainMenu"], [data-testid="stDeployButton"],
[data-testid="stAppDeployButton"], #MainMenu {display:none !important;}
header[data-testid="stHeader"] {background: transparent;}
.hero-center {padding-top: 16vh; margin-bottom: 1rem;}
[data-testid="stHeaderActionElements"], .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a,
.stMarkdown h4 a, [data-testid="stHeadingWithActionElements"] a {display:none !important;}
.st-key-home_btn {position: fixed; top: .9rem; left: 1.4rem; z-index: 999999; width: auto !important;}
.st-key-home_btn button {border: none; background: transparent; font-weight: 700; font-size: 1.05rem;}
.block-container {padding-top: 3.5rem !important;}
.st-key-theme_btn {position: fixed; top: .9rem; right: 1.4rem; z-index: 999999; width: auto !important;}
.stApp button[kind="primary"], .stApp button[kind="primaryFormSubmit"] {
  background: #5AA9F0 !important; border-color: #5AA9F0 !important; color: #fff !important;}
.stApp button[kind="primary"]:hover, .stApp button[kind="primaryFormSubmit"]:hover {
  background: #3E93E0 !important; border-color: #3E93E0 !important;}
.stTabs [data-baseweb="tab-highlight"] {background-color: #5AA9F0 !important;}
.stTabs [aria-selected="true"] p {color: #5AA9F0 !important;}
.bb-footer {position: fixed; bottom: .4rem; left: 1rem; font-size: .75rem; opacity: .55; z-index: 1000;}
.bb-footer a {color: inherit;}
.typing {opacity:.6; letter-spacing: 3px; animation: glowA 1.2s ease-in-out infinite;}
</style>""", unsafe_allow_html=True)
if ss.theme == "light":
    st.markdown("""
<style>
.stApp, header[data-testid="stHeader"] {background:#FAF8F5 !important;}
.stApp, .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp li, .stApp small, .stApp div {color:#1a1a1a;}
.stApp input, .stApp textarea, [data-baseweb="select"] > div, [data-baseweb="input"] {
  background:#fff !important; color:#1a1a1a !important;}
[data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] details {
  background:#fff; border-color:#e5e0d8 !important;}
.stApp button[kind="secondary"] {background:#fff; color:#1a1a1a; border-color:#d9d3c8;}
[data-testid="stChatInput"] {background:#fff !important;}
</style>""", unsafe_allow_html=True)


def theme_toggle():
    icon = "☀️" if ss.theme == "dark" else "🌙"
    st.markdown('<div class="bb-footer">Memory powered by '
                '<a href="https://backboard.io" target="_blank">Backboard.io</a></div>',
                unsafe_allow_html=True)
    if ss.page != "landing" and st.button("🤝 Handoff", key="home_btn", help="Back to start"):
        go("landing")
    if st.button(icon, key="theme_btn", help="Switch light / dark"):
        ss.theme = "light" if ss.theme == "dark" else "dark"
        st.rerun()

MODEL_ICONS = {"Claude": "✳", "GPT": "◎", "Gemini": "✦"}


def model_label(m):
    return f'{next((i for k, i in MODEL_ICONS.items() if k in m), "•")}  {m}'


MODEL_COLORS = {
    "Claude": "#D97757",
    "GPT": "#10A37F",
    "Gemini": "#4285F4",
}


def badge(model):
    color = next((c for k, c in MODEL_COLORS.items() if k in model), "#888")
    return f'<span class="badge" style="background:{color}22;color:{color};border:1px solid {color}">{model_label(model)}</span>'


LOGO = """
<svg width="200" height="110" viewBox="0 0 200 110" xmlns="http://www.w3.org/2000/svg">
  <g class="pA" fill="none" stroke="currentColor" stroke-width="4">
    <circle cx="35" cy="30" r="14"/><path d="M12 95 Q35 50 58 95"/>
  </g>
  <g class="pB" fill="none" stroke="currentColor" stroke-width="4">
    <circle cx="165" cy="30" r="14"/><path d="M142 95 Q165 50 188 95"/>
  </g>
  <g class="baton">
    <rect x="35" y="55" width="22" height="28" rx="3" fill="#E8A33D"/>
    <line x1="40" y1="63" x2="52" y2="63" stroke="#1a1a1a" stroke-width="2"/>
    <line x1="40" y1="69" x2="52" y2="69" stroke="#1a1a1a" stroke-width="2"/>
    <line x1="40" y1="75" x2="48" y2="75" stroke="#1a1a1a" stroke-width="2"/>
  </g>
</svg>
"""


# ---------------------------------------------------------------- demo bar
def demo_bar():
    st.divider()
    with st.expander("🎬 Demo mode: switch accounts"):
        st.caption("Jump between teammates to show the same project from different accounts.")
        if st.button("Create demo accounts (Ibrahim, Sarah, Kevin)"):
            for e, n in DEMO_USERS.items():
                db["users"].setdefault(e, {"name": n})
            save(db)
            st.rerun()
        users = list(db["users"].keys())
        if users:
            cols = st.columns(len(users[:6]))
            for col, e in zip(cols, users[:6]):
                label = db["users"][e]["name"] + (" (you)" if e == ss.email else "")
                if col.button(label, key=f"sw_{e}", use_container_width=True, disabled=e == ss.email):
                    keep = ss.pid
                    sign_in(e, db["users"][e]["name"])
                    p = db["projects"].get(keep)
                    if p and e in p["members"]:
                        open_project(keep)
                    go("projects")


# ---------------------------------------------------------------- pages
def landing():
    theme_toggle()
    st.markdown(f'<div class="hero hero-center">{LOGO}<h1>Handoff</h1>'
                "<p>One project memory. Any teammate. Any model.</p></div>",
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1.3, 1, 1.3])
    if mid.button("Start", type="primary", use_container_width=True):
        go("login")


def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def login_page():
    theme_toggle()
    st.markdown(f'<div class="hero" style="margin-top:0">{LOGO}<h2>Welcome to Handoff</h2></div>',
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        tab_in, tab_up = st.tabs(["Log in", "Sign up"])
        with tab_in:
            with st.form("login"):
                email = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Log in", type="primary", use_container_width=True):
                    u = db["users"].get(email.strip().lower())
                    if not u or u.get("pw") != _hash(pw):
                        st.error("Wrong email or password.")
                    else:
                        sign_in(email, u["name"])
                        go("projects")
        with tab_up:
            with st.form("signup"):
                name = st.text_input("Full name")
                email2 = st.text_input("Email ")
                pw1 = st.text_input("Create password", type="password")
                pw2 = st.text_input("Confirm password", type="password")
                if st.form_submit_button("Create account", type="primary", use_container_width=True):
                    e = email2.strip().lower()
                    if not name.strip() or "@" not in e:
                        st.error("Enter your name and a valid email.")
                    elif len(pw1) < 6 or pw1 != pw2:
                        st.error("Passwords must match and be at least 6 characters.")
                    elif db["users"].get(e, {}).get("pw"):
                        st.error("An account with this email already exists. Log in instead.")
                    else:
                        db["users"][e] = {"name": name.strip(), "pw": _hash(pw1)}
                        save(db)
                        sign_in(e, name)
                        go("projects")
        st.markdown('<p style="text-align:center;opacity:.6">or</p>', unsafe_allow_html=True)
        if st.button("Continue with Google", use_container_width=True):
            st.info("Google sign-in is coming soon. Use email for now.")
        if st.button("← Back", use_container_width=True):
            go("landing")

    st.divider()
    st.markdown('<p style="text-align:center;opacity:.7">🎬 Demo: jump straight into an account</p>',
                unsafe_allow_html=True)
    _, dm, _ = st.columns([1, 1.6, 1])
    cols = dm.columns(len(DEMO_USERS))
    for col, (e, n) in zip(cols, DEMO_USERS.items()):
        if col.button(n, key=f"demo_{e}", use_container_width=True):
            for e2, n2 in DEMO_USERS.items():
                db["users"].setdefault(e2, {"name": n2})
            save(db)
            sign_in(e, n)
            go("projects")


def projects_page():
    my_invites = [(pid, p) for pid, p in db["projects"].items() if ss.email in p.get("invites", [])]

    theme_toggle()
    left, right = st.columns([4, 1.4])
    left.markdown(f"## 👋 Hi {me()}")
    left.caption(f"Signed in as {ss.email}")
    with right:
        with st.popover(f"🔔 Invites ({len(my_invites)})", use_container_width=True):
            if not my_invites:
                st.caption("No pending invites.")
            for pid, p in my_invites:
                st.markdown(f"**{p['name']}**  \nfrom {db['users'].get(p['owner'], {}).get('name', p['owner'])}")
                a, d = st.columns(2)
                if a.button("Accept", key=f"acc_{pid}", type="primary"):
                    p["invites"].remove(ss.email)
                    p["members"].append(ss.email)
                    save(db)
                    st.rerun()
                if d.button("Decline", key=f"dec_{pid}"):
                    p["invites"].remove(ss.email)
                    save(db)
                    st.rerun()
        if st.button("Sign out", use_container_width=True):
            ss.email = None
            go("landing")

    st.markdown("### Your projects")
    mine = [(pid, p) for pid, p in db["projects"].items() if ss.email in p["members"]]
    if not mine:
        st.info("No projects yet. Create one below, or accept an invite.")
    cols = st.columns(3)
    for i, (pid, p) in enumerate(mine):
        with cols[i % 3].container(border=True):
            st.markdown(f"#### {p['name']}")
            st.markdown(" ".join(f'<span class="member">{db["users"].get(m, {}).get("name", m)}</span>'
                                 for m in p["members"]), unsafe_allow_html=True)
            st.caption(f"Created {p['created']}")
            if st.button("Open", key=f"open_{pid}", type="primary", use_container_width=True):
                open_project(pid)

    with st.expander("➕ New project"):
        with st.form("newproj", clear_on_submit=True):
            name = st.text_input("Project name", placeholder="e.g. MECHTRON Lab 3 Report")
            if st.form_submit_button("Create", type="primary") and name.strip():
                pid = uuid.uuid4().hex[:8]
                with st.spinner("Creating project brain on Backboard..."):
                    aid = str(hb.get_or_create_project(f"{name.strip()} [{pid}]"))
                db["projects"][pid] = {
                    "name": name.strip(), "assistant_id": aid, "owner": ss.email,
                    "members": [ss.email], "invites": [],
                    "created": datetime.now().strftime("%b %d, %H:%M"),
                }
                save(db)
                st.rerun()
    demo_bar()


def project_page():
    p = db["projects"].get(ss.pid)
    if not p or ss.email not in p["members"]:
        go("projects")
    aid = p["assistant_id"]

    theme_toggle()
    # --- top bar
    top_l, top_r = st.columns([4, 1.6])
    with top_l:
        if st.button("← All projects"):
            go("projects", pid=None)
        st.markdown(f"## {p['name']}")
        st.markdown("Team: " + " ".join(
            f'<span class="member">{db["users"].get(m, {}).get("name", m)}</span>' for m in p["members"])
            + (f"  ·  pending: {', '.join(p['invites'])}" if p["invites"] else ""),
            unsafe_allow_html=True)
    with top_r:
        with st.popover("➕ Invite teammate", use_container_width=True):
            with st.form("invite", clear_on_submit=True):
                em = st.text_input("Teammate's email")
                if st.form_submit_button("Send invite", type="primary"):
                    em = em.strip().lower()
                    if "@" in em and em not in p["members"] and em not in p["invites"]:
                        p["invites"].append(em)
                        save(db)
                        st.success(f"Invite sent to {em}")
                        st.rerun()
        model = st.selectbox("Your AI model", list(hb.MODELS.keys()), key="model", format_func=model_label)

    # --- auto status briefing on entry
    if not ss.briefed:
        ph = st.empty()
        ph.markdown('<p class="typing">● ● ●</p>', unsafe_allow_html=True)
        ss.thread_id, brief = hb.catch_up(aid, me(), model)
        ph.empty()
        ss.messages = [{"role": "assistant", "who": f"{model} · project status", "model": model, "text": brief}]
        ss.briefed = True

    chat_col, mem_col = st.columns([2, 1])

    with chat_col:
        for m in ss.messages:
            with st.chat_message(m["role"]):
                if m["role"] == "assistant":
                    st.markdown(badge(m["model"]) + f'<small>{m["who"]}</small>', unsafe_allow_html=True)
                else:
                    st.caption(m["who"])
                st.markdown(m["text"])


    with mem_col:
        with st.expander("📎 Add a document (draft, notes, slides)"):
            up = st.file_uploader("File", type=["pdf", "docx", "txt", "md", "pptx"], label_visibility="collapsed")
            if up and st.button("Share with project", type="primary"):
                path = os.path.join(tempfile.gettempdir(), up.name)
                with open(path, "wb") as f:
                    f.write(up.getbuffer())
                with st.spinner("Indexing document..."):
                    status = hb.upload_draft(aid, path)
                p.setdefault("docs", []).append({"name": up.name, "by": me()})
                save(db)
                st.success(f"{up.name}: {status}")
        if p.get("docs"):
            st.caption("Shared files: " + ", ".join(f'{d["name"]} ({d["by"]})' for d in p["docs"]))
        st.markdown("### 🧠 Project memory")
        st.caption("Powered by [Backboard.io](https://backboard.io)")
        notes, facts = hb.get_memory(aid)
        st.markdown("**Timeline**")
        people = sorted({n["author"] for n in notes})
        who = st.selectbox("Show work by", ["Everyone"] + people)
        shown = [n for n in notes if who == "Everyone" or n["author"] == who]
        for n in reversed(shown):
            st.info(n["text"])
        if not notes:
            st.caption("No sessions saved yet.")
        st.markdown("**What the project knows**")
        for f in facts:
            st.markdown(f"- {f}")
        if not facts:
            st.caption("Memories appear as you work.")

    if prompt := st.chat_input(f"Message as {me()} via {model}"):
        ss.messages.append({"role": "user", "who": me(), "text": prompt})
        ss.dirty = True
        with st.spinner(f"{model} is thinking..."):
            try:
                reply, ss.thread_id = hb.chat(aid, ss.thread_id, me(), model, prompt)
            except Exception:
                reply = "_That took longer than usual. Your message was saved to the project memory; send it again if you need a reply._"
        ss.messages.append({"role": "assistant", "who": model, "model": model, "text": reply})
        st.rerun()

    st.divider()
    with st.expander("⚙️ Manage project memory"):
        if st.button("🔄 Refresh memory"):
            st.rerun()
        items = hb.list_memories(aid)
        if not items:
            st.caption("Nothing stored yet.")
        for mid, content in items:
            a, b = st.columns([12, 1])
            a.markdown(f"<small>{content}</small>", unsafe_allow_html=True)
            if b.button("🗑", key=f"del_{mid}", help="Delete this memory"):
                hb.delete_memory(aid, mid)
                st.rerun()
        if items:
            sure = st.checkbox("I understand this erases everything the project remembers")
            if st.button("Clear all project memory", disabled=not sure):
                hb.reset_memories(aid)
                st.rerun()

    demo_bar()


# ---------------------------------------------------------------- router
if ss.page == "landing":
    landing()
elif ss.page == "login" or not ss.email:
    login_page()
elif ss.page == "project" and ss.pid:
    project_page()
else:
    projects_page()
