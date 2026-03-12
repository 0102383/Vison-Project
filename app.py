import streamlit as st
import sqlite3
import base64
import os
import time
import uuid
import streamlit.components.v1 as components
from fpdf import FPDF

# --- ⚙️ MASTER SETTINGS ⚙️ ---
LOGO_FILENAME = "vison_logo.jpg.png" 
AI_AVATAR_FILENAME = "image_3b899c.jpg" # Make sure this matches your exact file name!

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
    # 🆕 NEW TABLE: This stores your custom chat names!
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

# Get all session IDs
c.execute('SELECT DISTINCT session_id FROM chat_log WHERE username=?', (st.session_state.username,))
db_sessions = [row[0] for row in c.fetchall() if row[0] is not None]

# Get custom session names
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

# Format function to make the dropdown look pretty!
def format_session_name(s_id):
    if s_id in session_names:
        return session_names[s_id]
    return f"Chat ({s_id[:6]})" # Shows a short ID if no name is set

# The 1-Hour Auto-Brain
if "last_learn_time" not in st.session_state:
    st.session_state.last_learn_time = time.time()

if time.time() - st.session_state.last_learn_time > 3600:
    if client and "messages" in st.session_state and len(st.session_state.messages) > 2:
        try:
            recent_texts = [m["content"] for m in st.session_state.messages if m["role"] == "user"][-5:]
            prompt = f"Based on these messages, what is this student studying? Return ONLY 3-4 comma-separated keywords: {' | '.join(recent_texts)}"
            res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
            inferred_interests = res.choices[0].message.content.replace('"', '').strip()
            
            old_prof = get_profile(st.session_state.username)
            save_profile(st.session_state.username, inferred_interests, old_prof["level"])
            st.toast("🧠 VISON automatically learned from your last hour of study!")
        except: pass
    st.session_state.last_learn_time = time.time()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    
    st.subheader("📁 Chat History")
    if st.button("➕ New Chat"):
        st.session_state.current_session = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
        
    # The Dropdown with pretty names
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
        st.rerun()
        
    # 🆕 RENAME CHAT TOOL
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
    st.subheader("⏱️ Focus Timer")
    minutes = st.number_input("Set Minutes", min_value=1, max_value=60, value=25)
    if st.button("Start Session"):
        ph = st.empty()
        for i in range(minutes * 60, 0, -1):
            mins, secs = divmod(i, 60)
            ph.metric("Time Left", f"{mins:02d}:{secs:02d}")
            time.sleep(1)
        st.balloons()
        st.success("Session Complete! Take a break.")
    
    st.markdown("---")
    math_mode = st.toggle("📐 Math Mode", value=True)
    
    profile = get_profile(st.session_state.username)
    new_ints = st.text_area("🧠 Interests", value=profile["interests"])
    levels = ["Primary School", "High School", "University"]
    new_level = st.selectbox("🎓 Level", levels, index=levels.index(profile["level"]) if profile["level"] in levels else 1)
    
    if st.button("Update Memory"):
        save_profile(st.session_state.username, new_ints, new_level)
        st.success("Learned! 🚀")
    
    persona = st.selectbox("Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor", "Casual Chat Buddy"])
    lang = st.selectbox("Language", ["English", "Bahasa Melayu", "Japanese"])

    if st.button("📄 Download PDF"):
        pdf_bytes = create_pdf(load_memory(st.session_state.username, st.session_state.current_session))
        st.download_button("📥 Save Notes", pdf_bytes, "vison_notes.pdf", mime="application/pdf")

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

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_message(st.session_state.username, "user", user_input, st.session_state.current_session)
    with st.chat_message("user", avatar="👤"): 
        st.markdown(user_input)

    with st.chat_message("assistant", avatar=f"data:image/jpeg;base64,{ai_avatar_b64}" if ai_avatar_b64 else "🤖"):
        if client:
            try:
                model_id = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.3-70b-versatile"
                math_text = "IMPORTANT: Use LaTeX (enclosed in $$) for all math." if math_mode else ""
                sys_m = f"You are {persona} in {lang}. Level: {new_level}. Interests: {new_ints}. {math_text}"
                
                res = client.chat.completions.create(
                    model=model_id, 
                    messages=[{"role": "system", "content": sys_m}] + st.session_state.messages
                )
                ans = res.choices[0].message.content
                st.markdown(ans)
                
                tokens = res.usage.total_tokens
                st.caption(f"⚙️ **Model:** {model_id} | 🧠 **Tokens:** {tokens}")
                
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
