import time
import html
import streamlit as st

# ---------------------- Page & Styles ----------------------
st.set_page_config(page_title="RapStar Lyrics Studio", page_icon="🎵", layout="centered")

# Animated CSS (gradient title, floating stars, blinking cursor, fade-in lines)
st.markdown("""
<style>
/* Page background + subtle floating stars */
.main > div { 
  background: radial-gradient(1200px 600px at 20% -10%, rgba(0, 176, 255, .10), transparent 60%),
              radial-gradient(900px 500px at 120% 10%, rgba(255, 0, 132, .10), transparent 60%),
              #0b0f14;
}
@keyframes floatStar {
  0% { transform: translateY(0px) translateX(0px); opacity:.5; }
  50% { transform: translateY(-12px) translateX(6px); opacity:.9; }
  100% { transform: translateY(0px) translateX(0px); opacity:.5; }
}
.starfield { position: fixed; inset: 0; pointer-events:none; z-index:0; }
.star { position:absolute; width:3px; height:3px; background:#7dd3fc; border-radius:50%; animation: floatStar 6s ease-in-out infinite; }

/* Animated gradient heading */
h1.rapstar-title {
  font-weight: 900 !important;
  background: linear-gradient(90deg, #06b6d4, #a78bfa, #22d3ee, #f472b6);
  background-size: 300% 300%;
  -webkit-background-clip: text; background-clip: text; color: transparent;
  animation: gradientShift 6s ease infinite;
  letter-spacing: .5px;
}
@keyframes gradientShift { 
  0%{background-position:0% 50%} 
  50%{background-position:100% 50%} 
  100%{background-position:0% 50%}
}

/* Typewriter cursor */
.cursor::after {
  content: "▍";
  margin-left: 2px;
  animation: blink 1s steps(1) infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* Fade-in lines */
@keyframes fadeInUp {
  from { opacity:0; transform: translateY(6px); } 
  to { opacity:1; transform: translateY(0); }
}
.fade-line { animation: fadeInUp .3s ease both; }

/* Output panel */
.output-box {
  background: rgba(15, 23, 42, .6);
  border: 1px solid rgba(148, 163, 184, .15);
  border-radius: 12px;
  padding: 16px 18px;
  font-family: ui-monospace, "JetBrains Mono", Menlo, Consolas, monospace;
  color: #e2e8f0;
  white-space: pre-wrap;
  line-height: 1.5;
}

/* Search highlight */
mark {
  background: #fde68a;
  color: #1f2937;
  padding: 0 .1rem;
  border-radius: .2rem;
}
</style>
<div class="starfield">
  <!-- A few decorative stars -->
  <div class="star" style="left:8%; top:22%; animation-delay:.0s;"></div>
  <div class="star" style="left:18%; top:62%; animation-delay:.6s;"></div>
  <div class="star" style="left:66%; top:18%; animation-delay:.3s;"></div>
  <div class="star" style="left:78%; top:58%; animation-delay:1.0s;"></div>
  <div class="star" style="left:42%; top:38%; animation-delay:1.6s;"></div>
</div>
""", unsafe_allow_html=True)

st.markdown('<h1 class="rapstar-title">🎶 RapStar Lyrics Studio</h1>', unsafe_allow_html=True)
st.caption("Paste or upload lyrics/text. Play the **typewriter** animation, highlight words, and export. (No copyrighted text included by default.)")

