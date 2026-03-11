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

# 3. UI LAYOUT
st.set_page_config(page_title="VISON AI", page_icon="🚀")
st.title("🚀 VISON: AI STEM Tutor")
# 3. UI LAYOUT
st.set_page_config(page_title="VISON AI", page_icon="🚀")

# --- CUSTOM DESIGN START ---
st.markdown("""
    <style>
    /* Dark mode background */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Gradient Sidebar */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(#1e1e2f, #0e1117);
        border-right: 1px solid #3d3d5c;
    }

    /* Professional Gradient Title */
    .main-title {
        font-size: 45px !important;
        font-weight: 800 !important;
        background: -webkit-linear-gradient(#00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-top: 0px;
    }
    
    /* Better Chat Input */
    .stChatInput {
        border-radius: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🚀 VISON AI</p>', unsafe_allow_html=True)
st.markdown("##### *The Future of STEM Learning*")
st.markdown("---")
# --- CUSTOM DESIGN END ---

# Sidebar Settings
with st.sidebar:
    st.header("Settings")
    lang = st.selectbox("Language / Bahasa", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Tutor Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor"])
    st.info("Vison is currently in 'Live Mode' for BIVIC 2026.")
    
    if st.button("🗑️ Clear Long-Term Memory"):
        clear_memory()
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.header("👁️ Vison Vision")
    uploaded_file = st.file_uploader("Upload a Math/Science Problem", type=['png', 'jpg', 'jpeg'])

# 4. CHAT HISTORY
if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = load_memory()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
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
    
    # Save user message to memory
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
    
    # AI Response
    with st.chat_message("assistant"):
        if client is None:
            st.error("Vison's brain is disconnected.")
        else:
            with st.spinner("Vison is analyzing..."):
                try:
                    system_prompt = f"You are a {persona} tutoring in {lang}. Focus on STEM. If the user uploads an image, analyze it carefully."
                    api_messages = [{"role": "system", "content": system_prompt}]
                    
                    for msg in st.session_state.messages:
                        api_messages.append({"role": msg["role"], "content": msg["content"]})
                        
                    if uploaded_file:
                        active_model = "meta-llama/llama-4-scout-17b-16e-instruct" 
                    else:
                        active_model = "llama-3.1-8b-instant"

                    response = client.chat.completions.create(
                        model=active_model, 
                        messages=api_messages
                    )
                    
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    save_message("assistant", answer)
                    
                except Exception as e:
                    st.error(f"API ERROR: {e}")
        
                    












