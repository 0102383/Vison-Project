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
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT DEFAULT 'default')''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT)''')
    
    try: c.execute("ALTER TABLE users ADD COLUMN interests TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN level TEXT")
    except: pass
    try: c.execute("ALTER TABLE chat_log ADD COLUMN session_id TEXT DEFAULT 'default'")
    except: pass
    conn.commit()
    conn.close()

def manage_user(username, password):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if row is None:
        c.execute('INSERT INTO users (username, password, interests, level) VALUES (?, ?, ?, ?)', (username, password, "", "High School"))
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

def get_profile(u):
    conn = sqlite3.connect('vison_user_data.db')
    res = conn.cursor().execute('SELECT interests, level FROM users WHERE username=?', (u,)).fetchone()
    conn.close()
    return {"interests": res[0] or "STEM", "level": res[1] or "High School"} if res else {"interests": "STEM", "level": "High School"}

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

def create_pdf(history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="VISON AI - Study Session", ln=True, align='C')
    pdf.set_font("Arial", size=11)
    for m in history:
        role = "YOU" if m['role'] == "user" else "VISON AI"
        pdf.multi_cell(0, 8, txt=f"\n{role}: {m['content']}")
    return pdf.output(dest='S').encode('latin-1')

def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    return None

init_db()
ai_avatar_b64 = get_image_base64(AI_AVATAR_FILENAME)

# --- 3. UI SETUP ---
st.set_page_config(page_title="VISON AI", page_icon="🚀", layout="wide")
st.markdown("""
    <style>
    .main-title { font-size: 50px; font-weight: 800; background: -webkit-linear-gradient(#a252ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) { flex-direction: row-reverse !important; text-align: right !important; }
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) > div { background-color: rgba(162, 82, 255, 0.1) !important; border: 1px solid #a252ff !important; border-radius: 15px !important; }
    div[data-testid="stChatMessage"]:has(img[data-testid="stChatMessageAvatarImage"]) > div { background-color: rgba(0, 114, 255, 0.1) !important; border: 1px solid #0072ff !important; border-radius: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. LOGIN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    logo_b64 = get_image_base64(LOGO_FILENAME)
    if logo_b64: st.markdown(f'<center><img src="data:image/jpeg;base64,{logo_b64}" width="300"></center>', unsafe_allow_html=True)
    
    cols = st.columns([1, 2, 1])
    with cols[1]:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Unlock AI"):
            if manage_user(u.lower().strip(), p) in ["registered", "authorized"]:
                st.session_state.logged_in = True
                st.session_state.username = u.lower().strip()
                st.rerun()
    st.stop()

# --- 5. CHAT SESSIONS & AUTO-LEARN LOGIC ---
conn = sqlite3.connect('vison_user_data.db')
c = conn.cursor()

c.execute('SELECT DISTINCT session_id FROM chat_log WHERE username=?', (st.session_state.username,))
db_sessions = [row[0] for row in c.fetchall() if row[0] is not None]

c.execute('SELECT session_id, session_name FROM chat_sessions WHERE username=?', (st.session_state.username,))
session_names = {row[0]: row[1] for row in c.fetchall()}
conn.close()

if "current_session" not in st.session_state:

