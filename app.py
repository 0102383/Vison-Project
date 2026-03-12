import streamlit as st
import sqlite3
import base64
import os
import time
from fpdf import FPDF
import io

# --- ⚙️ MASTER SETTINGS ⚙️ ---
LOGO_FILENAME = "vison_logo.jpg.png" 
AI_AVATAR_FILENAME = "ai_logo_glow.png"

# --- 1. DATABASE & AUTH ---
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT)''')
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
        return "registered"
    return "authorized" if row[0] == password else "denied"

def save_profile(u, i, l):
    conn = sqlite3.connect('vison_user_data.db')
    conn.cursor().execute('UPDATE users SET interests=?, level=? WHERE username=?', (i, l, u))
    conn.commit()
    conn.close()

def get_profile(u):
    conn = sqlite3.connect('vison_user_data.db')
    res = conn.cursor().execute('SELECT interests, level FROM users WHERE username=?', (u,)).fetchone()
    return {"interests": res[0] or "STEM", "level": res[1] or "High School"} if res else {"interests": "STEM", "level": "High School"}

def save_message(u, r, c):
    conn = sqlite3.connect('vison_user_data.db')
    conn.cursor().execute('INSERT INTO chat_log (username, role, content) VALUES (?, ?, ?)', (u, r, str(c)))
    conn.commit()
    conn.close()

# --- PDF GENERATOR ---
def create_pdf(history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for m in history:
        pdf.multi_cell(0, 10, txt=f"{m['role'].upper()}: {m['content']}")
    return pdf.output(dest='S').encode('latin-1')

init_db()

# --- UI SETUP ---
st.set_page_config(page_title="VISON AI", layout="wide")
st.markdown("""<style>.main-title { font-size: 45px; font-weight: 800; background: linear-gradient(to right, #a252ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }</style>""", unsafe_allow_html=True)

# --- LOGIN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Start Learning"):
        if manage_user(u, p) != "denied":
            st.session_state.logged_in = True
            st.session_state.username = u
            st.rerun()
    st.stop()

# --- SIDEBAR (TIMER + SETTINGS) ---
with st.sidebar:
    st.markdown(f"### 🚀 VISON Focus Zone")
    
    st.subheader("⏱️ Study Timer")
    minutes = st.number_input("Set Minutes", min_value=1, max_value=60, value=25)
    if st.button("Start Session"):
        ph = st.empty()
        for i in range(minutes * 60, 0, -1):
            mins, secs = divmod(i, 60)
            ph.metric("Time Left", f"{mins:02d}:{secs:02d}")
            time.sleep(1)
        st.balloons()
        st.success("Session Complete!")
    
    st.markdown("---")
    math_mode = st.toggle("📐 Math Mode", value=True)
    profile = get_profile(st.session_state.username)
    new_ints = st.text_area("🧠 My Interests", value=profile["interests"])
    new_level = st.selectbox("🎓 Level", ["Primary", "High School", "University"], index=1)
    if st.button("Update Memory"): save_profile(st.session_state.username, new_ints, new_level)
    
    persona = st.selectbox("Persona", ["Friendly Mentor", "Quirky Scientist", "Casual Chat Buddy"])
    lang = st.selectbox("Language", ["English", "Bahasa Melayu", "Japanese"])

# --- MAIN CHAT ---
st.markdown('<p class="main-title">VISON AI CORE</p>', unsafe_allow_html=True)
if "messages" not in st.session_state: 
    conn = sqlite3.connect('vison_user_data.db')
    data = conn.cursor().execute('SELECT role, content FROM chat_log WHERE username=? ORDER BY id ASC', (st.session_state.username,)).fetchall()
    st.session_state.messages = [{"role": r, "content": c} for r, c in data]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

st.markdown("---")
uploaded_file = st.file_uploader("➕ Add Image", type=['png', 'jpg', 'jpeg'])
user_input = st.chat_input("Ask Vison...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_message(st.session_state.username, "user", user_input)
    with st.chat_message("user"): st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            from groq import Groq
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            model = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.1-8b-instant"
            
            math_text = "Use LaTeX $$ for equations." if math_mode else ""
            sys_m = f"You are {persona} in {lang}. Level: {new_level}. Interests: {new_ints}. {math_text}"
            
            res = client.chat.completions.create(model=model, messages=[{"role": "system", "content": sys_m}] + st.session_state.messages)
            ans = res.choices[0].message.content
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            save_message(st.session_state.username, "assistant", ans)
        except Exception as e:
            st.error(f"Error: {e}")
