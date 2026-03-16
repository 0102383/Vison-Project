import streamlit as st
import streamlit.components.v1 as components

# --- STEP 1: DEFINE THE CSS (THE HARDWARE LOOK) ---
CALC_CSS = """
<style>
    body { background-color: #0e1117; color: white; font-family: sans-serif; }
    .calc-body { background: #333; border: 4px solid #fff; border-radius: 15px; width: 320px; padding: 15px; box-shadow: 0px 10px 30px rgba(0,0,0,0.7); }
    .calc-screen { background-color: #a8b0a0; color: black; font-family: 'Courier New', monospace; font-size: 24px; text-align: right; padding: 10px; height: 50px; border-radius: 5px; margin-bottom: 15px; border: 2px solid #555; overflow: hidden;}
    .btn-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    button { height: 45px; border-radius: 5px; border: 1px solid #555; font-size: 18px; font-weight: bold; cursor: pointer; transition: 0.1s; }
    button:active { transform: translateY(2px); }
    .btn-num { background-color: white; color: black; }
    .btn-op { background-color: #555; color: white; }
    .btn-del-ac { background-color: #2a52be; color: white; }
    .btn-sci { background-color: #777; color: white; font-size: 14px;}
</style>
"""

# --- STEP 2: DEFINE THE HTML & JS (THE OS) ---
# We use eval() here for simplicity, but in production we should use a safer library like math.js
CALC_HTML_JS = """
<div class="calc-body">
    <div style="font-size:12px; font-weight:bold;">CASIO <span style="font-size:10px; color:#aaa; font-weight:normal;">fx-570EX CLASSWIZ</span></div>
    <div id="screen" class="calc-screen">0</div>
    
    <div class="btn-grid">
        <button class="btn-sci" onclick="press('sin(')">sin</button>
        <button class="btn-sci" onclick="press('cos(')">cos</button>
        <button class="btn-sci" onclick="press('tan(')">tan</button>
        <button class="btn-sci" onclick="press('sqrt(')">sqrt</button>
        
        <button class="btn-num" onclick="press('7')">7</button>
        <button class="btn-num" onclick="press('8')">8</button>
        <button class="btn-num" onclick="press('9')">9</button>
        <button class="btn-del-ac" onclick="clear_screen()">AC</button>
        
        <button class="btn-num" onclick="press('4')">4</button>
        <button class="btn-num" onclick="press('5')">5</button>
        <button class="btn-num" onclick="press('6')">6</button>
        <button class="btn-op" onclick="press('*')">×</button>
        
        <button class="btn-num" onclick="press('1')">1</button>
        <button class="btn-num" onclick="press('2')">2</button>
        <button class="btn-num" onclick="press('3')">3</button>
        <button class="btn-op" onclick="press('/')">÷</button>
        
        <button class="btn-num" onclick="press('0')">0</button>
        <button class="btn-num" onclick="press('.')">.</button>
        <button class="btn-num" onclick="press('Math.PI')">π</button>
        <button class="btn-op" onclick="press('-')">-</button>
        
        <button class="btn-op" style="grid-column: span 3;" onclick="press('+')">+</button>
        <button class="btn-op" onclick="calculate()">=</button>
    </div>
</div>

<script>
    let expr = "";
    function press(v) { expr += v; document.getElementById("screen").innerText = expr; }
    function clear_screen() { expr = ""; document.getElementById("screen").innerText = "0"; }
    function calculate() { try { document.getElementById("screen").innerText = eval(expr); } catch { document.getElementById("screen").innerText = "Error"; } }
</script>
"""

# --- STEP 3: ASSEMBLE ---
def draw_calculator():
    full_code = CALC_CSS + CALC_HTML_JS
    # We host it in an iframe sandbox (height=450)
    components.html(full_code, height=450, width=350, scrolling=False)

# --- STEP 4: TEST IN STREAMLIT ---
st.set_page_config(layout="centered")
st.markdown("<h1 style='text-align: center; color: white;'>VISON CLASSWIZ 0.1</h1>", unsafe_allow_html=True)
draw_calculator()
st.info("Testing the JavaScript math engine. AI integration (OPTN/QR) is disabled in this prototype.")