# ---------------------- Session State ----------------------
def init_state():
    defaults = {
        "raw_text": "",
        "render_index": 0,         # where the typewriter currently is
        "is_animating": False,
        "use_line_mode": False,    # per-character vs per-line animation
        "highlight_term": "",
        "animated_output": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ---------------------- Sidebar Controls ----------------------
with st.sidebar:
    st.header("⚙️ Controls")
    st.write("**Input**")
    uploaded = st.file_uploader("Upload .txt", type=["txt"])
    if uploaded is not None:
        text_data = uploaded.read().decode("utf-8", errors="ignore")
        st.session_state.raw_text = text_data
        st.success("Loaded text from file.")

    st.session_state.raw_text = st.text_area(
        "Or paste text here",
        value=st.session_state.raw_text or "Paste your lyrics or any text in this box.",
        height=200
    )

    st.write("**Animation**")
    st.session_state.use_line_mode = st.toggle("Animate by line (faster)", value=False)
    char_delay = st.slider("Delay per character (seconds)", 0.00, 0.10, 0.02, 0.01, help="Used when 'Animate by line' is OFF.")
    line_delay = st.slider("Delay per line (seconds)", 0.00, 0.60, 0.15, 0.01, help="Used when 'Animate by line' is ON.")

    st.write("**Search/Highlight**")
    st.session_state.highlight_term = st.text_input("Highlight term (optional)")

    st.write("**Export**")
    if st.session_state.raw_text.strip():
        st.download_button("💾 Download current text", st.session_state.raw_text, file_name="lyrics.txt")

    st.divider()
    st.caption("Tip: Use a short delay on Streamlit Cloud so the animation feels smooth.")

# ---------------------- Helper Functions ----------------------
def highlight_html(text: str, term: str) -> str:
    """Return HTML with <mark> around case-insensitive matches."""
    safe = html.escape(text)
    if not term.strip():
        return safe
    import re
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{html.escape(m.group(0))}</mark>", safe)

def reset_animation():
    st.session_state.render_index = 0
    st.session_state.animated_output = ""
    st.session_state.is_animating = False

def play_animation():
    txt = st.session_state.raw_text or ""
    if not txt.strip():
        st.warning("Paste or upload some text first.")
        return

    st.session_state.is_animating = True
    placeholder = st.empty()

    if st.session_state.use_line_mode:
        # Per-line animation
        lines = txt.splitlines()
        out = []
        for i, ln in enumerate(lines):
            # build HTML with fade-in per line
            safe_line = html.escape(ln)
            out.append(f'<div class="fade-line">{safe_line}</div>')
            # Add a blinking cursor after last visible line
            html_block = '<div class="output-box">' + "\n".join(out) + '<span class="cursor"></span></div>'
            # Apply highlight after we assemble
            if st.session_state.highlight_term.strip():
                html_block = html_block.replace(
                    safe_line,
                    highlight_html(ln, st.session_state.highlight_term)
                )
            placeholder.markdown(html_block, unsafe_allow_html=True)
            time.sleep(line_delay)
            if not st.session_state.is_animating:
                break
        st.session_state.animated_output = "\n".join(lines)
        st.session_state.is_animating = False
        st.success("✅ Animation finished.")
        st.balloons()
    else:
        # Per-character typewriter (with blinking cursor)
        text_chars = list(txt)
        built = []
        for i, ch in enumerate(text_chars):
            built.append(ch)
            # Escape + highlight each frame (efficient enough for lyrics length)
            partial = "".join(built)
            safe_partial = highlight_html(partial, st.session_state.highlight_term)
            html_block = f'<div class="output-box"><span class="cursor">{safe_partial}</span></div>'
            placeholder.markdown(html_block, unsafe_allow_html=True)
            time.sleep(char_delay)
            if not st.session_state.is_animating:
                break
        st.session_state.animated_output = "".join(built)
        st.session_state.is_animating = False
        st.success("✅ Animation finished.")
        st.snow()

# ---------------------- Main UI ----------------------
c1, c2, c3 = st.columns(3)
play = c1.button("▶ Play")
stop = c2.button("⏹ Stop")
clear = c3.button("🧹 Reset")

if play:
    reset_animation()
    play_animation()

if stop:
    # Just flip the flag: loop checks it between frames
    st.session_state.is_animating = False

if clear:
    reset_animation()
    st.toast("Cleared.", icon="🧼")

# Live preview (static, with highlight)
st.subheader("Live Preview")
preview_html = f'<div class="output-box">{highlight_html(st.session_state.raw_text, st.session_state.highlight_term)}</div>'
st.markdown(preview_html, unsafe_allow_html=True)

# Stats
text = st.session_state.raw_text or ""
chars = len(text)
words = len(text.split())
lines = len(text.splitlines())
st.caption(f"**{chars}** chars • **{words}** words • **{lines}** lines")
