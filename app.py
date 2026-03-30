import streamlit as st
import sqlite3, base64, os, time, uuid, datetime
import streamlit.components.v1 as components
import math
from groq import Groq

# --- PART 1: SETTINGS & DATABASE ---
LOGO_FILENAME = "vison_logo.jpg"
AI_AVATAR_FILENAME = "ai_logo_glow.jpg"
ADMIN = "0102383"

def get_64(p):
    if os.path.exists(p):
        with open(p, "rb") as f: 
            return base64.b64encode(f.read()).decode()
    return None

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
    db_q('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, email TEXT, interests TEXT, level TEXT, secret_profile TEXT DEFAULT 'No data yet.')''')
    try: 
        db_q('ALTER TABLE users ADD COLUMN email TEXT') 
    except: 
        pass
    db_q('''CREATE TABLE IF NOT EXISTS chat_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, session_id TEXT)''')
    db_q('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, username TEXT, session_name TEXT, last_modified TEXT, mood_emoji TEXT DEFAULT '💬')''')

# --- PART 2: CASIO CLASSWIZ ENGINE (UPGRADED UI) ---
def render_casio_calculator():
    CALC_HTML = """
    <style>
        body { background-color: transparent; color: white; font-family: 'Arial', sans-serif; margin: 0; display: flex; justify-content: center;}
        .calc-body { 
            background: #222; 
            background-image: radial-gradient(#333 15%, transparent 16%), radial-gradient(#333 15%, transparent 16%);
            background-size: 6px 6px; 
            background-position: 0 0, 3px 3px;
            border: 2px solid #ddd; 
            border-radius: 20px; 
            width: 100%; 
            max-width: 320px; 
            padding: 20px 15px; 
            box-shadow: 0px 15px 35px rgba(0,0,0,0.8), inset 0px 0px 10px rgba(0,0,0,0.5); 
        }
        .brand-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 10px; }
        .brand-name { font-size: 16px; font-weight: 900; letter-spacing: 1px; color: #eee; }
        .model-name { font-size: 11px; font-style: italic; color: #ccc; }
        .calc-screen { 
            background-color: #b5bdad; 
            color: #111; 
            font-family: 'Courier New', monospace; 
            font-size: 28px; 
            text-align: right; 
            padding: 10px; 
            height: 60px; 
            border-radius: 5px; 
            margin-bottom: 20px; 
            border: inset 3px #888; 
            box-shadow: inset 2px 2px 5px rgba(0,0,0,0.3);
            overflow: hidden;
            display: flex;
            align-items: flex-end;
            justify-content: flex-end;
        }
        
        .grid-5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px 6px; margin-top: 15px;}
        .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px 6px; margin-top: 10px; padding: 0 10px;}
        
        button { 
            height: 35px; 
            border-radius: 4px; 
            border: none; 
            font-size: 14px; 
            font-weight: bold; 
            cursor: pointer; 
            box-shadow: 0px 3px 0px rgba(0,0,0,0.5);
            transition: all 0.1s; 
            display: flex;
            align-items: center;
            justify-content: center;
        }
        button:active { transform: translateY(3px); box-shadow: 0px 0px 0px rgba(0,0,0,0.5); }
        
        .btn-num { background-color: #f0f0f0; color: #111; border-top: 1px solid #fff; }
        .btn-op { background-color: #333; color: white; border-top: 1px solid #555; }
        .btn-del-ac { background-color: #2a52be; color: white; border-top: 1px solid #5a7add;}
        .btn-sci { background-color: #111; color: #ddd; font-size: 11px; height: 28px; border-radius: 8px; box-shadow: 0px 2px 0px rgba(0,0,0,0.6);}
        
        .d-pad-container { display: flex; justify-content: center; margin: 15px 0; }
        .d-pad { 
            width: 80px; height: 60px; background: #ddd; border-radius: 40px; 
            position: relative; box-shadow: inset 0px 0px 5px #555, 0px 5px 10px rgba(0,0,0,0.5);
            background: linear-gradient(135deg, #e0e0e0, #999);
        }
    </style>
    <div class="calc-body">
        <div class="brand-header">
            <span class="brand-name">CASIO</span>
            <span class="model-name">fx-570EX <span style="color:#d9534f;">CLASSWIZ</span></span>
        </div>
        <div id="screen" class="calc-screen">0</div>
        
        <!-- Fake D-Pad for visual accuracy -->
        <div class="d-pad-container">
            <div class="d-pad"></div>
        </div>

        <!-- Scientific Function Row (Simulated) -->
        <div class="grid-4">
            <button class="btn-sci" onclick="press('Math.sin(')">sin</button>
            <button class="btn-sci" onclick="press('Math.cos(')">cos</button>
            <button class="btn-sci" onclick="press('Math.tan(')">tan</button>
            <button class="btn-sci" onclick="press('Math.log10(')">log</button>
            <button class="btn-sci" onclick="press('Math.sqrt(')">√</button>
            <button class="btn-sci" onclick="press('**2')">x²</button>
            <button class="btn-sci" onclick="press('**')">x^</button>
            <button class="btn-sci" onclick="press('Math.log(')">ln</button>
        </div>

        <!-- Main Numpad -->
        <div class="grid-5">
            <button class="btn-num" onclick="press('7')">7</button>
            <button class="btn-num" onclick="press('8')">8</button>
            <button class="btn-num" onclick="press('9')">9</button>
            <button class="btn-del-ac" onclick="backspace()">DEL</button>
            <button class="btn-del-ac" onclick="clear_screen()">AC</button>
            
            <button class="btn-num" onclick="press('4')">4</button>
            <button class="btn-num" onclick="press('5')">5</button>
            <button class="btn-num" onclick="press('6')">6</button>
            <button class="btn-op" onclick="press('*')">×</button>
            <button class="btn-op" onclick="press('/')">÷</button>
            
            <button class="btn-num" onclick="press('1')">1</button>
            <button class="btn-num" onclick="press('2')">2</button>
            <button class="btn-num" onclick="press('3')">3</button>
            <button class="btn-op" onclick="press('+')">+</button>
            <button class="btn-op" onclick="press('-')">-</button>
            
            <button class="btn-num" onclick="press('0')">0</button>
            <button class="btn-num" onclick="press('.')">.</button>
            <button class="btn-op" onclick="press('*10**')">x10ˣ</button>
            <button class="btn-num" onclick="press('Ans')">Ans</button>
            <button class="btn-op" onclick="calculate()">=</button>
        </div>
    </div>
    <script>
        let expr = "";
        let ans = 0;
        const screen = document.getElementById("screen");
        
        function press(v) { 
            if(expr === "Error" || screen.innerText === "Error") expr = "";
            expr += v; 
            screen.innerText = expr.replace(/Math\\./g, '').replace(/\\*\\*2/g, '²').replace(/\\*\\*/g, '^'); 
        }
        function clear_screen() { 
            expr = ""; 
            screen.innerText = "0"; 
        }
        function backspace() {
            expr = expr.slice(0, -1);
            screen.innerText = expr === "" ? "0" : expr.replace(/Math\\./g, '').replace(/\\*\\*2/g, '²').replace(/\\*\\*/g, '^');
        }
        function calculate() { 
            try { 
                let evalExpr = expr.replace(/Ans/g, ans);
                let result = eval(evalExpr); 
                // Fix precision issues
                result = Math.round(result * 100000000) / 100000000;
                ans = result;
                screen.innerText = result; 
                expr = result.toString();
            } catch(e) { 
                screen.innerText = "Error"; 
                expr = "";
            } 
        }
    </script>
    """
    components.html(CALC_HTML, height=520)

