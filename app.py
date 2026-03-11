
import streamlit as st
from groq import Groq
import sqlite3

# 1. SETUP & SECRETS
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Please add GROQ_API_KEY to your Streamlit Secrets!")

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
    # Save and show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    # AI Response
    with st.chat_message("assistant"):
        with st.spinner("Vison is thinking incredibly fast..."):
            try:
                # Setup the Persona
                system_prompt = f"You are a {persona} tutoring in {lang}. Focus on STEM."
                api_messages = [{"role": "system", "content": system_prompt}]
                
                # Add history so it remembers the conversation
                for msg in st.session_state.messages:
                    api_messages.append({"role": msg["role"], "content": msg["content"]})
                    
                # Call the ultra-fast Groq model
                response = client.chat.completions.create(
                    model="llama3-8b-8192", 
                    messages=api_messages
                )
                
                answer = response.choices[0].message.content
                st.markdown(answer)
                
                # Save the AI's answer
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error("Error connecting to the AI. Did you add the Groq API Key?")

