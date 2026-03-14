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

# --- PART 3: REPORT ENGINE (PDF) ---
def create_evolution_pdf(user, power, evolution, history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(200, 15, "VISON AI: EVOLUTION REPORT", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Student: {user.upper()}", ln=True)
    pdf.cell(0, 10, f"Academic Power Level: {power}/100", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Mental Evolution & Blocks:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, str(evolution))
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Recent Session History:", ln=True)
    pdf.set_font("Arial", '', 10)
    for m in history[-10:]:
        role = "VISON" if m['role'] == "assistant" else "USER"
        pdf.multi_cell(0, 6, f"{role}: {m['content']}\n")
        
    return pdf.output(dest='S').encode('latin-1')

# --- PART 4: ANALYZER & GRAPHER ---
def analyze_all(u, sid):
    logs = db_q('SELECT role, content FROM chat_log WHERE username=? AND session_id=? ORDER BY id DESC LIMIT 20', (u, sid), True)
    if not logs: return "Incomplete Data", 0, "💬"
    h = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        evo = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Emotional blocks summary: {h}"}])
        pwr = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Power 0-100 (num only): {h}"}])
        mood = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Pick 1 emoji (🧠,⚠️,🔥,✅,💬) for mood: {h}"}])
        e, p, m = evo.choices[0].message.content, int(''.join(filter(str.isdigit, pwr.choices[0].message.content))), mood.choices[0].message.content.strip()[0]
        db_q('UPDATE chat_sessions SET mood_emoji=? WHERE session_id=?', (m, sid))
        db_q('UPDATE users SET secret_profile=? WHERE username=?', (e, u))
        return e, p, m
    except: return "Engine Busy", 10, "⏳"

def simple_plot(equation_str):
    try:
        x = np.linspace(-10, 10, 400)
        safe_eq = equation_str.replace('^', '**').replace('sin', 'np.sin').replace('cos', 'np.cos').replace('tan', 'np.tan')
        y = eval(safe_eq)
        fig, ax = plt.subplots()
        ax.plot(x, y, color='#a252ff', linewidth=2)
        ax.axhline(0, color='white', linewidth=0.5)
        ax.axvline(0, color='white', linewidth=0.5)
        ax.set_facecolor('#0e1117')
        fig.patch.set_facecolor('#0e1117')
        ax.tick_params(colors='white')
        ax.grid(True, linestyle='--', alpha=0.3)
        return fig
    except: return None

def get_mood_color(emoji):
    mood_map = {"🧠": "#00d4ff", "⚠️": "#ff4b4b", "🔥": "#ffaa00", "✅": "#00ff88", "💬": "#a252ff"}
    return mood_map.get(emoji, "#a252ff")

# --- PART 5: GATEWAY (NEW EMAIL AUTHENTICATION FLOW) ---
st.set_page_config(page_title="VISON AI STEM", layout="wide")
init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    lb = get_64(LOGO_FILENAME)
    if lb: st.markdown(f'<center><img src="data:image/jpeg;base64,{lb}" width="180"></center>', unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: white;'>VISON CORE</h1>", unsafe_allow_html=True)
    
    auth_mode = st.radio("Access Portal", ["Log In", "Create Account", "Reset Password"], horizontal=True)
    
    if auth_mode == "Log In":
        st.subheader("Welcome Back")
        identifier = st.text_input("Email (or Admin ID)")
        p = st.text_input("Security Key", type="password")
        if st.button("Unlock Core"):
            if identifier and p:
                if identifier == ADMIN:
                    res = db_q('SELECT password, username FROM users WHERE username=?', (identifier,), True)
                else:
                    res = db_q('SELECT password, username FROM users WHERE email=?', (identifier.lower(),), True)
                
                if res and res[0][0] == p:
                    st.session_state.logged_in = True
                    st.session_state.username = res[0][1] 
                    st.rerun()
                else:
                    st.error("❌ Invalid Email/Admin ID or Security Key.")
            else:
                st.warning("⚠️ Please enter your credentials.")
                
    elif auth_mode == "Create Account":
        st.subheader("Initialize New Student")
        new_u = st.text_input("Choose a User ID (Display Name)")
        new_e = st.text_input("Email Address")
        new_p = st.text_input("Create Security Key", type="password")
        new_p2 = st.text_input("Confirm Security Key", type="password")
        
        if st.button("Register Account"):
            if new_u and new_e and new_p and new_p2:
                if "@" not in new_e:
                    st.error("❌ Please enter a valid email address.")
                elif new_p == new_p2:
                    res = db_q('SELECT username FROM users WHERE username=? OR email=?', (new_u.lower(), new_e.lower()), True)
                    if res:
                        st.error("❌ User ID or Email is already registered.")
                    else:
                        db_q('INSERT INTO users (username, password, email, interests, level) VALUES (?,?,?,?,?)', (new_u.lower(), new_p, new_e.lower(), "STEM", "HS"))
                        st.success("✅ Account successfully created! Please switch to 'Log In'.")
                else:
                    st.error("❌ Security Keys do not match.")
            else:
                st.warning("⚠️ Please fill in all fields.")
                
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
                    else:
                        st.error("❌ Email not found in the system.")
                else:
                    st.error("❌ Security Keys do not match.")
            else:
                st.warning("⚠️ Please fill in all fields.")

    st.stop() 

# --- PART 6: SIDEBAR & PRODUCTIVITY SUITE ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    st.divider()
    
    # 🔬 SCIENTIFIC CALCULATOR
    with st.expander("🔬 Scientific Calculator"):
        st.markdown("<small><b>Functions:</b> <code>sin()</code>, <code>cos()</code>, <code>tan()</code>, <code>log()</code>, <code>ln()</code>, <code>sqrt()</code>, <code>exp()</code><br><b>Constants:</b> <code>pi</code>, <code>e</code> | <b>Power:</b> <code>^</code></small>", unsafe_allow_html=True)
        calc_input = st.text_input("Expression:")
        if calc_input:
            try:
                safe_calc = calc_input.lower().replace('^', '**').replace('sin', 'np.sin').replace('cos', 'np.cos').replace('tan', 'np.tan').replace('sqrt', 'np.sqrt').replace('pi', 'np.pi').replace('log', 'np.log10').replace('ln', 'np.log').replace('exp', 'np.exp')
                safe_calc = re.sub(r'\be\b', 'np.e', safe_calc)
                ans = eval(safe_calc)
                st.success(f"= {ans}")
            except:
                st.error("Invalid Math")

    # 🧠 MEMORY BUTTON
    if st.button("🗑️ Clear Memory"):
        if 'sid' in st.session_state:
            db_q('DELETE FROM chat_log WHERE session_id=?', (st.session_state.sid,))
            st.session_state.messages = []
            st.success("Memory Wiped")
            st.rerun()

    # 📝 QUIZ BUTTON
    if st.button("🧩 Generate Quiz"):
        st.session_state.pending_quiz = True

    # ⏱️ TIMER BUTTON
    with st.expander("⏱️ Pomodoro Timer"):
        t_min = st.number_input("Study Minutes:", 1, 120, 25)
        if st.button("Start Timer"):
            ph = st.empty()
            for i in range(t_min * 60, 0, -1):
                mins, secs = divmod(i, 60)
                ph.metric("Focus Time", f"{mins:02d}:{secs:02d}")
                time.sleep(1)
            st.success("Focus Session Done!")
            st.balloons()

    st.divider()
    persona = st.selectbox("Persona", ["Strict Professor", "Friendly Mentor", "Quirky Scientist"])
    lang = st.selectbox("Language", ["English", "Japanese", "Bahasa Melayu"])
    uploaded_file = st.file_uploader("📷 Solve STEM Equation", type=['png', 'jpg', 'jpeg'])
    
    st.divider()
    sessions = db_q('SELECT session_id, session_name, last_modified, mood_emoji FROM chat_sessions WHERE username=? ORDER BY last_modified DESC', (st.session_state.username,), True)
    if st.button("➕ New Session"):
        nid = str(uuid.uuid4())
        db_q('INSERT INTO chat_sessions VALUES (?,?,?,?,?)', (nid, st.session_state.username, "New Session", datetime.datetime.now().strftime("%H:%M"), "💬"))
        st.session_state.sid, st.session_state.messages = nid, []; st.rerun()
    
    if sessions:
        s_dict = {f"{s[3]} {s[1]}": s[0] for s in sessions}
        sel = st.selectbox("Timeline:", list(s_dict.keys()))
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

    # 🕵️ ADMIN VAULT
    if st.session_state.username == ADMIN:
        st.divider()
        with st.expander("🕵️ ADMIN VAULT"):
            if st.button("⚡ Sync Evolution"):
                e, pw, mo = analyze_all(st.session_state.username, st.session_state.sid)
                st.session_state.evo, st.session_state.pwr = e, pw
                st.rerun()
            
            if "pwr" in st.
