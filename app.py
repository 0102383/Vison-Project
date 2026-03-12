import streamlit as st
import sqlite3
import base64
import os

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
    return None

# --- 5. UI & CSS (SEAMLESS DARK MODE) ---
st.set_page_config(page_title="VISON AI", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .stApp, [data-testid="stAppViewContainer"], .main { background-color: #0e1117 !important; }
    [data-testid="stHeader"] { background-color: #0e1117 !important; }
    [data-testid="stBottomBlock"], [data-testid="stBottom"] > div { background-color: #0e1117 !important; }
    [data-testid="stSidebar"] { background-color: #0e1117 !important; border-right: 1px solid #1c2128 !important; }
    h1, h2, h3, h4, h5, p, span, div, label, li { color: #ffffff !important; }
    [data-testid="stChatInput"] { background-color: #1c2128 !important; border: 1px solid #a252ff !important; border-radius: 15px; }
    
    .hero-container { display: flex; justify-content: center; align-items: center; padding: 10px; animation: fadeInDown 1.5s ease-out; }
    .hero-image { max-width: 350px; border-radius: 20px; box-shadow: 0 0 25px rgba(138, 43, 226, 0.4); }
    @keyframes fadeInDown { 0% { opacity: 0; transform: translateY(-40px); } 100% { opacity: 1; transform: translateY(0); } }
    
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(162, 82, 255, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(162, 82, 255, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(162, 82, 255, 0); }
    }
    .online-indicator { display: inline-block; width: 12px; height: 12px; background-color: #a252ff; border-radius: 50%; margin-right: 8px; animation: pulse 2s infinite; }
    .main-title { font-size: 50px !important; font-weight: 800 !important; background: -webkit-linear-gradient(#a252ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-top: -15px; }
    .login-box { background-color: #1c2128; padding: 40px; border-radius: 20px; border: 2px solid #a252ff; text-align: center; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 6. SMART LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    logo_b64 = get_image_base64("vison_logo.jpg")
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
                # FIX: Auto-lowercase the username so case-sensitivity doesn't lose history
                clean_user_id = user_id.lower().strip() 
                status = manage_user(clean_user_id, user_pass)
                
                if status in ["registered", "authorized"]:
                    st.session_state.logged_in = True
                    st.session_state.username = clean_user_id
                    # FIX: Force clear the screen memory to ensure we load the database fresh
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
        # FIX: Wipes the screen memory so the next user doesn't see your chat!
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
    
    sidebar_logo = get_image_base64("vison_logo.jpg")
    if sidebar_logo:
        st.markdown(f"""<center><img src="data:image/jpeg;base64,{sidebar_logo}" style="max-width: 100px; border-radius: 10px; margin-bottom: 10px;"></center>""", unsafe_allow_html=True)
    
    st.markdown("""<div style="background: rgba(162, 82, 255, 0.1); padding: 5px; border-radius: 10px; border: 1px solid rgba(162, 82, 255, 0.3); margin-bottom: 20px; text-align: center;"><span class="online-indicator" style="background-color: #a252ff;"></span><span style="color: #a252ff; font-weight: bold;">SYSTEM ONLINE</span></div>""", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload STEM Image", type=['png', 'jpg', 'jpeg'])

st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)

if not st.session_state.messages:
    welcome = f"Systems active. How can I help you today, {st.session_state.username}?"
    st.session_state.messages = [{"role": "assistant", "content": welcome}]
    save_message(st.session_state.username, "assistant", welcome)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"] if isinstance(msg["content"], str) else msg["content"][0]["text"])

user_input = st.chat_input("Ask a question...")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)
        if uploaded_file: st.image(uploaded_file, width=300)

    if uploaded_file:
        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        content = [{"type": "text", "text": user_input}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]
        st.session_state.messages.append({"role": "user", "content": content})
        save_message(st.session_state.username, "user", f"{user_input} [Image Uploaded]")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_message(st.session_state.username, "user", user_input)

    with st.chat_message("assistant"):
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









