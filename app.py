import streamlit as st
import openai
import sqlite3
import base64
import os
import shutil

# ==========================================
# 0. SELF-REVIVE (AUTO-BACKUP SYSTEM)
# ==========================================
def create_backup():
    """Silently saves a backup of the code and database every time the app starts."""
    backup_folder = "Vison_Safe_Backups"
    
    # Create the backup folder if it doesn't exist
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)
        
    try:
        # 1. Backup this exact Python script
        current_script = os.path.abspath(__file__)
        script_backup = os.path.join(backup_folder, "app_master_backup.py")
        shutil.copyfile(current_script, script_backup)
        
        # 2. Backup the SQLite Database (so user memory isn't lost)
        db_file = "vison_database.db"
        if os.path.exists(db_file):
            db_backup = os.path.join(backup_folder, "vison_database_backup.db")
            shutil.copyfile(db_file, db_backup)
            
    except Exception as e:
        # If the backup fails for some reason, we don't want it to crash the main app
        pass

# Run the backup sequence immediately when the app starts
create_backup()

# ==========================================
# 1. APP CONFIGURATION & BRANDING
# ==========================================
st.set_page_config(page_title="Vison - AI STEM Tutor", page_icon="✨", layout="wide")
st.title("✨ Vison")
st.markdown("**Your Universal, Multilingual STEM Tutor.**")

# ==========================================
# 2. DATABASE SETUP (Privacy & Memory)
# ==========================================
conn = sqlite3.connect("vison_database.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id TEXT PRIMARY KEY,
        learned_rules TEXT,
        preferred_language TEXT
    )
''')
conn.commit()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def is_safe(client, text):
    response = client.moderations.create(input=text)
    return not response.results[0].flagged

def update_learning(client, user_id, user_input, ai_response):
    if not is_safe(client, user_input):
        return 

    cursor.execute("SELECT learned_rules FROM user_profiles WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    current_rules = result[0] if result else "You are a helpful assistant."

    learning_prompt = (
        f"Current rules: '{current_rules}'.\n"
        f"User said: '{user_input}'.\n"
        f"You replied: '{ai_response}'.\n"
        "Analyze this. Did the user express a positive preference or value about how you should act? "
        "If yes, rewrite the 'Current rules' to include this adaptation. "
        "If no, output the exact same rules. Output ONLY the rules."
    )
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": learning_prompt}]
    )
    
    new_rules = response.choices[0].message.content.strip()
    
    cursor.execute('''
        INSERT INTO user_profiles (user_id, learned_rules) 
        VALUES (?, ?) 
        ON CONFLICT(user_id) DO UPDATE SET learned_rules = excluded.learned_rules
    ''', (user_id, new_rules))
    conn.commit()

# ==========================================
# 4. SIDEBAR (User Settings & Persona)
# ==========================================
with st.sidebar:
    st.header("⚙️ Vison Settings")
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    user_id = st.text_input("Enter your Username (e.g., student_1):", value="demo_user")
    
    st.divider()
    
    st.header("🎭 Personalization")
    tutor_persona = st.selectbox(
        "Choose Vison's Teaching Style:", 
        ["Friendly Mentor", "Strict Professor", "Quirky Scientist"]
    )
    
    st.header("🌐 Language")
    language = st.selectbox("Choose language:", ["English (US)", "Bahasa Melayu", "Japanese"])

# ==========================================
# 5. CHAT MEMORY INITIALIZATION
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            if type(msg["content"]) is str:
                st.markdown(msg["content"])
            else:
                st.markdown(msg["content"][0]["text"])

# ==========================================
# 6. USER INPUTS (Mic, Camera, Keyboard)
# ==========================================
st.write("---")
col1, col2 = st.columns(2)
with col1:
    uploaded_image = st.file_uploader("📸 Upload a problem (Image)", type=["jpg", "png"])
with col2:
    recorded_audio = st.audio_input("🎤 Speak to Vison")

user_text = st.chat_input("Or type your question here...")
final_user_input = None

if recorded_audio and api_key:
    client = openai.OpenAI(api_key=api_key)
    with st.spinner("Listening..."):
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=recorded_audio
        )
        final_user_input = transcription.text
elif user_text:
    final_user_input = user_text

# ==========================================
# 7. MAIN AI LOGIC (Brain, Vision, Voice, Persona)
# ==========================================
if final_user_input:
    if not api_key:
        st.error("⚠️ API Key is missing! Please add it in the sidebar.")
        st.stop()
        
    client = openai.OpenAI(api_key=api_key)

    with st.chat_message("user"):
        st.markdown(final_user_input)
        if uploaded_image:
            st.image(uploaded_image, width=300)

    if uploaded_image:
        base64_img = encode_image(uploaded_image)
        new_msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": final_user_input},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
            ]
        }
    else:
        new_msg = {"role": "user", "content": final_user_input}
        
    st.session_state.messages.append(new_msg)

    # --- Fetch Rules & Build Ultimate Prompt ---
    cursor.execute("SELECT learned_rules FROM user_profiles WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    user_rules = res[0] if res else "No rules learned yet."

    lang_instr = f"Respond entirely in {language}. "
    if language == "Japanese":
        lang_instr += "Follow Japanese sentences with English translations in parentheses."

    stem_instr = (
        "You are an expert tutor. If asked about STEM: "
        "1. Read any uploaded images carefully. "
        "2. Break problems down step-by-step. "
        "3. Use LaTeX for math ($ for inline, $$ for display)."
    )

    persona_instr = ""
    if tutor_persona == "Friendly Mentor":
        persona_instr = "Personality: Be incredibly warm, encouraging, and use supportive emojis. Praise the student for asking questions!"
    elif tutor_persona == "Strict Professor":
        persona_instr = "Personality: Be highly formal, direct, and serious. Do not use emojis. Focus strictly on academic excellence and precision."
    elif tutor_persona == "Quirky Scientist":
        persona_instr = "Personality: Be highly energetic and slightly eccentric. Explain concepts using fun, wild analogies (like space, explosions, or time travel)!"

    system_prompt = f"Rules: {user_rules}\n{lang_instr}\n{stem_instr}\n{persona_instr}"
    api_messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages

    # --- Generate AI Text ---
    with st.chat_message("assistant"):
        with st.spinner(f"Vison is thinking as a {tutor_persona}..."):
            response = client.chat.completions.create(
                model="gpt-4o", 
                messages=api_messages
            )
            ai_text = response.choices[0].message.content
            st.markdown(ai_text)
            
            # --- TEXT TO SPEECH (Mouth) ---
            with st.spinner("Generating voice..."):
                audio_response = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=ai_text
                )
                st.audio(audio_response.content, format="audio/mp3", autoplay=True)

    st.session_state.messages.append({"role": "assistant", "content": ai_text})
    update_learning(client, user_id, final_user_input, ai_text)
