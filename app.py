import streamlit as st
import sqlite3
import base64
import os

# --- ⚙️ MASTER SETTINGS ⚙️ ---
LOGO_FILENAME = "vison_logo.jpg" 
AI_AVATAR_FILENAME = "ai_logo_glow.jpg"

# --- 1. SAFE LIBRARY IMPORT ---
GROQ_AVAILABLE = False
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    st.error("🚀 **System Requirement:** Please add `groq` to your `requirements.txt` file.")

# --- 2. SETUP & SECRETS ---
client = None
if GROQ_AVAILABLE:
    try:
        if "GROQ_API_KEY" in st.secrets:
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except Exception as e:
        st.error(f"Connection Error: {e}")

# --- 3. DATABASE (UPGRADED FOR PROFILE LEARNING) ---
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT)''')
    # Update older databases to include new columns if they are missing
    try:
        c.execute("ALTER TABLE users ADD COLUMN interests TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN level TEXT")
    except: pass
    conn.commit()
    conn.close()

def manage_user(username, password):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if row is None:
        c.execute('INSERT INTO users (username, password, interests, level) VALUES (?, ?, ?, ?)', 
                  (username, password, "", "High School"))
        conn.commit()
        conn.close()
        return "registered"
    elif row[0] == password:
        conn.close()
        return "authorized"
    else:
        conn.close()
        return "denied"

def save_profile(username, interests, level):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('UPDATE users SET interests=?, level=? WHERE username=?', (interests, level, username))
    conn.commit()
    conn.close()

def get_profile(username):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT interests, level FROM users WHERE username=?', (username,))
    res = c.fetchone()
    conn.close()
    if res:
        return {"interests": res[0] or "General STEM", "level": res[1] or "High School"}
    return {"interests": "General STEM", "level": "High School"}

def save_message(username, role, content):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO chat_log (username, role, content) VALUES (?, ?, ?)', (username, role, content))
    conn.commit()
    conn.close()

def load_memory(username):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT role, content FROM chat_log WHERE username=? ORDER BY id ASC', (username,))
    data = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in data]

def clear_user_memory(username):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM chat_log WHERE username=?', (username,))
    conn.commit()
    conn.close()

init_db()

# --- 4. IMAGE ENCODER FUNCTION ---
def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    return None

ai_avatar_b64 = get_image_base64(AI_AVATAR_FILENAME)

# --- 5. UI & CSS (NEON THEME) ---
st.set_page_config(page_title="VISON AI", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 50px !important; font-weight: 800 !important; background: -webkit-linear-gradient(#a252ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }
    .login-box { background-color: #1c2128; padding: 40px; border-radius: 20px; border: 2px solid #a252ff; text-align: center; }
    [data-testid="stChatInput"] { border: 2px solid #a252ff !important; border-radius: 10px !important; background-color: #0e1117 !important; }
    
    /* Chat Bubble Alignment */
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) { flex-direction: row-reverse !important; text-align: right !important; }
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) > div { background-color: rgba(162, 82, 255, 0.1) !important; border: 1px solid #a252ff !important; border-radius: 15px !important; }
    div[data-testid="stChatMessage"]:has(img[data-testid="stChatMessageAvatarImage"]) > div { background-color: rgba(0, 114, 255, 0.1) !important; border: 1px solid #0072ff !important; border-radius: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 6. LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    logo_b64 = get_image_base64(LOGO_FILENAME)
    if logo_b64:
        st.markdown(f'''<center><img src="data:image/jpeg;base64,{logo_b64}" style="max-width:350px; border-radius:20px;"></center>''', unsafe_allow_html=True)
    
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        user_id = st.text_input("Username")
        user_pass = st.text_input("Password", type="password")
        if st.button("Unlock AI"):
            if user_id and user_pass:
                clean_id = user_id.lower().strip()
                if manage_user(clean_id, user_pass) in ["registered", "authorized"]:
                    st.session_state.logged_in = True
                    st.session_state.username = clean_id
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 7. SIDEBAR (PROFILE & SETTINGS) ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    
    # LEARNING PROFILE
    profile = get_profile(st.session_state.username)
    new_ints = st.text_area("🧠 My Interests", value=profile["interests"])
    
    # EDUCATION LEVEL SELECTOR
    levels = ["Primary School", "High School", "University / Professional"]
    current_level_idx = levels.index(profile["level"]) if profile["level"] in levels else 1
    new_level = st.selectbox("🎓 Education Level", levels, index=current_level_idx)
    
    if st.button("Update Memory"):
        save_profile(st.session_state.username, new_ints, new_level)
        st.success("Profile learned! 🚀")
    
    st.markdown("---")
    lang = st.selectbox("Language", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor", "Casual Chat Buddy"])
    
    if st.button("🗑️ Wipe Chat History"):
        clear_user_memory(st.session_state.username)
        st.session_state.messages = []
        st.rerun()

st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)

# --- 8. CHAT LOGIC ---
# --- 8. CHAT LOGIC (WITH MAIN SCREEN UPLOADER) ---
if "messages" not in st.session_state:
    st.session_state.messages = load_memory(st.session_state.username)

# Display history
for msg in st.session_state.messages:
    avatar = f"data:image/png;base64,{ai_avatar_b64}" if msg["role"] == "assistant" and ai_avatar_b64 else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# --- THE "PLUS" UPLOADER AREA ---
# We place this right above the chat input
st.markdown("---")
uploaded_file = st.file_uploader("➕ Add Image / Equation", type=['png', 'jpg', 'jpeg'], help="Upload a photo of your math equation here!")

user_input = st.chat_input("Ask Vison anything...")

if user_input:
    # Handle Image Upload if present
    if uploaded_file:
        # Convert image to base64 for the AI to 'see' it
        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        user_content = [
            {"type": "text", "text": user_input},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
        ]
        # Display the image in the chat
        with st.chat_message("user", avatar="👤"):
            st.image(uploaded_file, width=300)
            st.markdown(user_input)
        
        save_message(st.session_state.username, "user", f"{user_input} [Image Uploaded]")
    else:
        user_content = user_input
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        save_message(st.session_state.username, "user", user_input)

    st.session_state.messages.append({"role": "user", "content": user_content})

    # AI Response
    with st.chat_message("assistant", avatar=f"data:image/png;base64,{ai_avatar_b64}" if ai_avatar_b64 else None):
        if client:
            user_prof = get_profile(st.session_state.username)
            with st.spinner("Analyzing equation..."):
                try:
                    # Switch to vision model if image is uploaded
                    model_id = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.1-8b-instant"
                    
                    sys_m = f"You are {persona} in {lang}. User level: {user_prof['level']}. Interests: {user_prof['interests']}. If an image is provided, solve the equation step-by-step."
                    
                    api_msgs = [{"role": "system", "content": sys_m}]
                    # We need to format the history correctly for the vision model
                    for m in st.session_state.messages:
                        api_msgs.append({"role": m["role"], "content": m["content"]})

                    res = client.chat.completions.create(model=model_id, messages=api_msgs)
                    ans = res.choices[0].message.content
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                    save_message(st.session_state.username, "assistant", ans)
                except Exception as e:
                    st.error(f"Error: {e}")




