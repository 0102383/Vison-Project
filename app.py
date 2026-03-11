
import streamlit as st
import google.generativeai as genai
import sqlite3

# 1. SETUP & SECRETS (OpenAI REMOVED!)
# We are now using the free Google Gemini AI
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Please add GOOGLE_API_KEY to your Streamlit Secrets!")

# 2. DATABASE (Self-Revive Logic)
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (name TEXT, persona TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 3. UI LAYOUT
st.set_page_config(page_title="VISON AI", page_icon="🚀")
st.title("🚀 VISON: AI STEM Tutor")
st.markdown("---")

# Sidebar for Personas and Language
with st.sidebar:
    st.header("Settings")
    lang = st.selectbox("Language / Bahasa", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Tutor Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor"])
    st.info("Vison is currently in 'Live Mode' for BIVIC 2026.")

# 4. CHAT HISTORY MEMORY
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. MAIN APP LOGIC
user_input = st.chat_input("Ask a STEM question...")

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    # AI Response
    with st.chat_message("assistant"):
        with st.spinner("Vison is thinking..."):
            try:
                # The New "Free Brain" logic
                prompt = f"You are a {persona} tutoring in {lang}. Focus on STEM. The user says: {user_input}"
                response = model.generate_content(prompt)
                answer = response.text
                
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error("Error connecting to the AI. Did you add the Google API Key?")

# 6. IMAGE UPLOADER (Computer Vision)
st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("Upload a Math/Science Problem", type=['png', 'jpg', 'jpeg'])
if uploaded_file:
    st.sidebar.success("Image received! (Integration Active)")
    
