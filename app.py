import streamlit as st
import sqlite3, base64, os, time, uuid, datetime
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
from groq import Groq

# --- PART 1: SETTINGS & DATABASE ---
LOGO_FILENAME = "vison_logo.jpg"
AI_AVATAR_FILENAME = "ai_logo_glow.jpg"
ADMIN = "0102383"

def get_64(p):
    if os.path.exists(p):
        with open(p, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

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

# --- PART 2: CASIO CLASSWIZ ENGINE (HTML/JS) ---
def render_casio_calculator():
    CALC_HTML = """
    <style>
        body { background-color: transparent; color: white; font-family: sans-serif; margin: 0; }
        .calc-body { background: #333; border: 4px solid #fff; border-radius: 15px; width: 100%; max-width: 300px; padding: 15px; box-shadow: 0px 10px 30px rgba(0,0,0,0.7); margin: auto; }
        .calc-screen { background-color: #a8b0a0; color: black; font-family: 'Courier New', monospace; font-size: 24px; text-align: right; padding: 10px; height: 50px; border-radius: 5px; margin-bottom: 15px; border: 2px solid #555; overflow: hidden;}
        .btn-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        button { height: 40px; border-radius: 5px; border: 1px solid #555; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.1s; }
        button:active { transform: translateY(2px); }
        .btn-num { background-color: white; color: black; }
        .btn-op { background-color: #555; color: white; }
        .btn-del-ac { background-color: #2a52be; color: white; }
        .btn-sci { background-color: #777; color: white; font-size: 12px;}
    </style>
    <div class="calc-body">
        <div style="font-size:12px; font-weight:bold; margin-bottom:5px;">CASIO <span style="font-size:10px; color:#aaa; font-weight:normal;">fx-570EX CLASSWIZ</span></div>
        <div id="screen" class="calc-screen">0</div>
        <div class="btn-grid">
            <button class="btn-sci" onclick="press('sin(')">sin</button>
            <button class="btn-sci" onclick="press('cos(')">cos</button>
            <button class="btn-sci" onclick="press('tan(')">tan</button>
            <button class="btn-sci" onclick="press('sqrt(')">√</button>
            
            <button class="btn-num" onclick="press('7')">7</button>
            <button class="btn-num" onclick="press('8')">8</button>
            <button class="btn-num" onclick="press('9')">9</button>
            <button class="btn-del-ac" onclick="clear_screen()">AC</button>
            
            <button class="btn-num" onclick="press('4')">4</button>
            <button class="btn-num" onclick="press('5')">5</button>
            <button class="btn-num" onclick="press('6')">6</button>
            <button class="btn-op" onclick="press('*')">×</button>
            
            <button class="btn-num" onclick="press('1')">1</button>
            <button class="btn-num" onclick="press('2')">2</button>
            <button class="btn-num" onclick="press('3')">3</button>
            <button class="btn-op" onclick="press('/')">÷</button>
            
            <button class="btn-num" onclick="press('0')">0</button>
            <button class="btn-num" onclick="press('.')">.</button>
            <button class="btn-num" onclick="press('Math.PI')">π</button>
            <button class="btn-op" onclick="press('-')">-</button>
            
            <button class="btn-op" style="grid-column: span 3;" onclick="press('+')">+</button>
            <button class="btn-op" onclick="calculate()">=</button>
        </div>
    </div>
    <script>
        let expr = "";
        function press(v) { expr += v; document.getElementById("screen").innerText = expr; }
        function clear_screen() { expr = ""; document.getElementById("screen").innerText = "0"; }
        function calculate() { try { document.getElementById("screen").innerText = eval(expr); } catch { document.getElementById("screen").innerText = "Error"; } }
    </script>
    """
    components.html(CALC_HTML, height=400)

# --- PART 3: UI SETUP & AUTH ---
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
        else:
            st.error("Invalid Credentials.")
    st.stop()

# --- PART 4: SIDEBAR ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    
    st.divider()
    render_casio_calculator() # The Casio UI lives here now!
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

# --- PART 5: CHAT LOGIC ---
if 'sid' not in st.session_state:
    st.session_state.sid = str(uuid.uuid4())
    db_q('INSERT OR IGNORE INTO chat_sessions (session_id, username, session_name, last_modified) VALUES (?,?,?,?)', (st.session_state.sid, st.session_state.username, "Main Chat", "Now"))

if "messages" not in st.session_state: st.session_state.messages = []

ai_av = f"data:image/png;base64,{get_64(AI_AVATAR_FILENAME)}" if get_64(AI_AVATAR_FILENAME) else "🤖"
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): 
        st.markdown(m["content"])

user_in = st.chat_input("Evolve your thinking...")

# --- THE FIX: SAFETY NET FOR GROQ API ---
if user_in or uploaded_file:
    # Check if key exists in secrets before trying to use it
    if "GROQ_API_KEY" not in st.secrets:
        st.error("🚨 **API Key Missing!** Please go to Streamlit Cloud Dashboard -> Settings -> Secrets and add `GROQ_API_KEY = 'your_key_here'`.")
        st.stop()

    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        
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

    except Exception as e:
        if "AuthenticationError" in str(e) or "401" in str(e):
            st.error("🚨 **Authentication Failed!** Your Groq API key is invalid or expired. Please generate a new one at console.groq.com and update your Streamlit Secrets.")
        else:
            st.error(f"⚠️ **Engine Error:** {e}")

components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0) 
