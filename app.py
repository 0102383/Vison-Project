import streamlit as st
import sqlite3, base64, os, time, uuid, datetime
import streamlit.components.v1 as components
from fpdf import FPDF
from groq import Groq

# --- PART 1: SETTINGS & AVATARS ---
LOGO_FILENAME = "vison_logo.jpg"
AI_AVATAR_FILENAME = "ai_logo_glow.jpg"
ADMIN = "0102383"

def get_64(p):
    if os.path.exists(p):
        with open(p, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# --- PART 2: DATABASE & SELF-HEALING ---
def db_q(q, d=(), fetch=False):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    try:
        c.execute(q, d)
        res = c.fetchall() if fetch else None
        conn.commit()
        return res
    finally: conn.close()

def init_db():
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT, mood_emoji TEXT DEFAULT '💬')''')
    # Auto-patcher for column compatibility
    cols = [r[1] for r in db_q("PRAGMA table_info(chat_log)", fetch=True)]
    if 'session_id' not in cols: db_q('ALTER TABLE chat_log ADD COLUMN session_id TEXT')

# --- PART 3: PDF ENGINE ---
def create_pdf(user, power, evolution, history):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "VISON EVOLUTION REPORT", ln=True, align='C')
    pdf.set_font("Arial", size=10); pdf.cell(200, 10, f"User: {user} | Power: {power}/100", ln=True)
    pdf.ln(5); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "Mental State Summary:", ln=True)
    pdf.set_font("Arial", size=10); pdf.multi_cell(0, 8, evolution)
    pdf.ln(5); pdf.cell(0, 10, "Recent Log:", ln=True)
    for m in history[-10:]: pdf.multi_cell(0, 6, f"{m['role'].upper()}: {m['content']}\n")
    return pdf.output(dest='S').encode('latin-1')

# --- PART 4: BRAIN & EVOLUTION ANALYZER ---
def get_mem(u):
    past = db_q('SELECT content FROM chat_log WHERE username=? AND role="user" ORDER BY id DESC LIMIT 10', (u,), True)
    res = db_q('SELECT interests, level, secret_profile FROM users WHERE username=?', (u,), True)
    txt = " ".join([r[0] for r in past]) if past else ""
    return {"i": res[0][0] if res else "STEM", "l": res[0][1] if res else "HS", "s": res[0][2] if res else "New", "c": txt[-500:]}

def analyze_evolution(u, sid):
    logs = db_q('SELECT role, content FROM chat_log WHERE username=? AND session_id=? ORDER BY id DESC LIMIT 15', (u, sid), True)
    if not logs: return "Initial State", 10, "💬"
    h = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        evo = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Summarize psychological/learning blocks: {h}"}])
        pwr = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Academic Power 0-100 (Num only): {h}"}])
        mood = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Pick 1 emoji for this user's mood: {h}"}])
        e, p, m = evo.choices[0].message.content, int(''.join(filter(str.isdigit, pwr.choices[0].message.content))), mood.choices[0].message.content.strip()[0]
        db_q('UPDATE users SET secret_profile=? WHERE username=?', (e, u))
        db_q('UPDATE chat_sessions SET mood_emoji=? WHERE session_id=?', (m, sid))
        return e, p, m
    except: return "Syncing...", 10, "⏳"

# --- PART 5: UI & CSS (YOUR FAVORITE THEME) ---
st.set_page_config(page_title="VISON AI", layout="wide")
init_db()

st.markdown("""
    <style>
    .online-indicator { display: inline-block; width: 10px; height: 10px; background-color: #a252ff; border-radius: 50%; margin-right: 8px; box-shadow: 0 0 8px #a252ff; }
    .main-title { font-size: 45px !important; font-weight: 800; background: linear-gradient(#a252ff, #0072ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }
    
    /* CHAT BUBBLE STYLING */
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) {
        flex-direction: row-reverse !important; text-align: right;
    }
    div[data-testid="stChatMessage"]:has(span[aria-label="User Avatar icon"]) > div {
        background-color: rgba(162, 82, 255, 0.05) !important; border: 1px solid #a252ff !important; border-radius: 15px !important;
    }
    div[data-testid="stChatMessage"]:has(img[data-testid="stChatMessageAvatarImage"]) > div {
        background-color: rgba(0, 114, 255, 0.05) !important; border: 1px solid #0072ff !important; border-radius: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- PART 6: GATEWAY ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    lb = get_64(LOGO_FILENAME)
    if lb: st.markdown(f'<center><img src="data:image/jpeg;base64,{lb}" width="200" style="border-radius:20px; box-shadow: 0 0 20px rgba(162,82,255,0.3);"></center>', unsafe_allow_html=True)
    st.markdown('<p class="main-title">VISON GATEWAY</p>', unsafe_allow_html=True)
    u, p = st.text_input("User ID"), st.text_input("Security Key", type="password")
    if st.button("Unlock Core"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_q('INSERT INTO users (username, password, interests, level) VALUES (?,?,?,?)', (u.lower(), p, "STEM", "HS"))
        if not res or res[0][0] == p: st.session_state.logged_in, st.session_state.username = True, u.lower(); st.rerun()
    st.stop()

# --- PART 7: SIDEBAR (PRO FEATURES) ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    st.divider()
    
    # Session Management
    sessions = db_q('SELECT session_id, session_name, last_modified, mood_emoji FROM chat_sessions WHERE username=? ORDER BY last_modified DESC', (st.session_state.username,), True)
    if st.button("➕ New Session"):
        nid, now = str(uuid.uuid4()), datetime.datetime.now().strftime("%d %b, %H:%M")
        db_q('INSERT INTO chat_sessions VALUES (?,?,?,?,?)', (nid, st.session_state.username, "New Evolution", now, "💬"))
        st.session_state.sid, st.session_state.messages = nid, []; st.rerun()
    
    if sessions:
        s_list = [f"{s[3]} {s[1]} ({s[2]})" for s in sessions]
        s_dict = {f"{s[3]} {s[1]} ({s[2]})": s[0] for s in sessions}
        sel = st.selectbox("Timeline:", s_list)
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

    # Admin/Report Vault
    if st.session_state.username == ADMIN:
        st.divider()
        with st.expander("🕵️ EVOLUTION VAULT"):
            if st.button("⚡ Sync & Analyze"):
                e, pw, mo = analyze_evolution(st.session_state.username, st.session_state.sid)
                st.session_state.evo, st.session_state.pwr = e, pw
            if "pwr" in st.session_state:
                st.metric("Power Level", f"{st.session_state.pwr}/100")
                pdf = create_pdf(st.session_state.username, st.session_state.pwr, st.session_state.evo, st.session_state.messages)
                st.download_button("📄 Download Report", data=pdf, file_name=f"vison_{st.session_state.username}.pdf")
            if st.button("🗑️ NUCLEAR WIPE"):
                db_q('DELETE FROM chat_log WHERE username=?', (st.session_state.username,))
                db_q('DELETE FROM chat_sessions WHERE username=?', (st.session_state.username,)); st.rerun()

# --- PART 8: CHAT INTERFACE ---
st.markdown('<p class="main-title">🚀 VISON AI CORE</p>', unsafe_allow_html=True)
st.markdown('<center><div style="margin-bottom:20px;"><span class="online-indicator"></span><span style="color:#a252ff;">EVOLUTION TRACKER ACTIVE</span></div></center>', unsafe_allow_html=True)

if 'sid' not in st.session_state:
    st.session_state.sid = str(uuid.uuid4())
    db_q('INSERT OR IGNORE INTO chat_sessions VALUES (?,?,?,?,?)', (st.session_state.sid, st.session_state.username, "Core Entry", datetime.datetime.now().strftime("%d %b, %H:%M"), "💬"))

ai_av_b64 = get_64(AI_AVATAR_FILENAME)
ai_av = f"data:image/png;base64,{ai_av_b64}" if ai_av_b64 else "🤖"

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): st.markdown(m["content"])

user_in = st.chat_input("Evolve your thinking...")
if user_in:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    now = datetime.datetime.now().strftime("%d %b, %H:%M")
    st.session_state.messages.append({"role": "user", "content": user_input}) # Corrected var
    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", user_in, st.session_state.sid))
    db_q('UPDATE chat_sessions SET last_modified=? WHERE session_id=?', (now, st.session_state.sid))
    
    with st.chat_message("user", avatar="👤"): st.markdown(user_in)
    with st.chat_message("assistant", avatar=ai_av):
        mem = get_mem(st.session_state.username)
        sys = f"You are a Strict Professor. Focus on STEM and emotional evolution. Secret Student Profile: {mem['s']}"
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":sys}]+st.session_state.messages[-10:])
        ans = res.choices[0].message.content; st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))

components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)
