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

# Sidebar Settings & Image Uploader
with st.sidebar:
    st.header("Settings")
    lang = st.selectbox("Language / Bahasa", ["English", "Bahasa Melayu", "Japanese"])
    persona = st.selectbox("Tutor Persona", ["Friendly Mentor", "Quirky Scientist", "Strict Professor"])
    st.info("Vison is currently in 'Live Mode' for BIVIC 2026.")
    
    st.markdown("---")
    st.header("👁️ Vison Vision")
    uploaded_file = st.file_uploader("Upload a Math/Science Problem", type=['png', 'jpg', 'jpeg'])
    if uploaded_file:
        st.success("Image received! Ask a question about it below.")

# 4. CHAT HISTORY MEMORY
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. MAIN APP LOGIC
user_input = st.chat_input("Ask a STEM question or tell Vison to look at the image...")

if user_input:
    # Save and show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Image", width=250)
    
    # AI Response
    with st.chat_message("assistant"):
        if client is None:
            st.error("Vison's brain is disconnected.")
        else:
            with st.spinner("Vison is analyzing..."):
                try:
                    # Setup the Persona
                    system_prompt = f"You are a {persona} tutoring in {lang}. Focus on STEM. If the user uploads an image, analyze it carefully."
                    api_messages = [{"role": "system", "content": system_prompt}]
                    
                    # VISION MODE: If an image is uploaded
                    if uploaded_file:
                        # Convert image to a format the AI can read
                        base64_image = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
                        
                        user_msg = {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_input},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }
                        api_messages.append(user_msg)
                        active_model = "llama-3.2-11b-vision-preview" # Groq's Vision Brain
                        
                    # NORMAL TEXT MODE: No image uploaded
                    else:
                        for msg in st.session_state.messages:
                            api_messages.append({"role": msg["role"], "content": msg["content"]})
                        active_model = "llama-3.1-8b-instant" # Groq's Text Brain

                    # Call the AI Engine
                    response = client.chat.completions.create(
                        model=active_model, 
                        messages=api_messages
                    )
                    
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    
                    # Save the AI's answer
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                except Exception as e:
                    st.error(f"VISION ERROR: {e}")
                    






