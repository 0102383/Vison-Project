import streamlit as st
import sqlite3
import base64
import os
import time
import uuid
import streamlit.components.v1 as components
from fpdf import FPDF

# --- ⚙️ MASTER SETTINGS ⚙️ ---
LOGO_FILENAME = "vison_logo.jpg" 
AI_AVATAR_FILENAME = "ai_logo_glow.jpg"
ADMIN_USERNAME = "0102383" 

# --- 1. SAFE LIBRARY IMPORT ---
client = None
try:
    from groq import Groq
    if "GROQ_API_KEY" in st.secrets:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except ImportError:
    st.error("🚀 Please add `groq` to your `requirements.txt`!")

# --- 2. DATABASE & SESSIONS ---
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT DEFAULT 'default')''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT)''')
    conn.commit()
    conn.close()

def manage_user(username, password):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if row is None:
        c.execute('INSERT INTO users (username, password, interests, level) VALUES (?, ?, ?, ?)', (username, password, "General", "High School"))
        conn.commit()
        conn.close()
        return "registered"
    elif row[0] == password:
        conn.close()
        return "authorized"
    else:
        conn.close()
        return "denied"

def save_profile(u, i, l):
    conn = sqlite3.connect('vison_user_data.db')
    conn.cursor().execute('UPDATE users SET interests=?, level=? WHERE username=?', (i, l, u))
    conn.commit()
    conn.close()

def save_secret_profile(u, secret_text):
    conn = sqlite3.connect('vison_user_data.db')
    conn.cursor().execute('UPDATE users SET secret_profile=? WHERE username=?', (secret_text, u))
    conn.commit()
    conn.close()

def get_profile(u):
    conn = sqlite3.connect('vison_user_data.db')
    res = conn.cursor().execute('SELECT interests, level, secret_profile FROM users WHERE username=?', (u,)).fetchone()
    conn.close()
    if res:
        return {"interests": res[0] or "General", "level": res[1] or "High School", "secret": res[2] or "No data yet."}
    return {"interests": "General", "level": "High School", "secret": "No data yet."}

def save_message(u, r, c, s_id):
    conn = sqlite3.connect('vison_user_data.db')
    conn.cursor().execute('INSERT INTO chat_log (username, role, content, session_id) VALUES (?, ?, ?, ?)', (u, r, str(c), str(s_id)))
    conn.commit()
    conn.close()

def load_memory(u, s_id):
    conn = sqlite3.connect('vison_user_data.db')
    data = conn.cursor().execute('SELECT role, content FROM chat_log WHERE username=? AND session_id=? ORDER BY id ASC', (u, s_id)).fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in data]

def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    return None

def get_all_users_data():
    conn = sqlite3.connect('vison_user_data.db')
    data = conn.cursor().execute('SELECT username, interests, secret_profile FROM users').fetchall()
    conn.close()
    return data

def run_auto_brain(username, messages):
    if client and len(messages) > 1:
        try:
            user_texts = [m["content"] for m in messages if m["role"] == "user"][-5:]
            joined = " | ".join(user_texts)
            # 1. Topics
            res1 = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"Extract 3 study keywords: {joined}"}])
            ints = res1.choices[0].message.content.strip()
            # 2. Psychology
            res2 = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"Write a 1-sentence psychological profile of this student based on: {joined}"}])
            sec = res2.choices[0].message.content.strip()
            save_profile(username, ints, "High School")
            save_secret_profile(username, sec)
            return True
        except: return False
    return False

init_db()
ai_avatar_b64 = get_image_base64(AI_AVATAR_FILENAME)

# --- 3. UI ---
st.set_page_config(page_title="VISON AI", page_icon="🚀", layout="wide")
st.markdown("<style>.main-title { font-size: 50px; font-weight: 800; background: -webkit-linear-gradient(#a252ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }</style>", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    logo_b64 = get_image_base64(LOGO_FILENAME)
    if logo_b64: st.markdown(f'<center><img src="data:image/jpeg;base64,{logo_b64}" width="300"></center>', unsafe_allow_html=True)
    cols = st.columns([1, 2, 1]); u = cols[1].text_input("Username"); p = cols[1].text_input("Password", type="password")
    if cols[1].button("Unlock AI"):
        if manage_user(u.lower().strip(), p) in ["registered", "authorized"]:
            st.session_state.logged_in = True; st.session_state.username = u.lower().strip(); st.rerun()
    st.stop()

# --- 4. SESSIONS ---
conn = sqlite3.connect('vison_user_data.db')
c = conn.cursor()
c.execute('SELECT DISTINCT session_id FROM chat_log WHERE username=?', (st.session_state.username,))
db_sessions = [row[0] for row in c.fetchall() if row[0] is not None]
conn.close()

if "current_session" not in st.session_state:
    st.session_state.current_session = db_sessions[-1] if db_sessions else str(uuid.uuid4())
if st.session_state.current_session not in db_sessions: db_sessions.append(st.session_state.current_session)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    if st.button("🚪 Logout", use_container_width=True): st.session_state.clear(); st.rerun()
    st.markdown("---")
    
    st.subheader("📁 Chat History")
    if st.button("➕ New Chat"):
        st.session_state.current_session = str(uuid.uuid4()); st.session_state.messages = []; st.rerun()
    
    sel_session = st.selectbox("Past Chats:", db_sessions[::-1], index=0)
    if sel_session != st.session_state.current_session:
        st.session_state.current_session = sel_session; st.session_state.messages = load_memory(st.session_state.username, sel_session); st.rerun()

    st.markdown("---")
    st.subheader("📝 Quick Quiz")
    with st.expander("Start Quiz"):
        subj = st.text_input("Subject", "Math")
        if st.button("🚀 Go"):
            st.session_state.quiz_mode = True
            st.session_state.pending_prompt = f"Give me a 3-question {subj} quiz. Ask one by one."
            st.rerun()

    st.markdown("---")
    st.subheader("⏱️ Focus Timer")
    mins = st.number_input("Minutes", 1, 60, 25)
    if st.button("Start Timer"):
        ph = st.empty()
        for i in range(mins*60, 0, -1):
            m, s = divmod(i, 60); ph.metric("Focusing...", f"{m:02d}:{s:02d}"); time.sleep(1)
        st.balloons()

    st.markdown("---")
    math_mode = st.toggle("📐 Math Mode", True)
    prof = get_profile(st.session_state.username)
    persona = st.selectbox("Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor", "Casual Buddy"])
    lang = st.selectbox("Language", ["English", "Bahasa Melayu"])

    if st.session_state.username == ADMIN_USERNAME:
        st.markdown("---")
        with st.expander("🕵️ VISON Vault 2.1"):
            if st.button("🔄 Force Sync AI Analytics"):
                if run_auto_brain(st.session_state.username, st.session_state.get('messages', [])):
                    st.success("Vault Updated!")
                    time.sleep(1)
                    st.rerun()
            for u_n, u_i, u_s in get_all_users_data():
                st.markdown(f"**{u_n}**")
                st.caption(f"Topic: {u_i}")
                st.info(u_s)
                st.divider()

# --- 6. CHAT ---
st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)
if "messages" not in st.session_state: st.session_state.messages = load_memory(st.session_state.username, st.session_state.current_session)

for m in st.session_state.messages:
    av = f"data:image/jpeg;base64,{ai_avatar_b64}" if m["role"] == "assistant" and ai_avatar_b64 else "👤"
    with st.chat_message(m["role"], avatar=av): st.markdown(m["content"])

up_file = st.file_uploader("➕ Image", type=['png', 'jpg', 'jpeg'], key="vup")
user_in = st.chat_input("Ask Vison...")

if st.session_state.get("pending_prompt"):
    user_in = st.session_state.pending_prompt; st.session_state.pending_prompt = None

if user_in:
    st.session_state.messages.append({"role": "user", "content": user_in})
    save_message(st.session_state.username, "user", user_in, st.session_state.current_session)
    with st.chat_message("user", avatar="👤"): st.markdown(user_in)

    with st.chat_message("assistant", avatar=f"data:image/jpeg;base64,{ai_avatar_b64}" if ai_avatar_b64 else "🤖"):
        try:
            m_id = "llama-3.2-11b-vision-instruct" if up_file else "llama-3.3-70b-versatile"
            sys_m = f"You are {persona} in {lang}. {prof['secret']}. {'Use LaTeX $$' if math_mode else ''}"
            res = client.chat.completions.create(model=m_id, messages=[{"role": "system", "content": sys_m}] + st.session_state.messages)
            ans = res.choices[0].message.content
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            save_message(st.session_state.username, "assistant", ans, st.session_state.current_session)
        except Exception as e: st.error(f"Error: {e}")

components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)
