import streamlit as st
import sqlite3
import base64
import os
from fpdf import FPDF
from gtts import gTTS # New library for Voice
import io

# --- ⚙️ MASTER SETTINGS ⚙️ ---
LOGO_FILENAME = "vison_logo.jpg" 
AI_AVATAR_FILENAME = "ai_logo_glow.jpg"

# --- 1. SAFE LIBRARY IMPORT ---
GROQ_AVAILABLE = False
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    st.error("🚀 Please add `groq` and `gtts` to your `requirements.txt`!")

# --- 2. SETUP & SECRETS ---
client = None
if GROQ_AVAILABLE:
    try:
        if "GROQ_API_KEY" in st.secrets:
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except Exception as e:
        st.error(f"Connection Error: {e}")

# --- 3. DATABASE & FUNCTIONS ---
def init_db():
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT)''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN interests TEXT")
        c.execute("ALTER TABLE users ADD COLUMN level TEXT")
    except: pass
    conn.commit()
    conn.close()

def manage_user(username, password):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if row is None:
        c.execute('INSERT INTO users (username, password, interests, level) VALUES (?, ?, ?, ?)', 
                  (username, password, "", "High School"))
        conn.commit()
        conn.close()
        return "registered"
    elif row[0] == password:
        conn.close()
        return "authorized"
    else:
        conn.close()
        return "denied"

def save_profile(username, interests, level):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('UPDATE users SET interests=?, level=? WHERE username=?', (interests, level, username))
    conn.commit()
    conn.close()

def get_profile(username):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT interests, level FROM users WHERE username=?', (username,))
    res = c.fetchone()
    conn.close()
    return {"interests": res[0] or "General STEM", "level": res[1] or "High School"} if res else {"interests": "General STEM", "level": "High School"}

def save_message(username, role, content):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO chat_log (username, role, content) VALUES (?, ?, ?)', (username, role, content))
    conn.commit()
    conn.close()

def load_memory(username):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    c.execute('SELECT role, content FROM chat_log WHERE username=? ORDER BY id ASC', (username,))
    data = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in data]

# --- VOICE GENERATOR ---
def speak_text(text, lang_code='en'):
    # Clean LaTeX for better speaking
    clean_text = text.replace('$', '').replace('**', '')
    tts = gTTS(text=clean_text, lang=lang_code)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp

# --- PDF GENERATOR ---
def create_pdf(chat_history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="VISON AI Study Session", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    for msg in chat_history:
        role = "YOU" if msg["role"] == "user" else "VISON AI"
        pdf.multi_cell(0, 5, txt=f"\n{role}: {str(msg['content'])}")
    return pdf.output(dest='S').encode('latin-1')

init_db()

def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    return None

ai_avatar_b64 = get_image_base64(AI_AVATAR_FILENAME)

# --- UI & CSS ---
st.set_page_config(page_title="VISON AI", page_icon="🚀", layout="wide")
st.markdown("""<style>.main-title { font-size: 50px; font-weight: 800; background: -webkit-linear-gradient(#a252ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }</style>""", unsafe_allow_html=True)

# --- LOGIN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    logo_b64 = get_image_base64(LOGO_FILENAME)
    if logo_b64: st.markdown(f'<center><img src="data:image/jpeg;base64,{logo_b64}" width="300"></center>', unsafe_allow_html=True)
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Unlock"):
        if manage_user(u, p) in ["registered", "authorized"]:
            st.session_state.logged_in = True
            st.session_state.username = u
            st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    math_mode = st.toggle("📐 Math Mode", value=True)
    voice_toggle = st.toggle("🔊 Auto-Voice", value=False)
    profile = get_profile(st.session_state.username)
    new_ints = st.text_area("🧠 Interests", value=profile["interests"])
    new_level = st.selectbox("🎓 Level", ["Primary School", "High School", "University"], index=1)
    if st.button("Save Profile"): save_profile(st.session_state.username, new_ints, new_level)
    persona = st.selectbox("Persona", ["Friendly Mentor", "Quirky Scientist", "Casual Chat Buddy"])
    lang = st.selectbox("Language", ["English", "Bahasa Melayu", "Japanese"])
    if st.button("📄 Download PDF"):
        pdf_bytes = create_pdf(load_memory(st.session_state.username))
        st.download_button("Download", pdf_bytes, "study_guide.pdf")

# --- CHAT ---
st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)
if "messages" not in st.session_state: st.session_state.messages = load_memory(st.session_state.username)

for msg in st.session_state.messages:
    avatar = f"data:image/png;base64,{ai_avatar_b64}" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

st.markdown("---")
uploaded_file = st.file_uploader("➕ Add Image", type=['png', 'jpg', 'jpeg'])
user_input = st.chat_input("Ask Vison...")

if user_input:
    # Handle user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_message(st.session_state.username, "user", user_input)
    with st.chat_message("user", avatar="👤"): st.markdown(user_input)

    # Handle AI Response
    with st.chat_message("assistant", avatar=f"data:image/png;base64,{ai_avatar_b64}"):
        if client:
            model_id = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.1-8b-instant"
            sys_m = f"You are {persona}. Level: {new_level}. Interests: {new_ints}. Use LaTeX $$ if math mode."
            res = client.chat.completions.create(model=model_id, messages=[{"role": "system", "content": sys_m}] + st.session_state.messages)
            ans = res.choices[0].message.content
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            save_message(st.session_state.username, "assistant", ans)
            
            # VOICE OUTPUT
            lang_map = {"English": "en", "Bahasa Melayu": "ms", "Japanese": "ja"}
            audio_fp = speak_text(ans, lang_map.get(lang, "en"))
            st.audio(audio_fp, format='audio/mp3')

