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
ADMIN_USERNAME = "0102383" # 👑 ONLY THIS USERNAME CAN SEE THE SECRET DATA!

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
    
    # 🕵️‍♂️ Adding the new secret vault column
    try: c.execute("ALTER TABLE users ADD COLUMN interests TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN level TEXT")
    except: pass
    try: c.execute("ALTER TABLE chat_log ADD COLUMN session_id TEXT DEFAULT 'default'")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN secret_profile TEXT DEFAULT 'No data yet.'")
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

def save_secret_profile(u, secret_text):
    conn = sqlite3.connect('vison_user_data.db')
    conn.cursor().execute('UPDATE users SET secret_profile=? WHERE username=?', (secret_text, u))
    conn.commit()
    conn.close()

def get_profile(u):
    conn = sqlite3.connect('vison_user_data.db')
    res = conn.cursor().execute('SELECT interests, level, secret_profile FROM users WHERE username=?', (u,)).fetchone()
    conn.close()
    if res:
        secret = res[2] if len(res) > 2 and res[2] else "No data yet."
        return {"interests": res[0] or "STEM", "level": res[1] or "High School", "secret": secret}
    return {"interests": "STEM", "level": "High School", "secret": "No data yet."}

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

def get_all_users_data():
    conn = sqlite3.connect('vison_user_data.db')
    data = conn.cursor().execute('SELECT username, interests, secret_profile FROM users').fetchall()
    conn.close()
    return data

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
if 'logged_in' not in st.session_state: 
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    logo_b64 = get_image_base64(LOGO_FILENAME)
    if logo_b64: 
        st.markdown(f'<center><img src="data:image/jpeg;base64,{logo_b64}" width="300"></center>', unsafe_allow_html=True)
    
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
    if db_sessions:
        st.session_state.current_session = db_sessions[-1]
    else:
        st.session_state.current_session = str(uuid.uuid4())

if st.session_state.current_session not in db_sessions:
    db_sessions.append(st.session_state.current_session)

def format_session_name(s_id):
    if s_id in session_names:
        return session_names[s_id]
    return f"Chat ({s_id[:6]})" 

if "last_learn_time" not in st.session_state:
    st.session_state.last_learn_time = time.time()

# 🧠 THE EMOTIONAL AUTO-BRAIN
if time.time() - st.session_state.last_learn_time > 3600:  
    if client and "messages" in st.session_state and len(st.session_state.messages) > 2:
        try:
            recent_texts = [m["content"] for m in st.session_state.messages if m["role"] == "user"][-8:]
            joined_texts = ' | '.join(recent_texts)
            
            prompt_topics = f"Based on these messages, what is this student studying? Return ONLY 3-4 comma-separated keywords: {joined_texts}"
            res_topics = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt_topics}])
            inferred_interests = res_topics.choices[0].message.content.replace('"', '').strip()
            
            prompt_emotion = (
                f"Read these messages from a student: {joined_texts}. "
                f"Analyze their psychological state and learning style. Are they frustrated? Confident? "
                f"Do they struggle with specific concepts? Write a short 2-sentence psychological profile."
            )
            res_emotion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt_emotion}])
            inferred_emotion = res_emotion.choices[0].message.content.strip()
            
            old_prof = get_profile(st.session_state.username)
            save_profile(st.session_state.username, inferred_interests, old_prof["level"])
            save_secret_profile(st.session_state.username, inferred_emotion)
            
            st.toast("🧠 VISON automatically learned from your last hour of study!")
        except: 
            pass
    st.session_state.last_learn_time = time.time()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    
    # 🚪 LOGOUT BUTTON ADDED HERE
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear() # Clears session data safely
        st.rerun()
        
    st.markdown("---")
    
    st.subheader("📁 Chat History")
    if st.button("➕ New Chat"):
        st.session_state.current_session = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.quiz_mode = False
        st.rerun()
        
    reversed_sessions = db_sessions[::-1]
    selected_session = st.selectbox(
        "Jump to past chat:", 
        reversed_sessions, 
        format_func=format_session_name,
        index=reversed_sessions.index(st.session_state.current_session)
    )
    
    if selected_session != st.session_state.current_session:
        st.session_state.current_session = selected_session
        st.session_state.messages = load_memory(st.session_state.username, selected_session)
        st.session_state.quiz_mode = False
        st.rerun()
        
    with st.expander("✏️ Rename Current Chat"):
        current_display_name = format_session_name(st.session_state.current_session)
        new_name_input = st.text_input("New Name", value=current_display_name, label_visibility="collapsed")
        if st.button("💾 Save Name", use_container_width=True):
            conn = sqlite3.connect('vison_user_data.db')
            conn.cursor().execute('INSERT OR REPLACE INTO chat_sessions (session_id, username, session_name) VALUES (?, ?, ?)', (st.session_state.current_session, st.session_state.username, new_name_input))
            conn.commit()
            conn.close()
            st.success("Renamed!")
            time.sleep(0.5)
            st.rerun()
            
    st.markdown("---")
    
    st.subheader("📝 Quick Quiz")
    with st.expander("Setup & Start Quiz"):
        quiz_country = st.text_input("Country", value="Malaysia") 
        quiz_school = st.text_input("School Name (Optional)", placeholder="e.g., SMK...")
        quiz_grade = st.selectbox("Grade / Form", ["Form 1", "Form 2", "Form 3", "Form 4", "Form 5", "Primary School", "College / University"])
        
        st.markdown("---")
        
        quiz_subject = st.text_input("Subject", value="Math & STEM")
        quiz_difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard", "Expert"])
        quiz_questions = st.number_input("Number of Questions", min_value=1, max_value=20, value=3)
        quiz_timer = st.number_input("Seconds per Question", min_value=10, max_value=300, value=30)
        
        if st.button("🚀 Start Quiz!", use_container_width=True):
            school_context = f" at {quiz_school}" if quiz_school else ""
            st.session_state.quiz_mode = True
            st.session_state.quiz_time_limit = quiz_timer
            st.session_state.pending_prompt = (
                f"I want to test my knowledge! I am a student in {quiz_country}{school_context}, "
                f"currently in {quiz_grade}. Please generate a {quiz_difficulty} difficulty, "
                f"{quiz_questions}-question multiple choice quiz on the subject of '{quiz_subject}'. "
                f"Ask me the questions ONE by ONE. Wait for me to answer each question before "
                f"revealing if I am correct and moving to the next one. "
                f"IMPORTANT: I have exactly {quiz_timer} seconds to answer each question. "
                f"Let me know if I am too slow!"
            )
            st.rerun()
