import streamlit as st
import sqlite3
import base64

# Safely check for the Groq library
try:
    from groq import Groq
except ImportError:
    st.error("Groq library missing! Check requirements.txt")

# 1. SETUP & SECRETS
client = None
if "GROQ_API_KEY" in st.secrets:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# 2. DATABASE (PER-USER MEMORY)
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT)''')
    conn.commit()
    conn.close()

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

init_db()

# 3. UI LAYOUT & CUSTOM CSS
st.set_page_config(page_title="VISON AI", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(51, 217, 178, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(51, 217, 178, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(51, 217, 178, 0); }
    }
    .online-indicator {
        display: inline-block; width: 12px; height: 12px;
        background-color: #33d9b2; border-radius: 50%;
        margin-right: 8px; animation: pulse 2s infinite;
    }
    .stApp { background-color: #0e1117; }
    h1, h2, h3, h4, h5, p, span, div, label, li { color: #ffffff !important; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    .main-title {
        font-size: 50px !important; font-weight: 800 !important;
        background: -webkit-linear-gradient(#00c6ff, #0072ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .login-card {
        background-color: #1c2128; padding: 30px; border-radius: 15px;
        border: 1px solid #30363d; text-align: center;
    }
    .robot-container { fill: #000000; filter: drop-shadow(0 0 8px rgba(0, 198, 255, 0.8)); margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

# 4. LOGIN LOGIC
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<p class="main-title">🚀 VISON AI LOGIN</p>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.subheader("Welcome to VISON CORE")
        user_email = st.text_input("Enter Email / Google Account ID")
        
        # Simulate "Sign in with Google" button
        if st.button("Connect with Google ID"):
            if user_email:
                st.session_state.logged_in = True
                st.session_state.username = user_email
                st.rerun()
            else:
                st.error("Please enter an email to identify your history.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop() # Prevents the rest of the app from loading until login

# --- EVERYTHING BELOW ONLY RUNS AFTER LOGIN ---

# Sidebar setup
with st.sidebar:
    st.markdown(f"👤 **Logged in as:** {st.session_state.username}")
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()
    st.markdown("---")
    st.markdown("### ⚙️ System Settings")
    lang = st.selectbox("Language", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Tutor Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor"])
    st.markdown("---")
    
    # BLACK ROBOT ICON SVG
    st.markdown("""
        <center>
        <svg class="robot-container" width="80" height="80" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A3,3 0 0,1 17,10V11H18A2,2 0 0,1 20,13V18A2,2 0 0,1 18,20H6A2,2 0 0,1 4,18V13A2,2 0 0,1 6,11H7V10A3,3 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2M7.5,13A1.5,1.5 0 0,0 6,14.5A1.5,1.5 0 0,0 7.5,16A1.5,1.5 0 0,0 9,14.5A1.5,1.5 0 0,0 7.5,13M16.5,13A1.5,1.5 0 0,0 15,14.5A1.5,1.5 0 0,0 16.5,16A1.5,1.5 0 0,0 18,14.5A1.5,1.5 0 0,0 16.5,13M12,14L10.75,17H13.25L12,14Z"/>
        </svg>
        <h3 style='margin-top:0;'>VISON CORE</h3>
        <div style="background: rgba(51, 217, 178, 0.1); padding: 5px; border-radius: 10px; border: 1px solid rgba(51, 217, 178, 0.3); margin-bottom: 20px;">
            <span class="online-indicator"></span><span style="color: #33d9b2; font-weight: bold;">SYSTEM ONLINE</span>
        </div>
        </center>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload STEM Image", type=['png', 'jpg', 'jpeg'])
    st.markdown("<br><center><p style='color:#8b949e !important;'>BIVIC 2026 PROJECT</p></center>", unsafe_allow_html=True)

# Main Title
st.markdown('<p class="main-title">🚀 VISON AI</p>', unsafe_allow_html=True)

# Load user-specific history
if "messages" not in st.session_state:
    st.session_state.messages = load_memory(st.session_state.username)
    if not st.session_state.messages:
        welcome = f"Welcome, {st.session_state.username}! I am Vison. How can I help you today?"
        st.session_state.messages = [{"role": "assistant", "content": welcome}]
        save_message(st.session_state.username, "assistant", welcome)

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"] if isinstance(msg["content"], str) else msg["content"][0]["text"])

# Interaction
user_input = st.chat_input("Ask Vison anything...")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)
        if uploaded_file: st.image(uploaded_file, width=300)

    if uploaded_file:
        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        user_content = [{"type": "text", "text": user_input}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]
        st.session_state.messages.append({"role": "user", "content": user_content})
        save_message(st.session_state.username, "user", f"{user_input} [Image Uploaded]")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_message(st.session_state.username, "user", user_input)

    with st.chat_message("assistant"):
        if client:
            with st.spinner("Processing..."):
                try:
                    sys_p = f"You are a {persona} in {lang}. Focus on STEM."
                    api_msgs = [{"role": "system", "content": sys_p}]
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
                except Exception as e:
                    st.error(f"Error: {e}")










