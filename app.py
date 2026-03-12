import streamlit as st
import sqlite3, base64, os, time, uuid, datetime
import streamlit.components.v1 as components
from fpdf import FPDF
from groq import Groq

# --- PART 1: SETTINGS ---
LOGO, AVATAR, ADMIN = "vison_logo.jpg", "ai_logo_glow.jpg", "0102383"
def get_64(p):
    if os.path.exists(p):
        with open(p, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# --- PART 2: DATABASE ---
def db_q(q, d=(), fetch=False):
    conn = sqlite3.connect('vison_user_data.db')
    c = conn.cursor()
    try:
        c.execute(q, d)
        res = c.fetchall() if fetch else None
        conn.commit()
        return res
    finally:
        conn.close()

def init_db():
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT, mood_emoji TEXT DEFAULT '💬')''')

# --- PART 3: REPORT ENGINE (NEW) ---
def create_evolution_pdf(user, power, evolution, history):
    pdf = FPDF()
    pdf.add_page()
    # Header
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(200, 15, "VISON AI: EVOLUTION REPORT", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    # Stats
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Student: {user.upper()}", ln=True)
    pdf.cell(0, 10, f"Academic Power Level: {power}/100", ln=True)
    pdf.ln(5)
    
    # Evolution Summary
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Mental Evolution & Blocks:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, evolution)
    pdf.ln(10)
    
    # Recent Log
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Recent Session History:", ln=True)
    pdf.set_font("Arial", '', 10)
    for m in history[-10:]: # Last 10 messages
        role = "VISON" if m['role'] == "assistant" else "USER"
        pdf.multi_cell(0, 6, f"{role}: {m['content']}\n")
        
    return pdf.output(dest='S').encode('latin-1')

# --- PART 4: BRAIN ENGINE ---
def get_mem(u):
    past = db_q('SELECT content FROM chat_log WHERE username=? AND role="user" ORDER BY id DESC LIMIT 15', (u,), True)
    res = db_q('SELECT interests, level, secret_profile FROM users WHERE username=?', (u,), True)
    txt = " ".join([r[0] for r in past]) if past else ""
    return {"i": res[0][0] if res else "General", "l": res[0][1] if res else "HS", "s": res[0][2] if res else "New", "c": txt[-600:]}

def analyze_all(u, sid):
    logs = db_q('SELECT role, content FROM chat_log WHERE username=? AND session_id=? ORDER BY id DESC LIMIT 20', (u, sid), True)
    if not logs: return "Incomplete Data", 0, "💬"
    h = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        evo = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Emotional blocks summary: {h}"}])
        pwr = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Power 0-100 (num only): {h}"}])
        mood = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Pick 1 emoji for mood: {h}"}])
        e, p, m = evo.choices[0].message.content, int(''.join(filter(str.isdigit, pwr.choices[0].message.content))), mood.choices[0].message.content.strip()[0]
        db_q('UPDATE chat_sessions SET mood_emoji=? WHERE session_id=?', (m, sid))
        db_q('UPDATE users SET secret_profile=? WHERE username=?', (e, u))
        return e, p, m
    except: return "Engine Busy", 10, "⏳"

# --- PART 6: SIDEBAR ---
st.set_page_config(page_title="VISON AI", layout="wide")
init_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    logo = get_64(LOGO)
    if logo: st.markdown(f'<center><img src="data:image/jpeg;base64,{logo}" width="150"></center>', unsafe_allow_html=True)
    u, p = st.text_input("User ID"), st.text_input("Security Key", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        if not res: db_q('INSERT INTO users (username, password, interests, level) VALUES (?,?,?,?)', (u.lower(), p, "STEM", "HS"))
        if not res or res[0][0] == p: st.session_state.logged_in, st.session_state.username = True, u.lower(); st.rerun()
    st.stop()

with st.sidebar:
    st.title(f"👤 {st.session_state.username.upper()}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    st.divider()
    
    sessions = db_q('SELECT session_id, session_name, last_modified, mood_emoji FROM chat_sessions WHERE username=? ORDER BY last_modified DESC', (st.session_state.username,), True)
    if st.button("➕ New Session"):
        nid, now = str(uuid.uuid4()), datetime.datetime.now().strftime("%d %b, %H:%M")
        db_q('INSERT INTO chat_sessions VALUES (?,?,?,?,?)', (nid, st.session_state.username, "New Discovery", now, "💬"))
        st.session_state.sid, st.session_state.messages = nid, []; st.rerun()

    if sessions:
        s_list = [f"{s[3]} {s[1]} ({s[2]})" for s in sessions]
        s_dict = {f"{s[3]} {s[1]} ({s[2]})": s[0] for s in sessions}
        sel = st.selectbox("Timeline:", s_list)
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

    if st.session_state.username == ADMIN:
        st.divider()
        with st.expander("🕵️ ADMIN VAULT"):
            if st.button("⚡ Sync & Analyze"):
                e, pw, mo = analyze_all(st.session_state.username, st.session_state.sid)
                st.session_state.evo, st.session_state.pwr = e, pw
            
            if "pwr" in st.session_state:
                st.metric("Power Level", f"{st.session_state.pwr}/100")
                # PDF DOWNLOAD BUTTON
                pdf_data = create_evolution_pdf(st.session_state.username, st.session_state.pwr, st.session_state.evo, st.session_state.messages)
                st.download_button("📄 Download Evolution Report", data=pdf_data, file_name=f"vison_report_{st.session_state.username}.pdf", mime="application/pdf")
                st.write(f"**Analysis:** {st.session_state.evo}")

            if st.button("🗑️ NUCLEAR DATA WIPE"):
                db_q('DELETE FROM chat_log WHERE username=?', (st.session_state.username,))
                db_q('DELETE FROM chat_sessions WHERE username=?', (st.session_state.username,))
                st.rerun()

# --- PART 7: CHAT ---
st.markdown("<h1 style='text-align: center; color: #a252ff;'>🚀 VISON AI CORE</h1>", unsafe_allow_html=True)
if 'sid' not in st.session_state: 
    st.session_state.sid = str(uuid.uuid4())
    db_q('INSERT OR IGNORE INTO chat_sessions VALUES (?,?,?,?,?)', (st.session_state.sid, st.session_state.username, "Initial Entry", datetime.datetime.now().strftime("%d %b, %H:%M"), "💬"))

if "messages" not in st.session_state: st.session_state.messages = []
ai_av = f"data:image/jpeg;base64,{get_64(AVATAR)}" if get_64(AVATAR) else "🤖"

for m in st.session_state.messages: 
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): st.markdown(m["content"])

user_in = st.chat_input("Continue evolution...")
if user_in:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    now = datetime.datetime.now().strftime("%d %b, %H:%M")
    st.session_state.messages.append({"role": "user", "content": user_in})
    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", user_in, st.session_state.sid))
    db_q('UPDATE chat_sessions SET last_modified=? WHERE session_id=?', (now, st.session_state.sid))
    with st.chat_message("user", avatar="👤"): st.markdown(user_in)
    with st.chat_message("assistant", avatar=ai_av):
        m = get_mem(st.session_state.username)
        sys = f"You are a Strict Professor. Personality: {m['i']}. Evolution Context: {m['s']}"
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":sys}]+st.session_state.messages)
        ans = res.choices[0].message.content; st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))

components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)
