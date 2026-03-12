import streamlit as st
import sqlite3, base64, os, time, uuid, datetime
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
        c.execute(q, d); res = c.fetchall() if fetch else None
        conn.commit(); return res
    finally: conn.close()

def init_db():
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT, mood_emoji TEXT DEFAULT '💬')''')

# --- PART 3: SCIENTIFIC TOOLS (GRAPHER) ---
def simple_plot(equation_str):
    try:
        x = np.linspace(-10, 10, 400)
        # Clean string for python logic
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

# --- PART 4: UI HELPERS ---
def get_mood_color(emoji):
    mood_map = {"🧠": "#00d4ff", "⚠️": "#ff4b4b", "🔥": "#ffaa00", "✅": "#00ff88", "💬": "#a252ff"}
    return mood_map.get(emoji, "#a252ff")

# --- APP START ---
st.set_page_config(page_title="VISON AI STEM", layout="wide")
init_db()

# Persistence for Mood Ring
current_mood = "💬"
if 'sid' in st.session_state:
    res = db_q('SELECT mood_emoji FROM chat_sessions WHERE session_id=?', (st.session_state.sid,), True)
    if res: current_mood = res[0][0]
mood_color = get_mood_color(current_mood)

st.markdown(f"""
    <style>
    .mood-ring {{ height: 4px; width: 100%; background: linear-gradient(90deg, transparent, {mood_color}, transparent); box-shadow: 0px 4px 12px {mood_color}; margin-bottom: 20px; }}
    .main-title {{ font-size: 45px !important; font-weight: 800; background: linear-gradient({mood_color}, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }}
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) {{ flex-direction: row-reverse !important; }}
    </style>
    <div class="mood-ring"></div>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    lb = get_64(LOGO_FILENAME)
    if lb: st.markdown(f'<center><img src="data:image/jpeg;base64,{lb}" width="180"></center>', unsafe_allow_html=True)
    u, p = st.text_input("User ID"), st.text_input("Key", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_q('INSERT INTO users (username, password, interests, level) VALUES (?,?,?,?)', (u.lower(), p, "STEM", "HS"))
        if not res or res[0][0] == p: st.session_state.logged_in, st.session_state.username = True, u.lower(); st.rerun()
    st.stop()

# --- SIDEBAR: PRODUCTIVITY TOOLS ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    st.divider()
    
    # 🧠 MEMORY BUTTON
    if st.button("🗑️ Clear Memory"):
        db_q('DELETE FROM chat_log WHERE session_id=?', (st.session_state.sid,))
        st.session_state.messages = []
        st.success("Session Memory Wiped")
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
        sel = st.selectbox("History:", list(s_dict.keys()))
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

# --- MAIN CHAT ---
st.markdown('<p class="main-title">🚀 VISON AI STEM CORE</p>', unsafe_allow_html=True)

ai_av = f"data:image/png;base64,{get_64(AI_AVATAR_FILENAME)}" if get_64(AI_AVATAR_FILENAME) else "🤖"
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): 
        st.markdown(m["content"])

user_in = st.chat_input("Evolve your thinking...")

# Auto-Trigger Quiz via button
if st.session_state.get('pending_quiz'):
    user_in = "Generate a 3-question STEM quiz based on our conversation. Use LaTeX."
    st.session_state.pending_quiz = False

if user_in or uploaded_file:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    # Graphing Logic
    if user_in and "plot" in user_in.lower():
        eq = user_in.lower().split("plot")[-1].strip().replace("$", "")
        fig = simple_plot(eq)
        if fig: st.pyplot(fig)

    # Standard Chat / Vision
    model_to_use = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.3-70b-versatile"
    display_text = user_in if user_in else "Analyze this image."
    
    if uploaded_file:
        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode()
        image_payload = [{"type": "text", "text": display_text}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]
        with st.chat_message("user", avatar="👤"): st.image(uploaded_file, width=300); st.markdown(display_text)
        content_payload = image_payload
    else:
        with st.chat_message("user", avatar="👤"): st.markdown(user_in)
        content_payload = display_text

    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", display_text, st.session_state.sid))
    st.session_state.messages.append({"role": "user", "content": display_text})

    with st.chat_message("assistant", avatar=ai_av):
        mem = db_q('SELECT secret_profile FROM users WHERE username=?', (st.session_state.username,), True)
        profile = mem[0][0] if mem else "New Student"
        sys_prompt = f"You are a {persona} fluent in {lang}. Use LaTeX ($) for all math. Context: {profile}"
        
        res = client.chat.completions.create(
            model=model_to_use,
            messages=[{"role": "system", "content": sys_prompt}] + st.session_state.messages[-8:] + [{"role": "user", "content": content_payload}]
        )
        ans = res.choices[0].message.content
        st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))

components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)