# --- 7. MAIN CHAT INTERFACE ---
st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = load_memory(st.session_state.username, st.session_state.current_session)

for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        display_avatar = f"data:image/jpeg;base64,{ai_avatar_b64}" if ai_avatar_b64 else "🤖"
    else:
        display_avatar = "👤"
        
    with st.chat_message(msg["role"], avatar=display_avatar):
        st.markdown(msg["content"])

st.markdown("---")

uploaded_file = st.file_uploader("➕ Add Image / Equation", type=['png', 'jpg', 'jpeg'], key="vison_uploader_main")

user_input = st.chat_input("Ask Vison anything...")

if st.session_state.get("pending_prompt"):
    user_input = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_input:
    time_note_for_ai = ""
    display_time = None
    
    if st.session_state.get("quiz_mode") and "last_ai_time" in st.session_state:
        elapsed_time = int(time.time() - st.session_state.last_ai_time)
        limit = st.session_state.get("quiz_time_limit", 30)
        display_time = f"⏱️ Time taken: {elapsed_time}s / {limit}s"
        
        if elapsed_time > limit:
            time_note_for_ai = f"\n\n[System Alert to AI: The student took {elapsed_time} seconds. The limit was {limit} seconds. They FAILED the time limit! Tell them!]"
        else:
            time_note_for_ai = f"\n\n[System Alert to AI: The student answered in {elapsed_time} seconds. Fast enough!]"

    st.session_state.messages.append({"role": "user", "content": user_input})
    save_message(st.session_state.username, "user", user_input, st.session_state.current_session)
    
    with st.chat_message("user", avatar="👤"): 
        st.markdown(user_input)
        if display_time:
            st.caption(display_time)

    with st.chat_message("assistant", avatar=f"data:image/jpeg;base64,{ai_avatar_b64}" if ai_avatar_b64 else "🤖"):
        if client:
            try:
                # 🛠️ HERE IS THE UPDATED VISION MODEL LINE!
                model_id = "llama-3.2-11b-vision-instruct" if uploaded_file else "llama-3.3-70b-versatile"
                
                math_text = "IMPORTANT: Use LaTeX (enclosed in $$) for all math." if math_mode else ""
                
                # Fetch their secret profile so the AI knows how they are feeling right now!
                secret_context = f"Student Profile Note: {profile['secret']}" if profile['secret'] != "No data yet." else ""
                
                sys_m = f"You are {persona} in {lang}. Level: {new_level}. Interests: {new_ints}. {secret_context} {math_text}"
                
                messages_for_ai = st.session_state.messages.copy()
                if time_note_for_ai:
                    messages_for_ai[-1] = {"role": "user", "content": user_input + time_note_for_ai}
                
                res = client.chat.completions.create(
                    model=model_id, 
                    messages=[{"role": "system", "content": sys_m}] + messages_for_ai
                )
                ans = res.choices[0].message.content
                st.markdown(ans)
                
                tokens = res.usage.total_tokens
                st.caption(f"⚙️ **Model:** {model_id} | 🧠 **Tokens:** {tokens}")
                
                st.session_state.last_ai_time = time.time()
                
                st.session_state.messages.append({"role": "assistant", "content": ans})
                save_message(st.session_state.username, "assistant", ans, st.session_state.current_session)
            
            except Exception as e:
                st.error(f"Error: {e}")

# --- 8. AUTO-SCROLL TO BOTTOM JAVASCRIPT ---
components.html(
    """
    <script>
        function scrollToBottom() {
            var chatElements = window.parent.document.querySelectorAll('.stChatMessage');
            if (chatElements.length > 0) {
                chatElements[chatElements.length - 1].scrollIntoView({ behavior: 'smooth' });
            }
        }
        setTimeout(scrollToBottom, 300);
    </script>
    """,
    height=0,
)