# --- PART 3: UI SETUP & AUTH (RESTORED GATEWAY) ---
st.set_page_config(page_title="VISON AI STEM", layout="wide")
init_db()

if 'logged_in' not in st.session_state: 
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    lb = get_64(LOGO_FILENAME)
    if lb: 
        st.markdown(f'<center><img src="data:image/jpeg;base64,{lb}" width="180"></center>', unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>VISON CORE</h1>", unsafe_allow_html=True)
    
    auth_mode = st.radio("Access Portal", ["Log In", "Create Account", "Reset Password"], horizontal=True)
    
    if auth_mode == "Log In":
        st.subheader("Welcome Back")
        identifier = st.text_input("Email (or Admin ID)")
        p = st.text_input("Security Key", type="password")
        if st.button("Unlock Core"):
            if identifier and p:
                res = db_q('SELECT password, username FROM users WHERE email=? OR username=?', (identifier.lower(), identifier), True)
                if res and res[0][0] == p:
                    st.session_state.logged_in = True
                    st.session_state.username = res[0][1] 
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials.")
            else: 
                st.warning("⚠️ Please fill in all fields.")
                
    elif auth_mode == "Create Account":
        st.subheader("Initialize New Student")
        new_u = st.text_input("Choose a User ID")
        new_e = st.text_input("Email Address")
        new_p = st.text_input("Create Security Key", type="password")
        new_p2 = st.text_input("Confirm Security Key", type="password")
        
        if st.button("Register Account"):
            if new_u and new_e and new_p and new_p2:
                if "@" not in new_e: 
                    st.error("❌ Please enter a valid email address.")
                elif new_p == new_p2:
                    res = db_q('SELECT username FROM users WHERE username=? OR email=?', (new_u.lower(), new_e.lower()), True)
                    if res: 
                        st.error("❌ User ID or Email already registered.")
                    else:
                        db_q('INSERT INTO users (username, password, email, interests, level) VALUES (?,?,?,?,?)', (new_u.lower(), new_p, new_e.lower(), "STEM", "HS"))
                        st.success("✅ Account created! Switch to 'Log In'.")
                else: 
                    st.error("❌ Security Keys do not match.")
            else: 
                st.warning("⚠️ Please fill in all fields.")
                
    elif auth_mode == "Reset Password":
        st.subheader("System Override: Reset Key")
        r_e = st.text_input("Registered Email")
        r_p = st.text_input("New Security Key", type="password")
        r_p2 = st.text_input("Confirm New Key", type="password")
        
        if st.button("Execute Reset"):
            if r_e and r_p and r_p2:
                if r_p == r_p2:
                    res = db_q('SELECT username FROM users WHERE email=?', (r_e.lower(),), True)
                    if res:
                        db_q('UPDATE users SET password=? WHERE email=?', (r_p, r_e.lower()))
                        st.success("✅ Security Key updated! Switch to 'Log In'.")
                    else: 
                        st.error("❌ Email not found.")
                else: 
                    st.error("❌ Keys do not match.")
            else: 
                st.warning("⚠️ Please fill in all fields.")

    st.stop()

# --- PART 4: SIDEBAR ---
with st.sidebar:
    st.title(f"🚀 {st.session_state.username.upper()}")
    if st.button("Logout"): 
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    render_casio_calculator()
    st.divider()

    persona = st.selectbox("Persona", ["Strict Professor", "Friendly Mentor"])
    lang = st.selectbox("Language", ["English", "Japanese", "Bahasa Melayu"])
    uploaded_file = st.file_uploader("📷 Solve STEM Equation", type=['png', 'jpg', 'jpeg'])
    
    sessions = db_q('SELECT session_id, session_name FROM chat_sessions WHERE username=? ORDER BY last_modified DESC', (st.session_state.username,), True)
    if st.button("➕ New Session"):
        nid = str(uuid.uuid4())
        db_q('INSERT INTO chat_sessions (session_id, username, session_name, last_modified) VALUES (?,?,?,?)', (nid, st.session_state.username, "New Session", "Now"))
        st.session_state.sid = nid
        st.rerun()
    
    if sessions:
        s_dict = {s[1]: s[0] for s in sessions}
        sel = st.selectbox("Sessions", list(s_dict.keys()))
        st.session_state.sid = s_dict[sel]
        st.session_state.messages = [{"role":r, "content":c} for r,c in db_q('SELECT role, content FROM chat_log WHERE session_id=?', (st.session_state.sid,), True)]

# --- PART 5: CHAT LOGIC & EVOLUTION ENGINE ---
if 'sid' not in st.session_state:
    st.session_state.sid = str(uuid.uuid4())
    db_q('INSERT OR IGNORE INTO chat_sessions (session_id, username, session_name, last_modified) VALUES (?,?,?,?)', (st.session_state.sid, st.session_state.username, "Main Chat", "Now"))

if "messages" not in st.session_state: 
    st.session_state.messages = []

ai_av = f"data:image/png;base64,{get_64(AI_AVATAR_FILENAME)}" if get_64(AI_AVATAR_FILENAME) else "🤖"
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=ai_av if m["role"]=="assistant" else "👤"): 
        st.markdown(m["content"])

