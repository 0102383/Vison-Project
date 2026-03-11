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

# 2. DATABASE (LONG-TERM MEMORY UPGRADE)
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    # Create a permanent table to store the chat log
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
    # Translate the database rows back into Streamlit's format
    return [{"role": row[0], "content": row[1]} for row in data]

def clear_memory():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM chat_log')
    conn.commit()
    conn.close()

init_db()

# 3. UI LAYOUT
st.set_page_config(page_title="VISON AI", page_icon="🚀")
st.title("🚀 VISON: AI STEM Tutor")
st.markdown("---")

# Sidebar Settings
with st.sidebar:
    st.header("Settings")
    lang = st.selectbox("Language / Bahasa", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Tutor Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor"])
    st.info("Vison is currently in 'Live Mode' for BIVIC 2026.")
    
    # NEW: Button to wipe the database
    if st.button("🗑️ Clear Long-Term Memory"):
        clear_memory()
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.header("👁️ Vison Vision")
    uploaded_file = st.file_uploader("Upload a Math/Science Problem", type=['png', 'jpg', 'jpeg'])

# 4. CHAT HISTORY (Loading from the Database)
if "messages" not in st.session_state or not st.session_state.messages:
    # When the page loads, pull the memory from the SQLite database
    st.session_state.messages = load_memory()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Handle regular text OR images safely
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            st.markdown(message["content"][0]["text"])

# 5. MAIN APP LOGIC
user_input = st.chat_input("Ask a STEM question or tell Vison to look at the image...")

if user_input:
    # Show user message on screen
    with st.chat_message("user"):
        st.write(user_input)
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Image", width=250)
    
    # Save user message to Short-Term AND Long-Term Memory
    if uploaded_file:
        base64_image = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        user_msg_content = [
            {"type": "text", "text": user_input},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
                    









