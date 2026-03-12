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

# --- PART 3: POMODORO TIMER ---
def study_timer():
    st.subheader("⏱️ Focus Timer")
    t_min = st.number_input("Minutes:", min_value=1, value=25)
    if st.button("Start Timer"):
        placeholder = st.empty()
        for i in range(t_min * 60, 0, -1):
            mins, secs = divmod(i, 60)
            placeholder.metric("Time Remaining", f"{mins:02d}:{secs:02d}")
            time.sleep(1)
        st.success("Time's up! Take a break.")
        st.balloons()

# --- PART 4: APP START ---
st.set_page_config(page_title="VISON AI", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    # ... (Standard Gateway Logic)
    u, p = st.text_input("User ID"), st.text_input("Key", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_q('INSERT INTO users (username, password, interests, level) VALUES (?,?,?,?)', (u.lower(), p, "STEM", "HS"))
        st.session_state.logged_in, st.session_state.username = True, u.lower(); st.rerun()
    st.stop()

# --- PART 5: SIDEBAR (THE NEW TOOLSET) ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    
    # 🧠 MEMORY BUTTON
    if st.button("🗑️ Wipe Session Memory"):
        db_q('DELETE FROM chat_log WHERE session_id=?', (st.session_state.sid,))
        st.session_state.messages = []
        st.success("Memory cleared!")
        st.rerun()

    st.divider()
    
    # 📝 QUIZ BUTTON
    if st.button("🧩 Generate STEM Quiz"):
        st.session_state.quiz_mode = True
        # We trigger this via a specific chat message to the AI
        user_in = "GENERATE_STEM_QUIZ" 
    
    st.divider()
    
    # ⏱️ TIMER BUTTON (Expander)
    with st.expander("⏱️ Study Timer"):
        study_timer()

    st.divider()
    persona = st.selectbox("Persona", ["Strict Professor", "Friendly Mentor", "Quirky Scientist"])
    uploaded_file = st.file_uploader("📷 Solve STEM Image", type=['png', 'jpg', 'jpeg'])

# --- PART 6: CHAT CORE ---
st.markdown("<h1 style='text-align: center; color: #a252ff;'>🚀 VISON AI CORE</h1>", unsafe_allow_html=True)

if 'sid' not in st.session_state: st.session_state.sid = str(uuid.uuid4())
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

ai_av = f"data:image/jpeg;base64,{get_64(AVATAR)}" if get_64(AVATAR) else "🤖"

for m in st.session_state.messages: 
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): 
        st.markdown(m["content"])

user_in = st.chat_input("Continue evolution...")

# Handle Quiz Trigger
if 'quiz_mode' in st.session_state and st.session_state.quiz_mode:
    user_in = "Please give me a short, challenging 3-question STEM quiz based on our recent topics. Use LaTeX for equations."
    st.session_state.quiz_mode = False

if user_in or uploaded_file:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    model = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.3-70b-versatile"
    payload = user_in
    if uploaded_file:
        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode()
        payload = [{"type": "text", "text": user_in if user_in else "Solve this."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]

    with st.chat_message("user", avatar="👤"): st.markdown(user_in if user_in else "Image Upload")
    
    # AI Response
    with st.chat_message("assistant", avatar=ai_av):
        sys = f"You are a {persona}. Use LaTeX. Reference memory."
        res = client.chat.completions.create(model=model, messages=[{"role": "system", "content": sys}] + st.session_state.messages[-10:] + [{"role":"user", "content": payload}])
        ans = res.choices[0].message.content
        st.markdown(ans)
        
    # Save & Update
    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", user_in if user_in else "Image", st.session_state.sid))
    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))
    st.session_state.messages.append({"role": "user", "content": user_in if user_in else "Image"})
    st.session_state.messages.append({"role": "assistant", "content": ans})
