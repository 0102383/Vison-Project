import streamlit as st
import sqlite3, base64, os, time, uuid, datetime
import streamlit.components.v1 as components
from fpdf import FPDF
from groq import Groq

# --- PART 1: SETTINGS ---
LOGO_FILENAME = "vison_logo.jpg"
AI_AVATAR_FILENAME = "ai_logo_glow.jpg"
ADMIN = "0102383"

def get_64(p):
    if os.path.exists(p):
        with open(p, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# --- PART 2: DATABASE & SELF-HEALING ---
def db_q(q, d=(), fetch=False):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    try:
        c.execute(q, d)
        res = c.fetchall() if fetch else None
        conn.commit()
        return res
    finally: conn.close()

def init_db():
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT, mood_emoji TEXT DEFAULT '💬')''')
    cols = [r[1] for r in db_q("PRAGMA table_info(chat_log)", fetch=True)]
    if 'session_id' not in cols: db_q('ALTER TABLE chat_log ADD COLUMN session_id TEXT')

# --- PART 3: MOOD-BASED CSS ---
def get_mood_color(emoji):
    mood_map = {
        "🧠": "#00d4ff", # Focused - Cyan
        "⚠️": "#ff4b4b", # Stressed - Red
        "🔥": "#ffaa00", # Motivated - Orange
        "✅": "#00ff88", # Accomplished - Green
        "💬": "#a252ff"  # Neutral - Purple
    }
    return mood_map.get(emoji, "#a252ff")

# --- PART 4: ANALYZER & PDF ---
def analyze_evolution(u, sid):
    logs = db_q('SELECT role, content FROM chat_log WHERE username=? AND session_id=? ORDER BY id DESC LIMIT 15', (u, sid), True)
    if not logs: return "Initial State", 10, "💬"
    h = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        evo = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Summarize psychological/learning blocks: {h}"}])
        pwr = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Power 0-100 (Num only): {h}"}])
        mood = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Pick 1 emoji (🧠,⚠️,🔥,✅,💬) for student mood: {h}"}])
        e, p, m = evo.choices[0].message.content, int(''.join(filter(str.isdigit, pwr.choices[0].message.content))), mood.choices[0].message.content.strip()[0]
        db_q('UPDATE users SET secret_profile=? WHERE username=?', (e, u))
        db_q('UPDATE chat_sessions SET mood_emoji=? WHERE session_id=?', (m, sid))
        return e, p, m
    except: return "Syncing...", 10, "⏳"

# --- PART 5: MAIN UI ---
st.set_page_config(page_title="VISON AI", layout="wide")
init_db()

# Fetch mood for dynamic styling
current_mood = "💬"
if 'sid' in st.session_state:
    res = db_q('SELECT mood_emoji FROM chat_sessions WHERE session_id=?', (st.session_state.sid,), True)
    if res: current_mood = res[0][0]

mood_color = get_mood_color(current_mood)

st.markdown(f"""
    <style>
    .mood-ring {{
        height: 5px; width: 100%; 
        background: linear-gradient(90deg, transparent, {mood_color}, transparent);
        box-shadow: 0px 5px 15px {mood_color};
        margin-bottom: 20px;
    }}
    .main-title {{ font-size: 45px !important; font-weight: 800; background: linear-gradient({mood_color}, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }}
    .online-indicator {{ display: inline-block; width: 10px; height: 10px; background-color: {mood_color}; border-radius: 50%; margin-right: 8px; box-shadow: 0 0 8px {mood_color}; }}
    
    /* ALIGNMENT FIX */
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) {{ flex-direction: row-reverse !important; }}
    </style>
    <div class="mood-ring"></div>
    """, unsafe_allow_html=True)

# --- PART 6: GATEWAY ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    lb = get_64(LOGO_FILENAME)
    if lb: st.markdown(f'<center><img src="data:image/jpeg;base64,{lb}" width="180"></center>', unsafe_allow_html=True)
    u, p = st.text_input("User ID"), st.text_input("Key", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_q('INSERT INTO users (username, password, interests, level) VALUES (?,?,?,?)', (u.lower(), p, "STEM", "HS"))
        if not res or res[0][0] == p: st.session_state.logged_in, st.session_state.username = True, u.lower(); st.rerun()
    st.stop()

# --- PART 7: SIDEBAR ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    st.divider()
    
    sessions = db_q('SELECT session_id, session_name, last_modified, mood_emoji FROM chat_sessions WHERE username=? ORDER BY last_modified DESC', (st.session_state.username,), True)
    if st.button("➕ New Session"):
        nid = str(uuid.uuid4())
        db_q('INSERT INTO chat_sessions VALUES (?,?,?,?,?)', (nid, st.session_state.username, "New Discovery", datetime.datetime.now().strftime("%H:%M"), "💬"))
        st.session_state.sid, st.session_state.messages = nid, []; st.rerun()
    
    if sessions:
        s_dict = {f"{s[3]} {s[1]}": s[0] for s in sessions}
        sel = st.selectbox("Sessions:", list(s_dict.keys()))
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

    if st.session_state.username == ADMIN:
        with st.expander("🕵️ ADMIN VAULT"):
            if st.button("⚡ Sync Mood & Evolution"):
                analyze_evolution(st.session_state.username, st.session_state.sid); st.rerun()

# --- PART 8: CHAT ---
st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)
st.markdown(f'<center><span class="online-indicator"></span><span style="color:{mood_color}; font-weight:bold;">MOOD: {current_mood}</span></center>', unsafe_allow_html=True)

ai_av = f"data:image/png;base64,{get_64(AI_AVATAR_FILENAME)}" if get_64(AI_AVATAR_FILENAME) else "🤖"
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): st.markdown(m["content"])

user_in = st.chat_input("Continue evolution...")
if user_in:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    st.session_state.messages.append({"role": "user", "content": user_in})
    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", user_in, st.session_state.sid))
    
    with st.chat_message("user", avatar="👤"): st.markdown(user_in)
    with st.chat_message("assistant", avatar=ai_av):
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":"You are a Strict Professor."}]+st.session_state.messages[-10:])
        ans = res.choices[0].message.content; st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))

components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)

