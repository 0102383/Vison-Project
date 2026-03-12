import streamlit as st
import sqlite3
import base64
import os
import time
import uuid
import streamlit.components.v1 as components
from fpdf import FPDF
from groq import Groq

# --- PART 1: MASTER SETTINGS ---
LOGO_FILENAME = "vison_logo.jpg" 
AI_AVATAR_FILENAME = "ai_logo_glow.jpg"
ADMIN_USERNAME = "0102383" 

# --- PART 2: DATABASE & SECURITY ---
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT DEFAULT 'default')''')
    conn.commit(); conn.close()

def manage_user(u, p):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?', (u,))
    row = c.fetchone()
    if row is None:
        c.execute('INSERT INTO users (username, password, interests, level) VALUES (?, ?, ?, ?)', (u, p, "General STEM", "High School"))
        conn.commit(); conn.close(); return "registered"
    conn.close()
    return "authorized" if row[0] == p else "denied"

# --- PART 3: PDF GENERATION ENGINE ---
def create_pdf(history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="VISON AI - STUDY NOTES", ln=True, align='C')
    pdf.set_font("Arial", size=11)
    for m in history:
        role = "YOU" if m['role'] == "user" else "VISON AI"
        pdf.multi_cell(0, 8, txt=f"\n{role}: {m['content']}")
    return pdf.output(dest='S').encode('latin-1')

# --- PART 4: GLOBAL MEMORY & BRAIN LOGIC ---
def get_global_context(u):
    conn = sqlite3.connect('vison_user_data.db')
    past_logs = conn.cursor().execute('SELECT content FROM chat_log WHERE username=? AND role="user" ORDER BY id DESC LIMIT 15', (u,)).fetchall()
    res = conn.cursor().execute('SELECT interests, level, secret_profile FROM users WHERE username=?', (u,)).fetchone()
    conn.close()
    context_summary = " ".join([row[0] for row in past_logs])
    return {
        "ints": res[0] if res else "General", 
        "lvl": res[1] if res else "High School", 
        "sec": res[2] if res else "No data yet.",
        "history_context": context_summary[-600:] 
    }

def save_mem(u, i, l):
    conn = sqlite3.connect('vison_user_data.db')
    conn.cursor().execute('UPDATE users SET interests=?, level=? WHERE username=?', (i, l, u))
    conn.commit(); conn.close()

def purge_memory(u):
    conn = sqlite3.connect('vison_user_data.db')
    conn.cursor().execute('DELETE FROM chat_log WHERE username=?', (u,))
    conn.cursor().execute('UPDATE users SET interests="General", secret_profile="No data yet." WHERE username=?', (u,))
    conn.commit(); conn.close()

# --- PART 5: UI STYLING ---
st.set_page_config(page_title="VISON AI", layout="wide")
st.markdown("<style>.main-title { font-size: 50px; font-weight: 800; background: linear-gradient(45deg, #a252ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }</style>", unsafe_allow_html=True)

# --- PART 6: SIDEBAR (THE BRAIN CONTROLLER) ---
init_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<p class="main-title">VISON LOGIN</p>', unsafe_allow_html=True)
    u_log = st.text_input("Username"); p_log = st.text_input("Password", type="password")
    if st.button("Unlock Core"):
        if manage_user(u_log.lower().strip(), p_log) != "denied":
            st.session_state.logged_in = True; st.session_state.username = u_log.lower().strip()
            st.session_state.current_session = str(uuid.uuid4()); st.rerun()
    st.stop()

with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("🚪 Logout", use_container_width=True): st.session_state.clear(); st.rerun()
    st.divider()
    
    if st.button("➕ New Separate Chat", use_container_width=True):
        st.session_state.current_session = str(uuid.uuid4()); st.session_state.messages = []; st.success("New Session Active")

    st.subheader("🧠 Global Memory")
    prof = get_global_context(st.session_state.username)
    new_ints = st.text_area("Personality / Study Notes", value=prof["ints"])
    new_lvl = st.selectbox("Level", ["Primary", "High School", "University"], index=1)
    if st.button("💾 Save to Global Memory"):
        save_mem(st.session_state.username, new_ints, new_lvl); st.success("Saved!")

    with st.expander("⚠️ Danger Zone"):
        if st.button("🗑️ Purge All Memory", help="This wipes all chat history and AI notes permanently."):
            purge_memory(st.session_state.username); st.session_state.messages = []; st.warning("Memory Wiped!"); time.sleep(1); st.rerun()

    st.divider()
    persona = st.selectbox("Persona", ["Friendly Mentor", "Strict Professor", "Quirky Scientist", "Casual Buddy"])
    lang = st.selectbox("Language", ["English", "Bahasa Melayu"])
    
    if st.session_state.username == ADMIN_USERNAME:
        with st.expander("🕵️ ADMIN VAULT"):
            conn = sqlite3.connect('vison_user_data.db'); users = conn.cursor().execute('SELECT username, interests, secret_profile FROM users').fetchall(); conn.close()
            for un, ui, us in users: st.write(f"**{un}**\nNotes: {ui}\nAI Analysis: {us}"); st.divider()

# --- PART 7: MAIN CHAT LOGIC ---
st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)
if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

up = st.file_uploader("Upload Image", type=['png','jpg','jpeg'])
user_in = st.chat_input("Ask Vison...")

if user_in:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    st.session_state.messages.append({"role": "user", "content": user_in})
    conn = sqlite3.connect('vison_user_data.db'); conn.cursor().execute('INSERT INTO chat_log (username, role, content, session_id) VALUES (?, ?, ?, ?)', (st.session_state.username, "user", user_in, st.session_state.current_session)); conn.commit(); conn.close()
    with st.chat_message("user"): st.markdown(user_in)

    with st.chat_message("assistant"):
        m_id = "llama-3.2-11b-vision-instruct" if up else "llama-3.3-70b-versatile"
        sys_p = f"You are {persona} in {lang}. GLOBAL CONTEXT: {prof['history_context']}. NOTES: {prof['ints']}. AI INSIGHT: {prof['sec']}"
        res = client.chat.completions.create(model=m_id, messages=[{"role":"system","content":sys_p}]+st.session_state.messages)
        ans = res.choices[0].message.content
        st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        conn = sqlite3.connect('vison_user_data.db'); conn.cursor().execute('INSERT INTO chat_log (username, role, content, session_id) VALUES (?, ?, ?, ?)', (st.session_state.username, "assistant", ans, st.session_state.current_session)); conn.commit(); conn.close()

# --- PART 8: AUTO-SCROLL ---
components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)
