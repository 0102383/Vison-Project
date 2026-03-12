import streamlit as st
import sqlite3, base64, os, time, uuid, datetime
import streamlit.components.v1 as components
from fpdf import FPDF
from groq import Groq

# --- PART 1: SETTINGS & TOOLS ---
LOGO, AVATAR, ADMIN = "vison_logo.jpg", "ai_logo_glow.jpg", "0102383"

FORMULA_LIB = {
    "Quadratic": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
    "Schrödinger": r"i\hbar \frac{\partial}{\partial t} \Psi(\mathbf{r},t) = \hat{H} \Psi(\mathbf{r},t)",
    "Mass-Energy": r"E = mc^2",
    "Entropy": r"S = k \ln \Omega"
}

def get_64(p):
    if os.path.exists(p):
        with open(p, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# --- PART 2: DATABASE ---
def db_q(q, d=(), fetch=False):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    try:
        c.execute(q, d); res = c.fetchall() if fetch else None
        conn.commit(); return res
    finally: conn.close()

def init_db():
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT, mood_emoji TEXT DEFAULT '💬')''')

# --- PART 3: MOOD RING COLOR LOGIC ---
def get_mood_color(emoji):
    mood_map = {"🧠": "#00d4ff", "⚠️": "#ff4b4b", "🔥": "#ffaa00", "✅": "#00ff88", "💬": "#a252ff"}
    return mood_map.get(emoji, "#a252ff")

# --- PART 4: ANALYZER ---
def analyze_all(u, sid):
    logs = db_q('SELECT role, content FROM chat_log WHERE username=? AND session_id=? ORDER BY id DESC LIMIT 15', (u, sid), True)
    if not logs: return "Incomplete Data", 0, "💬"
    h = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        evo = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Summarize mental blocks: {h}"}])
        pwr = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Power 0-100 (num only): {h}"}])
        mood = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Pick 1 emoji (🧠,⚠️,🔥,✅,💬) for mood: {h}"}])
        e, p, m = evo.choices[0].message.content, int(''.join(filter(str.isdigit, pwr.choices[0].message.content))), mood.choices[0].message.content.strip()[0]
        db_q('UPDATE chat_sessions SET mood_emoji=? WHERE session_id=?', (m, sid))
        db_q('UPDATE users SET secret_profile=? WHERE username=?', (e, u))
        return e, p, m
    except: return "Engine Busy", 10, "⏳"

# --- PART 5: MAIN UI & CSS ---
st.set_page_config(page_title="VISON AI CORE", layout="wide")
init_db()

# Persistent Mood Style
current_mood = "💬"
if 'sid' in st.session_state:
    res = db_q('SELECT mood_emoji FROM chat_sessions WHERE session_id=?', (st.session_state.sid,), True)
    if res: current_mood = res[0][0]
mood_color = get_mood_color(current_mood)

st.markdown(f"""
    <style>
    .mood-ring {{ height: 5px; width: 100%; background: linear-gradient(90deg, transparent, {mood_color}, transparent); box-shadow: 0px 5px 15px {mood_color}; margin-bottom: 20px; }}
    .main-title {{ font-size: 50px !important; font-weight: 800; background: linear-gradient({mood_color}, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }}
    /* Chat Bubble Alignment */
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) {{ flex-direction: row-reverse !important; }}
    </style>
    <div class="mood-ring"></div>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    logo = get_64(LOGO)
    if logo: st.markdown(f'<center><img src="data:image/jpeg;base64,{logo}" width="150"></center>', unsafe_allow_html=True)
    u, p = st.text_input("User ID"), st.text_input("Key", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_q('INSERT INTO users (username, password, interests, level) VALUES (?,?,?,?)', (u.lower(), p, "STEM", "HS"))
        if not res or res[0][0] == p: st.session_state.logged_in, st.session_state.username = True, u.lower(); st.rerun()
    st.stop()

# --- PART 6: SIDEBAR (STEM TOOLS) ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    st.divider()
    
    # Restored Persona & Language
    persona = st.selectbox("Persona", ["Strict Professor", "Friendly Mentor", "Quirky Scientist"])
    lang = st.selectbox("Language", ["English", "Japanese", "Bahasa Melayu"])
    
    st.divider()
    # Formula Library
    st.subheader("🧪 Formula Library")
    for name, tex in FORMULA_LIB.items():
        if st.button(f"Inject {name}"): st.session_state.injected_tex = tex
    
    st.divider()
    # Image Solver
    uploaded_file = st.file_uploader("📷 Solve STEM Image", type=['png', 'jpg', 'jpeg'])
    
    st.divider()
    # Session Management
    sessions = db_q('SELECT session_id, session_name, last_modified, mood_emoji FROM chat_sessions WHERE username=? ORDER BY last_modified DESC', (st.session_state.username,), True)
    if st.button("➕ New Session"):
        nid = str(uuid.uuid4())
        db_q('INSERT INTO chat_sessions VALUES (?,?,?,?,?)', (nid, st.session_state.username, "New Evolution", datetime.datetime.now().strftime("%d %b"), "💬"))
        st.session_state.sid, st.session_state.messages = nid, []; st.rerun()

    if sessions:
        s_dict = {f"{s[3]} {s[1]}": s[0] for s in sessions}
        sel = st.selectbox("Timeline:", list(s_dict.keys()))
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

    if st.session_state.username == ADMIN:
        with st.expander("🕵️ ADMIN VAULT"):
            if st.button("⚡ Sync Evolution"):
                e, pw, mo = analyze_all(st.session_state.username, st.session_state.sid); st.rerun()

# --- PART 7: CHAT CORE ---
st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)

if 'sid' not in st.session_state: 
    st.session_state.sid = str(uuid.uuid4())
    db_q('INSERT OR IGNORE INTO chat_sessions VALUES (?,?,?,?,?)', (st.session_state.sid, st.session_state.username, "Initial Entry", datetime.datetime.now().strftime("%d %b"), "💬"))

ai_av = f"data:image/jpeg;base64,{get_64(AVATAR)}" if get_64(AVATAR) else "🤖"
for m in st.session_state.messages: 
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): st.markdown(m["content"])

# Handle Formula Injection
default_input = st.session_state.get("injected_tex", "")
user_in = st.chat_input("Continue evolution...", key="chat_input")
if default_input:
    st.info(f"Formula Injected: {default_input}")
    st.session_state.injected_tex = None # Clear after use

if user_in or uploaded_file:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    # Handle Vision vs Text
    model_id = "llama-3.3-70b-versatile"
    content_payload = user_in
    
    if uploaded_file:
        model_id = "llama-3.2-11b-vision-preview"
        img_64 = base64.b64encode(uploaded_file.getvalue()).decode()
        content_payload = [
            {"type": "text", "text": user_in if user_in else "Analyze this STEM image/equation."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_64}"}}
        ]
        with st.chat_message("user", avatar="👤"): st.image(uploaded_file, width=300)

    # UI Update
    if not uploaded_file:
        with st.chat_message("user", avatar="👤"): st.markdown(user_in)
    
    st.session_state.messages.append({"role": "user", "content": user_in if user_in else "Image Upload"})
    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", user_in if user_in else "Image Upload", st.session_state.sid))

    with st.chat_message("assistant", avatar=ai_av):
        res = db_q('SELECT secret_profile FROM users WHERE username=?', (st.session_state.username,), True)
        profile = res[0][0] if res else "New"
        sys = f"You are a {persona} in {lang}. Use LaTeX for all math. Context: {profile}"
        
        chat_res = client.chat.completions.create(model=model_id, messages=[{"role":"system","content":sys}] + st.session_state.messages[-10:])
        ans = chat_res.choices[0].message.content
        st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))

components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)

