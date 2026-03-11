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
    st.error(f"Key Error: Make sure your key is typed correctly. Details: {e}")

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
    /* Pulse Animation */
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
    
    /* Overall Theme */
    .stApp { background-color: #0e1117; color: white; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Gradient Title */
    .main-title {
        font-size: 50px !important;
        font-weight: 800 !important;
        background: -webkit-linear-gradient(#00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    
    /* Assistant Messages Styling */
    [data-testid="stChatMessageAssistant"] {
        border-left: 4px solid #00c6ff;
        background-color: #1c2128 !important;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Main Header
st.markdown('<p class="main-title">🚀 VISON AI</p>', unsafe_allow_html=True)
st.markdown("##### *The Future of STEM Learning*")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.markdown('<center><h1 style="font-size: 80px; margin-bottom:0;">🤖</h1></center>', unsafe_allow_html=True)
    st.markdown("<center><h3 style='margin-top:0;'>VISON CORE</h3></center>", unsafe_allow_html=True)
    
    # Pulse Status
    st.markdown("""
        <div style="background: rgba(51, 217, 178, 0.1); padding: 10px; border-radius: 10px; border: 1px solid rgba(51, 217, 178, 0.3); text-align: center; margin-bottom: 20px;">
            <span class="online-indicator"></span>
            <span style="color: #33d9b2; font-weight: bold; font-family: monospace;">SYSTEM ONLINE</span>
        </div>
    """, unsafe_allow_html=True)
    
    lang = st.selectbox("Language / Bahasa", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Tutor Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor"])
    
    if st.button("🗑️ Clear Long-Term Memory"):
        clear_memory()
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.header("🔍 Image Scanner")
    uploaded_file = st.file_uploader("Upload Math/Science Problem", type=['png', 'jpg', 'jpeg'])

# 4. CHAT HISTORY (Load from DB)
if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = load_memory()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            # Re-displaying image indicator for history
            st.markdown(message["content"][0]["text"])

# 5. CHAT LOGIC
user_input = st.chat_input("How can I help you with STEM today?")

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
        save_message("user", user_input + " [Image Uploaded]")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_message("user", user_input)

    # Assistant Response
    with st.chat_message("assistant"):
        if client:
            with st.spinner("Vison is processing..."):
                try:
                    system_prompt = f"You are a {persona} tutoring in {lang}. Focus on STEM. Be helpful and concise."
                    api_messages = [{"role": "system", "content": system_prompt}]
                    
                    # Add history to API call
                    for msg in st.session_state.messages:
                        api_messages.append({"role": msg["role"], "content": msg["content"]})
                    
                    # Pick Model
                    if uploaded_file:
                        active_model = "meta-llama/llama-4-scout-17b-16e-instruct"
                    else:
                        active_model = "llama-3.1-8b-instant"

                    response = client.chat.completions.create(model=active_model, messages=api_messages)
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    save_message("assistant", answer)
                except Exception as e:
                    st.error(f"Error: {e}")















