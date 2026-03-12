import streamlit as st
import sqlite3, base64, os, time, uuid, datetime
import matplotlib.pyplot as plt
import numpy as np
from groq import Groq

# --- PART 1: SETTINGS ---
LOGO, AVATAR, ADMIN = "vison_logo.jpg", "ai_logo_glow.jpg", "0102383"

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

# --- PART 3: SCIENTIFIC TOOLS ---
def simple_plot(equation_str):
    try:
        x = np.linspace(-10, 10, 400)
        # Replacing ^ with ** for Python power logic
        safe_eq = equation_str.replace('^', '**').replace('sin', 'np.sin').replace('cos', 'np.cos')
        y = eval(safe_eq)
        fig, ax = plt.subplots()
        ax.plot(x, y, color='#a252ff', linewidth=2)
        ax.axhline(0, color='white', linewidth=0.5)
        ax.axvline(0, color='white', linewidth=0.5)
        ax.set_facecolor('#0e1117')
        fig.patch.set_facecolor('#0e1117')
        ax.tick_params(colors='white')
        return fig
    except: return None

# --- PART 4: SIDEBAR & TOOLS ---
st.set_page_config(page_title="VISON AI", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    u, p = st.text_input("User ID"), st.text_input("Key", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_q('INSERT INTO users (username, password, interests, level) VALUES (?,?,?,?)', (u.lower(), p, "STEM", "HS"))
        st.session_state.logged_in, st.session_state.username = True, u.lower(); st.rerun()
    st.stop()

with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    
    # 🧠 MEMORY BUTTON
    if st.button("🗑️ Clear Session Memory"):
        db_q('DELETE FROM chat_log WHERE session_id=?', (st.session_state.sid,))
        st.session_state.messages = []
        st.rerun()

    # 📝 QUIZ BUTTON
    if st.button("🧩 Start STEM Quiz"):
        st.session_state.pending_quiz = True

    # ⏱️ TIMER BUTTON
    with st.expander("⏱️ Focus Timer"):
        t_min = st.number_input("Set Minutes:", 1, 120, 25)
        if st.button("Start"):
            ph = st.empty()
            for i in range(t_min * 60, 0, -1):
                m, s = divmod(i, 60)
                ph.metric("Focusing...", f"{m:02d}:{s:02d}")
                time.sleep(1)
            st.success("Session Complete!")

    st.divider()
    persona = st.selectbox("Persona", ["Strict Professor", "Friendly Mentor"])
    uploaded_file = st.file_uploader("📷 Solve STEM Image", type=['png', 'jpg', 'jpeg'])

# --- PART 5: CHAT INTERFACE ---
st.markdown("<h1 style='text-align: center; color: #a252ff;'>🚀 VISON AI CORE</h1>", unsafe_allow_html=True)

if 'sid' not in st.session_state: st.session_state.sid = str(uuid.uuid4())
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

ai_av = f"data:image/jpeg;base64,{get_64(AVATAR)}" if get_64(AVATAR) else "🤖"

for m in st.session_state.messages: 
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): 
        st.markdown(m["content"])

user_in = st.chat_input("Evolve your thinking...")

# Auto-Trigger Quiz
if st.session_state.get('pending_quiz'):
    user_in = "Generate a 3-question STEM quiz based on our chat history. Use LaTeX."
    st.session_state.pending_quiz = False

if user_in or uploaded_file:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    # Check for Plotting
    if user_in and "plot" in user_in.lower():
        eq = user_in.lower().split("plot")[-1].strip()
        fig = simple_plot(eq)
        if fig: st.pyplot(fig)

    model = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.3-70b-versatile"
    payload = user_in
    if uploaded_file:
        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode()
        payload = [{"type": "text", "text": user_in if user_in else "Solve."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]

    with st.chat_message("user", avatar="👤"): st.markdown(user_in if user_in else "Image Uploaded")
    
    with st.chat_message("assistant", avatar=ai_av):
        sys = f"You are a {persona}. Use LaTeX ($) for all math. Reference previous session context."
        res = client.chat.completions.create(model=model, messages=[{"role": "system", "content": sys}] + st.session_state.messages[-8:] + [{"role":"user", "content": payload}])
        ans = res.choices[0].message.content
        st.markdown(ans)
        
    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", user_in if user_in else "Image", st.session_state.sid))
    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))
    st.session_state.messages.append({"role": "user", "content": user_in if user_in else "Image"})
    st.session_state.messages.append({"role": "assistant", "content": ans})
