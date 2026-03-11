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
try:
    if "GROQ_API_KEY" in st.secrets:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    else:
        st.warning("⚠️ The GROQ_API_KEY is missing from the Settings -> Secrets menu!")
except Exception as e:
    st.error(f"Key Error: Details: {e}")

# 2. DATABASE (LONG-TERM MEMORY)
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)''')
    conn.commit()
    conn.close()

def save_message(role, content):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO chat_log (role, content) VALUES (?, ?)', (role, content))
    conn.commit()
    conn.close()

def load_memory():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT role, content FROM chat_log ORDER BY id ASC')
    data = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in data]

def clear_memory():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM chat_log')
    conn.commit()
    conn.close()

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
    [data-testid="stChatMessageAssistant"] {
        border-left: 4px solid #00c6ff; background-color: #1c2128 !important; border-radius: 10px;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        color: white !important; background-color: #0e1117 !important;
    }
    .robot-container { fill: #000000; filter: drop-shadow(0 0 8px rgba(0, 198, 255, 0.8)); margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🚀 VISON AI</p>', unsafe_allow_html=True)
st.markdown("##### *The Future of STEM Learning*")
st.markdown("---")

# SIDEBAR
with st.sidebar:
    st.markdown("### ⚙️ System Settings")
    lang = st.selectbox("Language / Bahasa", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Tutor Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor"])
    
    if st.button("🗑️ Clear Long-Term Memory"):
        clear_memory()
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("""
        <center>
        <svg class="robot-container" width="100" height="100" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A3,3 0 0,1 17,10V11H18A2,2 0 0,1 20,13V18A2,2 0 0,1 18,20H6A2,2 0 0,1 4,18V13A2,2 0 0,1 6,11H7V10A3,3 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2M7.5,13A1.5,1.5 0 0,0 6,14.5A1.5,1.5 0 0,0 7.5,16A1.5,1.5 0 0,0 9,14.5A1.5,1.5 0 0,0 7.5,13M16.5,13A1.5,1.5 0 0,0 15,14.5A1.5,1.5 0 0,0 16.5,16A1.5,1.5 0 0,0 18,14.5A1.5,1.5 0 0,0 16.5,13M12,14L10.75,17H13.25L12,14Z"/>
        </svg>
        <h3 style='margin-top:0;'>VISON CORE</h3>
        </center>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background: rgba(51, 217, 178, 0.1); padding: 10px; border-radius: 10px; border: 1px solid rgba(51, 217, 178, 0.3); text-align: center; margin-bottom: 20px;">
            <span class="online-indicator"></span>
            <span style="color: #33d9b2; font-weight: bold; font-family: monospace;">SYSTEM ONLINE</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.header("🔍 Image Scanner")
    uploaded_file = st.file_uploader("Upload Math/Science Problem", type=['png', 'jpg', 'jpeg'])
    st.markdown("<br><center><p style='color:#8b949e !important;'>BIVIC 2026 PROJECT</p></center>", unsafe_allow_html=True)
    st.markdown("<center><p style='color:#00c6ff !important; font-weight:bold;'>ST-Vison v2.9.2</p></center>", unsafe_allow_html=True)

# CHAT HISTORY
if "messages" not in st.session_state or not st.session_state.messages:
    db_msgs = load_memory()
    if not db_msgs:
        welcome = "Hello! I am Vison, your AI STEM Tutor. How can I help you today?"
        st.session_state.messages = [{"role": "assistant", "content": welcome}]
        save_message("assistant", welcome)
    else:
        st.session_state.messages = db_msgs

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"] if isinstance(msg["content"], str) else msg["content"][0]["text"])

# CHAT LOGIC
user_input = st.chat_input("Ask Vison a STEM question...")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)
        if uploaded_file: st.image(uploaded_file, width=300)

    if uploaded_file:
        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        user_content = [{"type": "text", "text": user_input}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]
        st.session_state.messages.append({"role": "user", "content": user_content})
        save_message("user", f"{user_input} [Image Uploaded]")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_message("user", user_input)

    with st.chat_message("assistant"):
        if client:
            with st.spinner("Vison is thinking..."):
                try:
                    sys_p = f"You are a {persona} in {lang}. Focus on STEM."
                    api_msgs = [{"role": "system", "content": sys_p}]
                    
                    # FIX: Sanitize messages for API (Convert everything back to string if not sending a new image)
                    for m in st.session_state.messages:
                        clean_content = m["content"]
                        if isinstance(clean_content, list) and not uploaded_file:
                            clean_content = clean_content[0]["text"] # Strip the image for non-vision models
                        api_msgs.append({"role": m["role"], "content": clean_content})
                    
                    # Choose model based on CURRENT upload
                    model_id = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.1-8b-instant"
                    
                    res = client.chat.completions.create(model=model_id, messages=api_msgs)
                    ans = res.choices[0].message.content
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                    save_message("assistant", ans)
                except Exception as e:
                    st.error(f"Error: {e}")
        










