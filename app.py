import streamlit as st
import sqlite3
import base64
import os
# --- ⚙️ MASTER SETTINGS ⚙️ ---
# Type the EXACT name of your main vison logo file on GitHub here:
LOGO_FILENAME = "vison_logo.jpg" 
# Name of the glowing AI logo for chat avatars:
AI_AVATAR_FILENAME = "ai_logo_glow.jpg"

# --- 1. SAFE LIBRARY IMPORT ---
GROQ_AVAILABLE = False
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    st.error("🚀 **System Requirement Missing:** Please add `groq` to your `requirements.txt` file.")

# --- 2. SETUP & SECRETS ---
client = None
if GROQ_AVAILABLE:
    try:
        if "GROQ_API_KEY" in st.secrets:
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except Exception as e:
        st.error(f"Connection Error: {e}")

# --- 3. DATABASE (USER ACCOUNTS & CHAT) ---
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT)''')
    conn.commit()
    conn.close()

def manage_user(username, password):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if row is None:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        return "registered"
    elif row[0] == password:
        conn.close()
        return "authorized"
    else:
        conn.close()
        return "denied"

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
    else:
        st.error(f"⚠️ ERROR: I cannot find the file named '{image_path}' in your GitHub repository. Please check the spelling!")
        return None

# Encode the AI avatar image
ai_avatar_b64 = get_image_base64(AI_AVATAR_FILENAME)
# Default user avatar
user_avatar_icon = "👤"

# --- 5. UI & CSS (ANIMATIONS & GLOW EFFECTS) ---
st.set_page_config(page_title="VISON AI", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    /* Splash Screen Logo Animation */
    .hero-container { display: flex; justify-content: center; align-items: center; padding: 10px; animation: fadeInDown 1.5s ease-out; }
    .hero-image { max-width: 350px; border-radius: 20px; box-shadow: 0 0 25px rgba(138, 43, 226, 0.4); }
    @keyframes fadeInDown { 0% { opacity: 0; transform: translateY(-40px); } 100% { opacity: 1; transform: translateY(0); } }
    
    /* General UI Effects */
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(162, 82, 255, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(162, 82, 255, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(162, 82, 255, 0); }
    }
    .online-indicator { display: inline-block; width: 12px; height: 12px; background-color: #a252ff; border-radius: 50%; margin-right: 8px; animation: pulse 2s infinite; }
    .main-title { font-size: 50px !important; font-weight: 800 !important; background: -webkit-linear-gradient(#a252ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-top: -15px; }
    .login-box { background-color: #1c2128; padding: 40px; border-radius: 20px; border: 2px solid #a252ff; text-align: center; margin-top: 10px; }
    
    /* 🔥 CHAT INPUT BOX FIX 🔥 */
    [data-testid="stChatInput"] {
        border: 2px solid #a252ff !important;
        border-radius: 10px !important;
        background-color: #0e1117 !important;
    }
    [data-testid="stChatInput"]:focus-within {
        box-shadow: 0 0 15px rgba(162, 82, 255, 0.5) !important;
    }

    /* 🔥 CHAT BUBBLE STYLING & ALIGNMENT 🔥 */
    /* Target user messages with CSS flexbox for right-alignment */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarIcon"]):has(span[aria-label="User Avatar icon"]) {
        display: flex !important;
        justify-content: flex-end !important;
        flex-direction: row-reverse !important;
    }
    
    /* Style the user message bubble content (right-aligned) */
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) > div {
        background-color: rgba(162, 82, 255, 0.1) !important;
        border: 1px solid #a252ff !important;
        border-radius: 15px !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(162, 82, 255, 0.3) !important;
    }
    
    /* Target assistant/AI messages with flexbox for left-alignment */
    div[data-testid="stChatMessage"]:has(img[data-testid="stChatMessageAvatarImage"]) {
        display: flex !important;
        justify-content: flex-start !important;
    }

    /* Style the AI/assistant message bubble content (left-aligned) */
    div[data-testid="stChatMessage"]:has(img[data-testid="stChatMessageAvatarImage"]) > div {
        background-color: rgba(0, 114, 255, 0.1) !important;
        border: 1px solid #0072ff !important;
        border-radius: 15px !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(0, 114, 255, 0.3) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 6. SMART LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    logo_b64 = get_image_base64(LOGO_FILENAME)
    if logo_b64:
        st.markdown(f'''<div class="hero-container"><img src="data:image/jpeg;base64,{logo_b64}" class="hero-image"></div>''', unsafe_allow_html=True)
    
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.subheader("🔑 Student Gateway")
        st.write("First time? Enter a username and a new password to register.")
        
        user_id = st.text_input("Username / Email")
        user_pass = st.text_input("Password", type="password")
        
        if st.button("Unlock AI"):
            if user_id and user_pass:
                clean_user_id = user_id.lower().strip() 
                status = manage_user(clean_user_id, user_pass)
                
                if status in ["registered", "authorized"]:
                    st.session_state.logged_in = True
                    st.session_state.username = clean_user_id
                    if "messages" in st.session_state: 
                        del st.session_state.messages
                    st.rerun()
                else:
                    st.error("❌ Incorrect Password for this Username.")
            else:
                st.warning("Please fill in both fields.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 7. CHAT APP (POST-LOGIN) ---
if "messages" not in st.session_state:
    st.session_state.messages = load_memory(st.session_state.username)

with st.sidebar:
    st.markdown(f"**👤 User:** `{st.session_state.username}`")
    if st.button("Logout"):
        st.session_state.logged_in = False
        if "messages" in st.session_state: 
            del st.session_state.messages
        st.rerun()
    st.markdown("---")
    lang = st.selectbox("Language", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor"])
    if st.button("🗑️ Wipe My Memory"):
        clear_user_memory(st.session_state.username)
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    
    sidebar_logo = get_image_base64(LOGO_FILENAME)
    if sidebar_logo:
        st.markdown(f"""<center><img src="data:image/jpeg;base64,{sidebar_logo}" style="max-width: 100px; border-radius: 10px; margin-bottom: 10px;"></center>""", unsafe_allow_html=True)
    
    st.markdown("""<div style="background: rgba(162, 82, 255, 0.1); padding: 5px; border-radius: 10px; border: 1px solid rgba(162, 82, 255, 0.3); margin-bottom: 20px; text-align: center;"><span class="online-indicator" style="background-color: #a252ff;"></span><span style="color: #a252ff; font-weight: bold;">SYSTEM ONLINE</span></div>""", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload STEM Image", type=['png', 'jpg', 'jpeg'])

st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)

if not st.session_state.messages:
    welcome = f"Systems active. How can I help you today, {st.session_state.username}?"
    st.session_state.messages = [{"role": "assistant", "content": welcome}]
    save_message(st.session_state.username, "assistant", welcome)

# --- DISPLAY CHAT MESSAGES WITH CUSTOM ALIGNMENT AND AVATARS ---
for msg in st.session_state.messages:
    # Set the correct avatar base64 or icon
    current_avatar = None
    if msg["role"] == "assistant" and ai_avatar_b64:
        current_avatar = f"data:image/png;base64,{ai_avatar_b64}"
    elif msg["role"] == "user":
        current_avatar = user_avatar_icon

    with st.chat_message(msg["role"], avatar=current_avatar):
        # The CSS above will automatically align the bubbles and add glowing borders
        content = msg["content"]
        if isinstance(content, list):
            # Handle mixed text and image user input if applicable
            for item in content:
                if item["type"] == "text":
                    st.markdown(item["text"])
                elif item["type"] == "image_url":
                    # You can customize image display here
                    pass 
        else:
            # Handle text content
            st.markdown(content)

user_input = st.chat_input("Ask a question...")
if user_input:
    # Immediately add the user message to the session state for a fast UI update
    new_user_message = {"role": "user", "content": user_input}
    st.session_state.messages.append(new_user_message)
    save_message(st.session_state.username, "user", user_input)

    # Re-display user message instantly with correct right alignment and avatar
    with st.chat_message("user", avatar=user_avatar_icon):
        if uploaded_file:
            # Re-process and save image upload if present
            # img_b64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
            # ...
            # save_message(...)
            pass 
        st.markdown(user_input)

    # --- PROCESS AI RESPONSE ---
    with st.chat_message("assistant", avatar=f"data:image/png;base64,{ai_avatar_b64}" if ai_avatar_b64 else None):
        if client:
            with st.spinner("Vison processing..."):
                try:
                    sys_m = f"You are a {persona} in {lang}. Focus on STEM."
                    api_msgs = [{"role": "system", "content": sys_m}]
                    for m in st.session_state.messages:
                        clean_c = m["content"]
                        if isinstance(clean_c, list) and not uploaded_file: clean_c = clean_c[0]["text"]
                        api_msgs.append({"role": m["role"], "content": clean_c})
                    mid = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.1-8b-instant"
                    res = client.chat.completions.create(model=mid, messages=api_msgs)
                    ans = res.choices[0].message.content
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                    save_message(st.session_state.username, "assistant", ans)
                except Exception as e: st.error(f"Error: {e}")




