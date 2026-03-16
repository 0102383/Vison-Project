import streamlit as st
import sqlite3, base64, os, time, uuid, datetime, re
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
import numpy as np
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

# --- PART 2: DATABASE ---
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
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, email TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    try: db_q('ALTER TABLE users ADD COLUMN email TEXT') 
    except: pass
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT, mood_emoji TEXT DEFAULT '💬')''')

# --- PART 3: REPORT ENGINE ---
def create_evolution_pdf(user, power, evolution, history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(200, 15, "VISON AI: EVOLUTION REPORT", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Student: {user.upper()} | Power Level: {power}/100", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, str(evolution))
    return pdf.output(dest='S').encode('latin-1')

# --- PART 4: ANALYZER & GRAPHER ---
def analyze_all(u, sid):
    logs = db_q('SELECT role, content FROM chat_log WHERE username=? AND session_id=? ORDER BY id DESC LIMIT 20', (u, sid), True)
    if not logs: return "No data yet.", 0, "💬"
    h = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        evo = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": "Analyze user emotions in 2 sentences."}, {"role":"user","content": h}])
        pwr = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": "Return only a number 1-100."}, {"role":"user","content": h}])
        p_text = ''.join(filter(str.isdigit, pwr.choices[0].message.content))
        return evo.choices[0].message.content, int(p_text) if p_text else 10, "🧠"
    except: return "Engine Busy.", 10, "⏳"

def simple_plot(equation_str):
    try:
        x = np.linspace(-10, 10, 400)
        safe_eq = equation_str.replace('^', '**').replace('sin', 'np.sin').replace('cos', 'np.cos')
        y = eval(safe_eq)
        fig, ax = plt.subplots(); ax.plot(x, y, color='#a252ff'); return fig
    except: return None

def get_mood_color(emoji):
    mood_map = {"🧠": "#00d4ff", "⚠️": "#ff4b4b", "🔥": "#ffaa00", "✅": "#00ff88", "💬": "#a252ff"}
    return mood_map.get(emoji, "#a252ff")

# --- PART 5: UI SETUP ---
st.set_page_config(page_title="VISON AI STEM", layout="wide")
init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>VISON CORE</h1>", unsafe_allow_html=True)
    identifier = st.text_input("Email or Admin ID")
    p = st.text_input("Security Key", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password, username FROM users WHERE email=? OR username=?', (identifier.lower(), identifier), True)
        if res and res[0][0] == p:
            st.session_state.logged_in = True
            st.session_state.username = res[0][1]
            st.rerun()
    st.stop()

# --- PART 6: SIDEBAR ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    st.divider()
    persona = st.selectbox("Persona", ["Strict Professor", "Friendly Mentor"])
    lang = st.selectbox("Language", ["English", "Japanese", "Bahasa Melayu"])
    uploaded_file = st.file_uploader("📷 Solve STEM Equation", type=['png', 'jpg', 'jpeg'])
    
    sessions = db_q('SELECT session_id, session_name FROM chat_sessions WHERE username=? ORDER BY last_modified DESC', (st.session_state.username,), True)
    if st.button("➕ New Session"):
        nid = str(uuid.uuid4())
        db_q('INSERT INTO chat_sessions (session_id, username, session_name, last_modified) VALUES (?,?,?,?)', (nid, st.session_state.username, "New Session", "Now"))
        st.session_state.sid = nid; st.rerun()
    
    if sessions:
        s_dict = {s[1]: s[0] for s in sessions}
        sel = st.selectbox("Sessions", list(s_dict.keys()))
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

# --- PART 7: CHAT LOGIC ---
if 'sid' not in st.session_state:
    st.session_state.sid = str(uuid.uuid4())
    db_q('INSERT OR IGNORE INTO chat_sessions (session_id, username, session_name, last_modified) VALUES (?,?,?,?)', (st.session_state.sid, st.session_state.username, "Main Chat", "Now"))

if "messages" not in st.session_state: st.session_state.messages = []

ai_av = f"data:image/png;base64,{get_64(AI_AVATAR_FILENAME)}" if get_64(AI_AVATAR_FILENAME) else "🤖"
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): 
        st.markdown(m["content"])

user_in = st.chat_input("Evolve your thinking...")

# --- THE FIX: PERFECTLY ALIGNED LOGIC BLOCK ---
if user_in or uploaded_file:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    now = datetime.datetime.now().strftime("%H:%M")
    
    model_to_use = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.3-70b-versatile"
    display_text = user_in if user_in else "Analyze this image."
    
    if uploaded_file:
        mime_type = uploaded_file.type 
        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode()
        content_payload = [{"type": "text", "text": display_text}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{img_b64}"}}]
        with st.chat_message("user", avatar="👤"):
            st.image(uploaded_file, width=300)
            st.markdown(display_text)
    else:
        content_payload = display_text
        with st.chat_message("user", avatar="👤"):
            st.markdown(display_text)

    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", display_text, st.session_state.sid))
    st.session_state.messages.append({"role": "user", "content": display_text})

    with st.chat_message("assistant", avatar=ai_av):
        sys_prompt = f"You are a {persona} in {lang}. Use LaTeX ($) for math."
        # Use history excluding the last message to avoid duplication
        hist = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-8:-1]]
        
        if uploaded_file:
            final_messages = hist + [{"role": "user", "content": content_payload}]
        else:
            final_messages = [{"role": "system", "content": sys_prompt}] + hist + [{"role": "user", "content": display_text}]
        
        res = client.chat.completions.create(model=model_to_use, messages=final_messages)
        ans = res.choices[0].message.content
        st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))

components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)
