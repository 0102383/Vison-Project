import streamlit as st
import sqlite3, base64, os, time, uuid
import streamlit.components.v1 as components
from fpdf import FPDF
from groq import Groq

# --- PART 1: SETTINGS ---
LOGO, AVATAR, ADMIN = "vison_logo.jpg", "ai_logo_glow.jpg", "0102383"

# --- PART 2: DATABASE ---
def db_query(q, data=(), fetch=False):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor(); c.execute(q, data)
    res = c.fetchall() if fetch else None
    conn.commit(); conn.close(); return res

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    db_query('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')

# --- PART 3: PDF ENGINE ---
def create_pdf(history):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "VISON AI NOTES", ln=True, align='C'); pdf.set_font("Arial", size=11)
    for m in history: pdf.multi_cell(0, 8, f"\n{'YOU' if m['role']=='user' else 'VISON'}: {m['content']}")
    return pdf.output(dest='S').encode('latin-1')

# --- PART 4: BRAIN, EVOLUTION & POWER LOGIC ---
def get_mem(u):
    past = db_query('SELECT content FROM chat_log WHERE username=? AND role="user" ORDER BY id DESC LIMIT 15', (u,), True)
    res = db_query('SELECT interests, level, secret_profile FROM users WHERE username=?', (u,), True)
    txt = " ".join([r[0] for r in past])
    return {"i": res[0][0], "l": res[0][1], "s": res[0][2], "c": txt[-600:]} if res else {"i":"STEM","l":"High School","s":"None","c":""}

def analyze_student_stats(u):
    logs = db_query('SELECT role, content FROM chat_log WHERE username=? ORDER BY id DESC LIMIT 20', (u,), True)
    if not logs: return "Not enough data.", 0
    history_text = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        # 1. Emotional Evolution String
        evo_res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"Summarize only the emotional feelings and mental blocks of this student for evolution: {history_text}"}])
        # 2. Academic Power Level
        pwr_res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"Based on the knowledge shown, give a Power Level from 0-100. Return ONLY the number: {history_text}"}])
        power_val = int(''.join(filter(str.isdigit, pwr_res.choices[0].message.content)))
        return evo_res.choices[0].message.content, power_val
    except: return "Engine Offline", 10

# --- PART 5: UI STYLE ---
st.set_page_config(page_title="VISON AI", layout="wide")
st.markdown("<style>.title { font-size:45px; font-weight:800; background:linear-gradient(45deg,#a252ff,#0072ff); -webkit-background-clip:text; -webkit-text-fill-color:transparent; text-align:center; }</style>", unsafe_allow_html=True)

# --- PART 6: SIDEBAR & ADMIN VAULT ---
init_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.markdown('<p class="title">VISON CORE</p>', unsafe_allow_html=True)
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Unlock"):
        res = db_query('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_query('INSERT INTO users VALUES (?,?,?,?,?)', (u.lower(), p, "STEM", "High School", "New Student"))
        if not res or res[0][0] == p:
            st.session_state.logged_in, st.session_state.username = True, u.lower()
            st.session_state.sid = str(uuid.uuid4()); st.rerun()
    st.stop()

with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    st.divider(); mem = get_mem(st.session_state.username)
    if st.button("➕ New Chat"): st.session_state.sid = str(uuid.uuid4()); st.session_state.messages = []; st.rerun()
    ni = st.text_area("Personality Notes", value=mem["i"])
    if st.button("Update Memory"): db_query('UPDATE users SET interests=? WHERE username=?', (ni, st.session_state.username)); st.success("Saved")
    
    if st.session_state.username == ADMIN:
        with st.expander("🕵️ VISON VAULT (STATS)"):
            if st.button("⚡ Sync Evolution & Power"):
                evo, pwr = analyze_student_stats(st.session_state.username)
                st.session_state.evo, st.session_state.pwr = evo, pwr
            if "pwr" in st.session_state:
                st.metric("Academic Power Level", f"{st.session_state.pwr}/100")
                st.subheader("🧬 Evolution (Feelings)")
                st.code(st.session_state.evo, language="text")
            st.divider()
            for un, ui, us in db_query('SELECT username, interests, secret_profile FROM users', fetch=True):
                st.write(f"**{un}**: {ui}"); st.divider()

    st.divider(); persona = st.selectbox("Persona", ["Friendly Mentor", "Strict Professor", "Quirky Scientist", "Casual Buddy"])
    if st.button("🗑️ Purge Memory"): db_query('DELETE FROM chat_log WHERE username=?', (st.session_state.username,)); st.rerun()

# --- PART 7: CHAT ---
st.markdown('<p class="title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)
if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages: 
    with st.chat_message(m["role"]): st.markdown(m["content"])

up, user_in = st.file_uploader("Image", type=['png','jpg','jpeg']), st.chat_input("Ask...")
if user_in:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    st.session_state.messages.append({"role": "user", "content": user_in})
    db_query('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", user_in, st.session_state.sid))
    with st.chat_message("user"): st.markdown(user_in)
    with st.chat_message("assistant"):
        mid = "llama-3.2-11b-vision-instruct" if up else "llama-3.3-70b-versatile"
        sys = f"You are {persona}. Global Context: {mem['c']}. Personality: {mem['i']}. AI Summary: {mem['s']}"
        res = client.chat.completions.create(model=mid, messages=[{"role":"system","content":sys}]+st.session_state.messages)
        ans = res.choices[0].message.content; st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        db_query('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))

# --- PART 8: SCROLL ---
components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)
