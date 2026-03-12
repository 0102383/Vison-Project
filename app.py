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
    c = conn.cursor(); c.execute(q, d)
    res = c.fetchall() if fetch else None
    conn.commit(); conn.close(); return res

def init_db():
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT, mood_emoji TEXT DEFAULT '💬')''')

# --- PART 4: BRAIN & STATS ---
def get_mem(u):
    past = db_q('SELECT content FROM chat_log WHERE username=? AND role="user" ORDER BY id DESC LIMIT 15', (u,), True)
    res = db_q('SELECT interests, level, secret_profile FROM users WHERE username=?', (u,), True)
    txt = " ".join([r[0] for r in past])
    return {"i": res[0][0] if res else "STEM", "l": res[0][1] if res else "HS", "s": res[0][2] if res else "None", "c": txt[-600:]}

def analyze_all(u, sid):
    logs = db_q('SELECT role, content FROM chat_log WHERE username=? AND session_id=? ORDER BY id DESC LIMIT 20', (u, sid), True)
    if not logs: return "No data yet. Chat more!", 10, "💬"
    h = " ".join([f"{r}: {c}" for r, c in logs])
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        evo = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Summarize emotional blocks/feelings: {h}"}])
        pwr = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Academic Power 0-100 (Num only): {h}"}])
        mood = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Pick 1 emoji for mood: {h}"}])
        m_emo = mood.choices[0].message.content.strip()[0]
        db_q('UPDATE chat_sessions SET mood_emoji=? WHERE session_id=?', (m_emo, sid))
        return evo.choices[0].message.content, int(''.join(filter(str.isdigit, pwr.choices[0].message.content))), m_emo
    except: return "Engine Error", 10, "⚠️"

# --- PART 6: SIDEBAR ---
st.set_page_config(page_title="VISON AI", layout="wide")
init_db()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    logo = get_64(LOGO)
    if logo: st.markdown(f'<center><img src="data:image/jpeg;base64,{logo}" width="180"></center>', unsafe_allow_html=True)
    u, p = st.text_input("User"), st.text_input("Pass", type="password")
    if st.button("Unlock"):
        res = db_q('SELECT password FROM users WHERE username=?', (u.lower(),), True)
        # --- FIXED LINE BELOW ---
        if not res: db_q('INSERT INTO users VALUES (?,?,?,?,?)', (u.lower(), p, "STEM", "HS", "New Student"))
        if not res or res[0][0] == p: st.session_state.logged_in, st.session_state.username = True, u.lower(); st.rerun()
    st.stop()

with st.sidebar:
    st.title(f"👤 {st.session_state.username}")
    if st.button("Logout"): st.session_state.clear(); st.rerun()
    st.divider()
    st.subheader("📁 Chat History")
    sessions = db_q('SELECT session_id, session_name, last_modified, mood_emoji FROM chat_sessions WHERE username=? ORDER BY last_modified DESC', (st.session_state.username,), True)
    if st.button("➕ New Chat"):
        nid, now = str(uuid.uuid4()), datetime.datetime.now().strftime("%d %b, %H:%M")
        db_q('INSERT INTO chat_sessions VALUES (?,?,?,?,?)', (nid, st.session_state.username, "New Chat", now, "💬"))
        st.session_state.sid, st.session_state.messages = nid, []; st.rerun()
    if sessions:
        s_list = [f"{m_e} {name} ({mod})" for sid, name, mod, m_e in sessions]
        s_dict = {f"{m_e} {name} ({mod})": sid for sid, name, mod, m_e in sessions}
        sel = st.selectbox("Jump to past chat:", s_list)
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]
        with st.expander("📝 Rename Current Chat"):
            n_name = st.text_input("New Name", value=sel.split(' (')[0][2:])
            if st.button("Update Name"): db_q('UPDATE chat_sessions SET session_name=? WHERE session_id=?', (n_name, st.session_state.sid)); st.rerun()
    st.divider()
    st.subheader("📝 Quick Quiz")
    if st.button("Setup & Start Quiz"): st.info("Quiz Engine integration coming in V4.0!")
    if st.session_state.username == ADMIN:
        with st.expander("🕵️ Admin Vault"):
            if st.button("⚡ Sync Current Session"):
                e, pw, mo = analyze_all(st.session_state.username, st.session_state.sid)
                db_q('UPDATE users SET secret_profile=? WHERE username=?', (e, st.session_state.username))
                st.session_state.evo, st.session_state.pwr = e, pw
            if "pwr" in st.session_state: st.metric("Power Level", f"{st.session_state.pwr}/100"); st.write(st.session_state.evo)
            for un, ui, us in db_q('SELECT username, interests, secret_profile FROM users', fetch=True):
                st.write(f"**{un}**: {us}"); st.divider()

# --- PART 7: CHAT ---
st.markdown("<h1 style='text-align: center; color: #a252ff;'>🚀 VISON AI CORE</h1>", unsafe_allow_html=True)
if 'sid' not in st.session_state: 
    st.session_state.sid = str(uuid.uuid4())
    db_q('INSERT OR IGNORE INTO chat_sessions VALUES (?,?,?,?,?)', (st.session_state.sid, st.session_state.username, "Initial Chat", datetime.datetime.now().strftime("%d %b, %H:%M"), "💬"))
if "messages" not in st.session_state: st.session_state.messages = []
ai_av = f"data:image/jpeg;base64,{get_64(AVATAR)}" if get_64(AVATAR) else "🤖"
for m in st.session_state.messages: 
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): st.markdown(m["content"])
user_in = st.chat_input("How can I help you evolve today?")
if user_in:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    now = datetime.datetime.now().strftime("%d %b, %H:%M")
    st.session_state.messages.append({"role": "user", "content": user_in})
    db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", user_in, st.session_state.sid))
    db_q('UPDATE chat_sessions SET last_modified=? WHERE session_id=?', (now, st.session_state.sid))
    with st.chat_message("user", avatar="👤"): st.markdown(user_in)
    with st.chat_message("assistant", avatar=ai_av):
        mem = get_mem(st.session_state.username)
        sys = f"You are a Strict Professor. Context: {mem['c']}. Personality: {mem['i']}. Evolution: {mem['s']}"
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":sys}]+st.session_state.messages)
        ans = res.choices[0].message.content; st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))
components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)
