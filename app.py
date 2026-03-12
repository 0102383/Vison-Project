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

# --- PART 2: DATABASE (WITH TIMESTAMPS) ---
def db_q(q, d=(), fetch=False):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor(); c.execute(q, d)
    res = c.fetchall() if fetch else None
    conn.commit(); conn.close(); return res

def init_db():
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT)''')

# --- PART 3: PDF ENGINE ---
def create_pdf(history):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "VISON AI NOTES", ln=True, align='C'); pdf.set_font("Arial", size=11)
    for m in history: pdf.multi_cell(0, 8, f"\n{'YOU' if m['role']=='user' else 'VISON'}: {m['content']}")
    return pdf.output(dest='S').encode('latin-1')

# --- PART 4: EVOLUTION & POWER ---
def get_mem(u):
    past = db_q('SELECT content FROM chat_log WHERE username=? AND role="user" ORDER BY id DESC LIMIT 15', (u,), True)
    res = db_q('SELECT interests, level, secret_profile FROM users WHERE username=?', (u,), True)
    txt = " ".join([r[0] for r in past])
    return {"i": res[0][0], "l": res[0][1], "s": res[0][2], "c": txt[-600:]} if res else {"i":"General","l":"HS","s":"None","c":""}

def analyze_all(u):
    logs = db_q('SELECT role, content FROM chat_log WHERE username=? ORDER BY id DESC LIMIT 20', (u,), True)
    if not logs: return "No data", 0
    h = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        evo = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Summarize emotional blocks/feelings: {h}"}])
        pwr = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Academic Power 0-100 (Num only): {h}"}])
        return evo.choices[0].message.content, int(''.join(filter(str.isdigit, pwr.choices[0].message.content)))
    except: return "Engine Error", 10

# --- PART 5: UI STYLE ---
st.set_page_config(page_title="VISON AI", layout="wide")
st.markdown("<style>.title { font-size:40px; font-weight:800; background:linear-gradient(45deg,#a252ff,#0072ff); -webkit-background-clip:text; -webkit-text-fill-color:transparent; text-align:center; }</style>", unsafe_allow_html=True)

# --- PART 6: SIDEBAR (TIMESTAMPS RESTORED) ---
init_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    logo = get_64(LOGO)
    if logo: st.markdown(f'<center><img src="data:image/jpeg;base64,{logo}" width="180"></center>', unsafe_allow_html=True)
    st.markdown('<p class="title">VISON CORE</p>', unsafe_allow_html=True)
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_q('INSERT INTO users VALUES (?,?,?,?,?)', (u.lower(), p, "STEM", "HS", "New"))
        if not res or res[0][0] == p: st.session_state.logged_in, st.session_state.username = True, u.lower(); st.rerun()
    st.stop()

with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("🚪 Logout"): st.session_state.clear(); st.rerun()
    st.divider()
    
    # Session Manager with Timestamps
    sessions = db_q('SELECT session_id, session_name, last_modified FROM chat_sessions WHERE username=? ORDER BY last_modified DESC', (st.session_state.username,), True)
    if st.button("➕ New Chat"):
        new_id, now = str(uuid.uuid4()), datetime.datetime.now().strftime("%d %b, %H:%M")
        db_q('INSERT INTO chat_sessions VALUES (?,?,?,?)', (new_id, st.session_state.username, "New Conversation", now))
        st.session_state.sid, st.session_state.messages = new_id, []; st.rerun()
    
    if sessions:
        s_list = [f"{name} ({mod})" for sid, name, mod in sessions]
        s_dict = {f"{name} ({mod})": sid for sid, name, mod in sessions}
        sel = st.selectbox("Your History", s_list)
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]
        
        n_name = st.text_input("Rename Chat", value=sel.split(' (')[0])
        if st.button("💾 Save Name"):
            db_q('UPDATE chat_sessions SET session_name=? WHERE session_id=?', (n_name, st.session_state.sid)); st.rerun()

    st.divider(); mem = get_mem(st.