user_in = st.chat_input("Ask a question, or type 'Evolve: <command>'...")

# ==========================================
# 🧬 THE EVOLUTION ENGINE: STAGING AREA
# ==========================================
if st.session_state.get("pending_mutation"):
    st.divider()
    st.markdown("## 🔬 Review Proposed DNA Mutation")
    st.warning("⚠️ **WARNING:** Approving this will permanently overwrite the `app.py` file on your server.")
    
    st.code(st.session_state.pending_mutation, language="python")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚠️ APPROVE & OVERWRITE APP", type="primary", use_container_width=True):
            try:
                with open(__file__, "w", encoding="utf-8") as file:
                    file.write(st.session_state.pending_mutation)
                del st.session_state["pending_mutation"]
                st.success("✅ App successfully evolved! Rebooting core...")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to write file: {e}")
    with col2:
        if st.button("❌ REJECT MUTATION", use_container_width=True):
            del st.session_state["pending_mutation"]
            st.info("Evolution aborted. Core remains unchanged.")
            st.rerun()
            
    st.stop()

# ==========================================
# NORMAL CHAT & EVOLUTION TRIGGER
# ==========================================
if user_in or uploaded_file:
    if "GROQ_API_KEY" not in st.secrets:
        st.error("🚨 **API Key Missing!** Please add `GROQ_API_KEY` to Streamlit Secrets.")
        st.stop()

    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    # 🧬 INTERCEPT: IS IT AN EVOLVE COMMAND?
    if user_in and user_in.lower().startswith("evolve:"):
        with st.spinner("🧬 Synthesizing new application DNA... Please wait (this takes about 10-20 seconds)."):
            with open(__file__, "r", encoding="utf-8") as file:
                current_code = file.read()
                
            system_prompt = """
            You are an auto-evolving AI expert in Python and Streamlit.
            The user wants to add a feature or alter the current script.
            You MUST output the ENTIRE, COMPLETE updated Python code for the app.
            DO NOT output explanations, introductory text, or conversational text.
            Output ONLY raw, valid, properly indented Python code.
            """
            
            try:
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Current Code:\n{current_code}\n\nRequested Evolution: {user_in}"}
                    ]
                )
                
                proposed_code = res.choices[0].message.content.strip()
                
                # Robust stripping of markdown to prevent syntax errors
                if proposed_code.startswith("```python"):
                    proposed_code = proposed_code.split("```python", 1)[1]
                elif proposed_code.startswith("```"):
                    proposed_code = proposed_code.split("```", 1)[1]
                    
                if proposed_code.endswith("```"):
                    proposed_code = proposed_code.rsplit("```", 1)[0]
                    
                st.session_state.pending_mutation = proposed_code.strip()
                st.rerun() 
                
            except Exception as e:
                st.error(f"Evolution failed to synthesize: {e}")
                st.stop()

    # --- NORMAL CHAT FLOW ---
    try:
        model_to_use = "llama-3.2-11b-vision-preview" if uploaded_file else "llama-3.3-70b-versatile"
        display_text = user_in if user_in else "Analyze this image."
        
        if uploaded_file:
            mime_type = uploaded_file.type 
            img_b64 = base64.b64encode(uploaded_file.getvalue()).decode()
            content_payload = [{"type": "text", "text": display_text}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{img_b64}"}}]
            with st.chat_message("user", avatar="👤"):
                st.image(uploaded_file, width=300)
                st.markdown(display_text)
        else:
            content_payload = display_text
            with st.chat_message("user", avatar="👤"):
                st.markdown(display_text)

        db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "user", display_text, st.session_state.sid))
        st.session_state.messages.append({"role": "user", "content": display_text})

        with st.chat_message("assistant", avatar=ai_av):
            sys_prompt = f"You are a {persona} in {lang}. Use LaTeX ($) for math."
            hist = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-8:-1]]
            
            if uploaded_file:
                final_messages = hist + [{"role": "user", "content": content_payload}]
            else:
                final_messages = [{"role": "system", "content": sys_prompt}] + hist + [{"role": "user", "content": display_text}]
            
            res = client.chat.completions.create(model=model_to_use, messages=final_messages)
            ans = res.choices[0].message.content
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            db_q('INSERT INTO chat_log (username, role, content, session_id) VALUES (?,?,?,?)', (st.session_state.username, "assistant", ans, st.session_state.sid))

    except Exception as e:
        if "AuthenticationError" in str(e) or "401" in str(e):
            st.error("🚨 **Authentication Failed!** Your Groq API key is invalid or expired.")
        else:
            st.error(f"⚠️ **Engine Error:** {e}")

components.html("<script>window.parent.document.querySelectorAll('.stChatMessage').forEach(el => el.scrollIntoView({behavior:'smooth'}));</script>", height=0)
