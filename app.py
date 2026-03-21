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

# --- PART 3: UI SETUP & AUTH (RESTORED GATEWAY) ---
st.set_page_config(page_title="VISON AI STEM", layout="wide")
init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    lb = get_64(LOGO_FILENAME)
    if lb: st.markdown(f'<center><img src="data:image/jpeg;base64,{lb}" width="180"></center>', unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>VISON CORE</h1>", unsafe_allow_html=True)
    
    auth_mode = st.radio("Access Portal", ["Log In", "Create Account", "Reset Password"], horizontal=True)
    
    if auth_mode == "Log In":
        st.subheader("Welcome Back")
        identifier = st.text_input("Email (or Admin ID)")
        p = st.text_input("Security Key", type="password")
        if st.button("Unlock Core"):
            if identifier and p:
                res = db_q('SELECT password, username FROM users WHERE email=? OR username=?', (identifier.lower(), identifier), True)
                if res and res[0][0] == p:
                    st.session_state.logged_in = True
                    st.session_state.username = res[0][1] 
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials.")
            else: st.warning("⚠️ Please fill in all fields.")
                
    elif auth_mode == "Create Account":
        st.subheader("Initialize New Student")
        new_u = st.text_input("Choose a User ID")
        new_e = st.text_input("Email Address")
        new_p = st.text_input("Create Security Key", type="password")
        new_p2 = st.text_input("Confirm Security Key", type="password")
        
        if st.button("Register Account"):
            if new_u and new_e and new_p and new_p2:
                if "@" not in new_e: st.error("❌ Please enter a valid email address.")
                elif new_p == new_p2:
                    res = db_q('SELECT username FROM users WHERE username=? OR email=?', (new_u.lower(), new_e.lower()), True)
                    if res: st.error("❌ User ID or Email already registered.")
                    else:
                        db_q('INSERT INTO users (username, password, email, interests, level) VALUES (?,?,?,?,?)', (new_u.lower(), new_p, new_e.lower(), "STEM", "HS"))
                        st.success("✅ Account created! Switch to 'Log In'.")
                else: st.error("❌ Security Keys do not match.")
            else: st.warning("⚠️ Please fill in all fields.")
                
    elif auth_mode == "Reset Password":
        st.subheader("System Override: Reset Key")
        r_e = st.text_input("Registered Email")
        r_p = st.text_input("New Security Key", type="password")
        r_p2 = st.text_input("Confirm New Key", type="password")
        
        if st.button("Execute Reset"):
            if r_e and r_p and r_p2:
                if r_p == r_p2:
                    res = db_q('SELECT username FROM users WHERE email=?', (r_e.lower(),), True)
                    if res:
                        db_q('UPDATE users SET password=? WHERE email=?', (r_p, r_e.lower()))
                        st.success("✅ Security Key updated! Switch to 'Log In'.")
                    else: st.error("❌ Email not found.")
                else: st.error("❌ Keys do not match.")
            else: st.warning("⚠️ Please fill in all fields.")

    st.stop()

# --- PART 4: SIDEBAR ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    
    st.divider()
    render_casio_calculator()
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

# --- PART 5: CHAT LOGIC & EVOLUTION ENGINE ---
if 'sid' not in st.session_state:
    st.session_state.sid = str(uuid.uuid4())
    db_q('INSERT OR IGNORE INTO chat_sessions (session_id, username, session_name, last_modified) VALUES (?,?,?,?)', (st.session_state.sid, st.session_state.username, "Main Chat", "Now"))

if "messages" not in st.session_state: st.session_state.messages = []

ai_av = f"data:image/png;base64,{get_64(AI_AVATAR_FILENAME)}" if get_64(AI_AVATAR_FILENAME) else "🤖"
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): 
        st.markdown(m["content"])

user_in = st.chat_input("Ask a question, or type 'Evolve: <command>'...")

# ==========================================
# 🧬 THE EVOLUTION ENGINE: STAGING AREA
# ==========================================
if st.session_state.get("pending_mutation"):
    st.divider()
    st.markdown("## 🔬 Review Proposed DNA Mutation")
    st.warning("⚠️ **WARNING:** Approving this will permanently overwrite the `app.py` file on your server.")
    
    st.code(st.session_state.pending_mutation, language="python")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚠️ APPROVE & OVERWRITE APP", type="primary", use_container_width=True):
            try:
                with open(__file__, "w", encoding="utf-8") as file:
                    file.write(st.session_state.pending_mutation)
                del st.session_state["pending_mutation"]
                st.success("✅ App successfully evolved! Rebooting core...")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to write file: {e}")
    with col2:
        if st.button("❌ REJECT MUTATION", use_container_width=True):
            del st.session_state["pending_mutation"]
            st.info("Evolution aborted. Core remains unchanged.")
            st.rerun()
            
    st.stop()

# ==========================================
# NORMAL CHAT & EVOLUTION TRIGGER
# ==========================================
if user_in or uploaded_file:
    if "GROQ_API_KEY" not in st.secrets:
        st.error("🚨 **API Key Missing!** Please add `GROQ_API_KEY` to Streamlit Secrets.")
        st.stop()

    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    # 🧬 INTERCEPT: IS IT AN EVOLVE COMMAND?
    if user_in and user_in.lower().startswith("evolve:"):
        with st.spinner("🧬 Synthesizing new application DNA... Please wait (this takes about 10-20 seconds)."):
            with open(__file__, "r", encoding="utf-8") as file:
                current_code = file.read()
                
            system_prompt = """
            You are an auto-evolving AI expert in Python and Streamlit.
            The user wants to add a feature or alter the current script.
            You MUST output the ENTIRE, COMPLETE updated Python code for the app.
            DO NOT output explanations, introductory text, or conversational text.
            Output ONLY raw, valid, properly indented Python code.
            """
            
            try:
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Current Code:\n{current_code}\n\nRequested Evolution: {user_in}"}
                    ]
                )
                
                proposed_code = res.choices[0].message.content.strip()
                
                # Robust stripping of markdown to prevent syntax errors
                if proposed_code.startswith("
