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
    /* Pulse Animation for System Online */
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(51, 217, 178, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(51, 217, 178, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(51, 217, 178, 0); }
    }
    .online-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #33d9b2;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    
    /* Dark Theme & Global White Text */
    .stApp { background-color: #0e1117; }
    h1, h2, h3, h4, h5, p, span, div, label, li { color: #ffffff !important; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Professional Gradient Title */
    .main-title {
        font-size: 50px !important;
        font-weight: 800 !important;
        background: -webkit-linear-gradient(#00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    
    /* AI Message Bubble Styling */
    [data-testid="stChatMessageAssistant"] {
        border-left: 4px solid #00c6ff;
        background-color: #1c2128 !important;
        border-radius: 10px;
    }

    /* Fix Dropdown/Input visibility */
    .stSelectbox div[data-baseweb="select"] > div {
        color: white !important;
        background-color: #0e1117 !important;
    }

    /* Solid Black Icon Styling with Glow */
    .black-icon {
        color: #000000 !important;
        font-size: 100px;
        margin-bottom: 0px;
        filter: drop-shadow(0 0 10px rgba(0, 198, 255, 0.6));
    }
    </style>
    """, unsafe_allow_html=True)

# Main Screen Header
st.markdown('<p class="main-title">🚀 VISON AI</p>', unsafe_allow_html=True)
st.markdown("##### *The Future of STEM Learning*")
st.markdown("---")

# --- SIDEBAR START ---
with st.sidebar:
    # 1. SETTINGS AT THE TOP
    st.markdown("### ⚙️ System Settings")
    lang = st.selectbox("Language / Bahasa", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Tutor Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor"])
    
    if st.button("🗑️ Clear Long-Term Memory"):
        clear_memory()
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")

    # 2. BRANDING & STATUS (Black Icon Here)
    st.markdown('<center><h1 class="black-icon">🤖</h1></center>', unsafe_allow_html=True)
    st.markdown("<center><h3 style='margin-top:0;'>VISON CORE</h3></center>", unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background: rgba(51, 217, 178, 0.1); padding: 10px; border-radius: 10px; border: 1px solid rgba(51, 217, 178, 0.3); text-align: center; margin-bottom: 20px;">
            <span class="online-indicator"></span>
            <span style="color: #33d9b2; font-weight: bold; font-family: monospace;">SYSTEM ONLINE</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 3. SCANNER AT THE BOTTOM
    st.header("🔍 Image Scanner")
    uploaded_file = st.file_uploader("Upload Math/Science Problem", type=['png', 'jpg', 'jpeg'])

    # Footer Credits
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<center><p style='color:#8b949e !important;'>BIVIC 2026 PROJECT</p></center>", unsafe_allow_html=True)
    st.markdown("<center><p style='color:#00c6ff !important; font-weight:bold;'>ST-Vison v2.7</p></center>", unsafe_allow_html=True)
# --- SIDEBAR END ---

# 4. CHAT HISTORY (Memory Management)
if "messages" not in st.session_state or not st.session_state.messages:
    db_messages = load_memory()
    if not db_messages:
        welcome_text = "Hello! I am Vison, your AI STEM Tutor. How can I help you explore science or math today?"
        st.session_state.messages = [{"role": "assistant", "content": welcome_text}]
        save_message("assistant", welcome_text)
    else:
        st.session_state.messages = db_messages

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            st.markdown(message["content"][0]["text"])

# 5. CHAT LOGIC
user_input = st.chat_input("Ask Vison a STEM question...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)
        if uploaded_file:
            st.image(uploaded_file, width=300)

    # Save logic
    if uploaded_file:
        base64_image = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        user_msg_content = [
            {"type": "text", "text": user_input},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
        st.session_state.messages.append({"role": "user", "content": user_msg_content})
        save_message("user", f"{user_input} [Image Uploaded]")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_message("user", user_input)

    # Assistant Response
    with st.chat_message("assistant"):
        if client:
            with st.spinner("Vison is thinking..."):
                try:
                    system_prompt = f"You are a {persona} tutoring in {lang}. Focus on STEM. Use clear formatting."
                    api_messages = [{"role": "system", "content": system_prompt}]
                    
                    for msg in st.session_state.messages:
                        api_messages.append({"role": msg["role"], "content": msg["content"]})
                    
                    active_model = "meta-llama/llama-4-scout-17b-16e-instruct" if uploaded_file else "llama-3.1-8b-instant"

                    response = client.chat.completions.create(model=active_model, messages=api_messages)
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    save_message("assistant", answer)
                except Exception as e:
                    st.error(f"Error: {e}")












