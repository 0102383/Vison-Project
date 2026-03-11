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
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #33d9b2;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    .stApp { background-color: #0e1117; }
    h1, h2, h3, h4, h5, p, span, div, label, li { color: #ffffff !important; }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    .main-title {
        font-size: 50px !important;
        font-weight: 800 !important;
        background: -webkit-linear-gradient(#00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    [data-testid="stChatMessageAssistant"] {
        border-left: 4px solid #00c6ff;
        background-color: #1c2128 !important;
        border-radius: 10px;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        color: white !important;
        background-color: #0e1117 !important;
    }
    .robot-container {
        fill: #000000;
        filter: drop-shadow(0 0 8px rgba(0, 198, 255, 0.8));
        margin: 20px 0;
    }
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
            <path d="M
        








