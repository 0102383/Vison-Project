import streamlit as st
import sqlite3, base64, os, time, uuid, datetime
import streamlit.components.v1 as components
from fpdf import FPDF
from groq import Groq

# --- PART 1: SETTINGS & AVATARS ---
LOGO, AVATAR, ADMIN = "vison_logo.jpg", "ai_logo_glow.jpg", "0102383"

def get_64(p):
    if os.path.exists(p):
        with open(p, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# --- PART 2: DATABASE ENGINE ---
def db_q(q, d=(), fetch=False):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor(); c.execute(q, d)
    res = c.fetchall() if fetch else None
    conn.commit(); conn.close(); return res

def init_db():
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT, mood_emoji TEXT DEFAULT '💬')''')

# --- PART 3: PDF ENGINE ---
def create_pdf(history):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "VISON AI NOTES", ln=True, align='C'); pdf.set_font("Arial", size=11)
    for m in history: pdf.multi_cell(0, 8, f"\n{'YOU' if m['role']=='user' else 'VISON'}: {m['content']}")
    return pdf.output(dest='S').encode('latin-1')

# --- PART 4: BRAIN & EVOLUTION LOGIC ---
def get_mem(u):
    past = db_q('SELECT content FROM chat_log WHERE username=? AND role="user" ORDER BY id DESC LIMIT 15', (u,), True)
    res = db_q('SELECT interests, level, secret_profile FROM users WHERE username=?', (u,), True)
    txt = " ".join([r[0] for r in past])
    return {"i": res[0][0] if res else "STEM", "l": res[0][1] if res else "HS", "s": res[0][2] if res else "None", "c": txt[-600:]}

def analyze_all(u, sid):
    logs = db_q('SELECT role, content FROM chat_log WHERE username=? AND session_id=? ORDER BY id DESC LIMIT 20', (u, sid), True)
    if not logs: return "No data", 10, "💬"
    h = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        evo = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Summarize emotional blocks/feelings: {h}"}])
        pwr = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Academic Power 0-100 (Num only): {h}"}])
        mood = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Pick 1 emoji representing the student mood: {h}"}])
        m_emo = mood.choices[0].message.content.strip()[0]
        db_q('UPDATE chat_sessions SET mood_emoji=? WHERE session_id=?', (m_emo, sid))
        return evo.choices[0].message.content, int(''.join(filter(str.isdigit, pwr.choices[0].message.content))), m_emo
    except: return "Engine Error", 10, "⚠️"

# --- PART 5: UI STYLE ---
st.set_page_config(page_title="VISON AI", layout="wide")
st.markdown("<style>.title { font-size:40px; font-weight:800; background:linear-gradient(45deg,#a252ff,#0072ff); -webkit-background-clip:text; -webkit-text-fill-color:transparent; text-align:center; }</style>", unsafe_allow_html=True)

# --- PART 6: SIDEBAR & SESSIONS ---
init_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    logo = get_64(LOGO)
    if logo: st.markdown(f'<center><img src="data:image/jpeg;base64,{logo}" width="180"></center>', unsafe_allow_html=True)
    st.markdown('<p class="title">VISON CORE</p>', unsafe_allow_html=True)
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_q('INSERT)
