import re
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="CleanSight",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)

with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, p, div, span, h1, h2, h3, h4, h5, h6, label, button, input, textarea, li, td, th {
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stIconMaterial"], [data-testid="stExpanderIcon"],
.material-symbols-rounded, .material-symbols-outlined, .material-icons {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    display: block !important;
    visibility: visible !important;
    width: 260px !important;
    background-color: #1A1D27 !important;
    border-right: 0.5px solid rgba(255,255,255,0.07) !important;
}

/* Uploader — button sits directly above the hint line */
[data-testid="stFileUploader"] > div > div:first-child { display: none !important; }
[data-testid="stFileUploaderDropzone"] {
    position: relative !important;
    display: block !important;
    background: linear-gradient(180deg, rgba(20,184,166,0.05), #12151F 70%) !important;
    border: 1.5px dashed rgba(20,184,166,0.45) !important;
    border-radius: 14px !important;
    padding: 0 !important;
    height: 140px !important;
    box-sizing: border-box !important;
    transition: border-color .2s, background .2s;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #14B8A6 !important;
    background: linear-gradient(180deg, rgba(20,184,166,0.10), #12151F 75%) !important;
}
[data-testid="stFileUploaderDropzone"] * {
    color: #8B8FA8 !important;
    background: transparent !important;
}
/* hint text: centered line below the button */
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzone"] > div:not(:has(button)) {
    position: absolute !important;
    top: 88px !important;
    left: 0 !important;
    right: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    text-align: center !important;
    display: flex !important;
    justify-content: center !important;
}
/* upload button: centered, just above the hint */
[data-testid="stFileUploaderDropzone"] button {
    position: absolute !important;
    top: 30px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    margin: 0 !important;
    padding: 8px 28px !important;
    font-weight: 600 !important;
    background: rgba(20,184,166,0.18) !important;
    color: #5EEAD4 !important;
    border: 0.5px solid rgba(20,184,166,0.5) !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploaderDropzone"] button * { color: #5EEAD4 !important; }
[data-testid="stFileUploaderDropzone"] button:hover {
    background: rgba(20,184,166,0.30) !important;
}

/* Hero */
.cs-hero {
    position: relative;
    overflow: hidden;
    border-radius: 22px;
    border: 0.5px solid rgba(20,184,166,0.22);
    padding: 44px 48px;
    margin-bottom: 36px;
    background:
        radial-gradient(520px 260px at 92% 0%, rgba(20,184,166,0.22), transparent 65%),
        radial-gradient(420px 240px at 0% 100%, rgba(127,119,221,0.14), transparent 65%),
        radial-gradient(rgba(255,255,255,0.045) 1px, transparent 1px),
        #14171F;
    background-size: auto, auto, 22px 22px, auto;
}
.cs-hero-inner { display: flex; align-items: center; justify-content: space-between; gap: 40px; }
.cs-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(20,184,166,0.10); border: 0.5px solid rgba(20,184,166,0.3);
    border-radius: 99px; padding: 5px 15px; font-size: 12px; font-weight: 500;
    color: #5EEAD4; margin-bottom: 22px; letter-spacing: 0.05em;
}
.cs-dot {
    width: 7px; height: 7px; border-radius: 50%; background: #14B8A6;
    animation: cs-pulse 2s ease-in-out infinite;
}
@keyframes cs-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(20,184,166,0.6); }
    50% { box-shadow: 0 0 0 7px rgba(20,184,166,0); }
}
.cs-grad {
    background: linear-gradient(90deg, #14B8A6, #5EEAD4 60%, #A7F3D0);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent !important;
}
.cs-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 26px; }
.cs-chip {
    font-size: 12px; color: #B8BCCC; padding: 6px 13px; border-radius: 99px;
    background: rgba(255,255,255,0.04); border: 0.5px solid rgba(255,255,255,0.1);
}

/* Decorative sample preview in the hero */
.cs-mock {
    flex-shrink: 0; width: 330px; border-radius: 16px; padding: 18px 20px;
    background: rgba(26,29,39,0.85); border: 0.5px solid rgba(255,255,255,0.1);
    box-shadow: 0 18px 50px rgba(0,0,0,0.45), 0 0 40px rgba(20,184,166,0.10);
    animation: cs-float 6s ease-in-out infinite;
}
@keyframes cs-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
.cs-mock-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.cs-ring {
    position: relative; width: 84px; height: 84px; border-radius: 50%; flex-shrink: 0;
    background: conic-gradient(#14B8A6 0 94%, rgba(255,255,255,0.08) 94% 100%);
    display: flex; align-items: center; justify-content: center;
}
.cs-ring::before { content: ''; position: absolute; inset: 8px; border-radius: 50%; background: #1A1D27; }
.cs-ring span { position: relative; font-size: 18px; font-weight: 700; color: #F0F0F0 !important; }
.cs-bars { display: flex; align-items: flex-end; gap: 6px; height: 54px; margin-top: 16px; }
.cs-bars i { flex: 1; border-radius: 4px 4px 0 0; background: linear-gradient(180deg, #14B8A6, rgba(20,184,166,0.25)); }
@media (max-width: 1000px) { .cs-mock { display: none; } .cs-hero { padding: 32px 26px; } }

/* Feature cards */
.cs-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 12px;
}
.cs-card {
    background: #1A1D27;
    border: 0.5px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 16px 18px;
    box-sizing: border-box;
    overflow: hidden;
    transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.cs-card:hover {
    transform: translateY(-3px);
    border-color: rgba(20,184,166,0.4);
    box-shadow: 0 12px 30px rgba(20,184,166,0.12);
}
</style>
""", unsafe_allow_html=True)


# ── Layout constants (px) ──
# RIGHT_H      : height of the "How CleanSight works" card
# LEFT_TOP_H   : height used on the left above the card grid (title + uploader + caption + gaps).
#                If the grid's bottom edge sits a few px above/below the right card, change this
#                number by that amount (smaller = taller grid).
RIGHT_H = 560
LEFT_TOP_H = 232
GRID_H = RIGHT_H - LEFT_TOP_H


def render(html):
    """Render raw HTML; flattens newlines/indentation so Markdown never treats it as a code block."""
    st.markdown(re.sub(r"\n\s*", " ", html.strip()), unsafe_allow_html=True)


# ── Sidebar ──
with st.sidebar:
    st.image("assets/logo.svg")
    st.caption("Automated data profiling & cleaning")
    st.divider()
    if "df" in st.session_state:
        st.success(f"📄 {st.session_state.filename}")
        st.caption(
            f"{st.session_state.df.shape[0]:,} rows · "
            f"{st.session_state.df.shape[1]} columns"
        )
        st.divider()
    st.caption("Navigate using the pages above")

# ── Hero ──
bars = "".join(f"<i style='height:{h}%'></i>" for h in (35, 55, 80, 100, 72, 48, 30, 18, 12))
chips = "".join(f"<span class='cs-chip'>{t}</span>" for t in (
    "IQR outlier detection", "Smart imputation", "Inconsistency checks",
    "Interactive charts", "AI assistant", "PDF reports"))

render(f"""
<div class='cs-hero'>
  <div class='cs-hero-inner'>
    <div style='min-width:0'>
      <div class='cs-badge'><span class='cs-dot'></span>Smart Data Profiling &amp; Cleaning</div>
      <div style='font-size:52px;font-weight:800;line-height:1.08;letter-spacing:-1.6px;margin-bottom:18px'>
        <span style='color:#F0F0F0'>Your Personal Data Analyst,</span><br>
        <span class='cs-grad'>CleanSight</span>
      </div>
      <div style='font-size:17px;color:#9CA1B5;line-height:1.7;max-width:560px'>
        Upload a dataset and CleanSight profiles it, finds and fixes quality issues,
        visualizes it and answers your questions &mdash; no code required.
      </div>
      <div class='cs-chips'>{chips}</div>
    </div>
    <div class='cs-mock'>
      <div class='cs-mock-head'>
        <span style='font-size:13px;font-weight:600;color:#F0F0F0'>Data quality</span>
        <span style='font-size:10px;color:#8B8FA8;border:0.5px solid rgba(255,255,255,0.15);
             border-radius:99px;padding:2px 9px'>sample preview</span>
      </div>
      <div style='display:flex;align-items:center;gap:18px'>
        <div class='cs-ring'><span>94%</span></div>
        <div style='display:flex;flex-direction:column;gap:7px;font-size:12px;color:#B8BCCC'>
          <div><b style='color:#5DCAA5'>510 &rarr; 0</b> missing values</div>
          <div><b style='color:#EF9F27'>514</b> outliers clipped</div>
          <div><b style='color:#5EEAD4'>0</b> duplicate rows</div>
        </div>
      </div>
      <div class='cs-bars'>{bars}</div>
    </div>
  </div>
</div>
""")

# ── Upload (left) + Workflow (right) ──
left, right = st.columns([1.5, 1], gap="large")

with left:
    render("""
    <div style='height:22px;line-height:22px;font-size:16px;font-weight:600;color:#F0F0F0'>
      <span style='color:#14B8A6'>●</span>&nbsp; Upload your dataset
    </div>
    """)

    uploaded = st.file_uploader(
        "dataset",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed"
    )

    if uploaded:
        try:
            with st.spinner("Loading dataset..."):
                if uploaded.name.endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded)

            # Only reset state when it is a genuinely new file, not on every rerun
            file_signature = (uploaded.name, uploaded.size)
            if st.session_state.get("file_signature") != file_signature:
                st.session_state.df = df
                st.session_state.original_df = df.copy()
                st.session_state.filename = uploaded.name
                st.session_state.file_signature = file_signature
                st.session_state.chat_history = []
                st.session_state.cleaning_log = []
                st.session_state.inconsistency_findings = []
                st.session_state.inconsistency_fixed = []
                st.session_state.ai_summary = None
                st.session_state.custom_charts = []
                st.session_state.last_chart_spec = None
                st.session_state.pdf_report = None
                st.session_state.profiler_insights = None

            current = st.session_state.df
            num_cols = len(current.select_dtypes(include="number").columns)
            missing = int(current.isnull().sum().sum())

            render(f"""
            <div style='background:rgba(29,158,117,0.08);border:0.5px solid rgba(29,158,117,0.28);
                 border-radius:10px;padding:13px 16px;font-size:14px;color:#5DCAA5;margin:12px 0'>
              ✓ &nbsp;<b>{uploaded.name}</b>&nbsp; loaded successfully
            </div>
            """)

            warn_c = "#EF9F27" if missing > 0 else "#5DCAA5"
            warn_bg = "rgba(239,159,39,0.08)" if missing > 0 else "rgba(29,158,117,0.08)"
            warn_bd = "rgba(239,159,39,0.28)" if missing > 0 else "rgba(29,158,117,0.28)"
            warn_icon = "⚠️" if missing > 0 else "✅"

            render(f"""
            <div style='display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 24px 0'>
              <div style='background:rgba(20,184,166,0.07);border:0.5px solid rgba(20,184,166,0.2);
                   border-radius:8px;padding:9px 16px;font-size:13px;color:#8B8FA8'>
                📊&nbsp;<b style='color:#F0F0F0;font-size:15px'>{current.shape[0]:,}</b>&nbsp;rows
              </div>
              <div style='background:rgba(255,255,255,0.03);border:0.5px solid rgba(255,255,255,0.1);
                   border-radius:8px;padding:9px 16px;font-size:13px;color:#8B8FA8'>
                ▦&nbsp;<b style='color:#F0F0F0;font-size:15px'>{current.shape[1]}</b>&nbsp;columns
              </div>
              <div style='background:rgba(20,184,166,0.07);border:0.5px solid rgba(20,184,166,0.2);
                   border-radius:8px;padding:9px 16px;font-size:13px;color:#8B8FA8'>
                🔢&nbsp;<b style='color:#F0F0F0;font-size:15px'>{num_cols}</b>&nbsp;numeric
              </div>
              <div style='background:{warn_bg};border:0.5px solid {warn_bd};
                   border-radius:8px;padding:9px 16px;font-size:13px;color:{warn_c}'>
                {warn_icon}&nbsp;<b style='color:{warn_c};font-size:15px'>{missing:,}</b>&nbsp;missing
              </div>
            </div>
            <div style='font-size:14px;font-weight:500;color:#8B8FA8;margin-bottom:10px'>
              Where would you like to start?
            </div>
            """)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("📊  Profile", use_container_width=True, key="nav_profile"):
                    st.switch_page("pages/1_Profiler.py")
            with c2:
                if st.button("🧹  Clean", use_container_width=True, key="nav_clean"):
                    st.switch_page("pages/3_Clean.py")
            with c3:
                if st.button("📈  Visualize", use_container_width=True, key="nav_visualize"):
                    st.switch_page("pages/4_Visualize.py")
            c4, c5 = st.columns(2)
            with c4:
                if st.button("🤖  Ask AI", use_container_width=True, key="nav_assistant"):
                    st.switch_page("pages/2_Assistant.py")
            with c5:
                if st.button("📄  Reports", use_container_width=True, key="nav_reports"):
                    st.switch_page("pages/5_Reports.py")

        except Exception as e:
            st.error(f"Could not read file: {e}")
    else:
        render("""
        <div style='height:22px;line-height:22px;font-size:13px;color:#8B8FA8'>
          🔒 &nbsp;The AI only receives summary statistics &mdash; never your full rows
        </div>
        """)

        highlights = [
            ("🛡️", "You stay in control", "#14B8A6",
             "Choose the fix for every issue, preview outliers on a box plot and review the full cleaning log."),
            ("📊", "See your data clearly", "#7F77DD",
             "Inspect any column in the profiler, then build your own charts or use explained auto-insights."),
            ("🤖", "Grounded AI answers", "#1D9E75",
             "Answers come from real computed statistics first, with an LLM fallback for everything else."),
            ("📄", "Export-ready results", "#EF9F27",
             "Download the cleaned CSV and an AI-written PDF report whenever you finish cleaning."),
        ]
        cards = "".join(f"""
        <div class='cs-card' style='border-top:2px solid {color}'>
          <div style='display:flex;align-items:center;gap:10px;margin-bottom:8px'>
            <div style='width:30px;height:30px;border-radius:8px;background:{color}22;
                 display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0'>{icon}</div>
            <div style='font-size:14px;font-weight:600;color:#F0F0F0'>{title}</div>
          </div>
          <div style='font-size:12.5px;color:#8B8FA8;line-height:1.55'>{text}</div>
        </div>
        """ for icon, title, color, text in highlights)
        render(f"<div class='cs-grid' style='height:{GRID_H}px'>{cards}</div>")

with right:
    steps = [
        ("1", "Profile", "Column types, stats, missing values and outlier flags", "#14B8A6"),
        ("2", "Ask", "Chat with an AI assistant that knows your dataset", "#1D9E75"),
        ("3", "Clean", "Fix missing values, outliers, duplicates and inconsistencies", "#EF9F27"),
        ("4", "Visualize", "Build your own charts or get automatic insights", "#7F77DD"),
        ("5", "Report", "AI summary plus PDF and cleaned CSV export", "#5DCAA5"),
    ]
    rows = ""
    for i, (num, title, desc, color) in enumerate(steps):
        border = "border-bottom:0.5px solid rgba(255,255,255,0.05);" if i < len(steps) - 1 else ""
        rows += f"""
        <div style='flex:1;display:flex;align-items:center;gap:14px;{border}'>
          <div style='width:34px;height:34px;border-radius:50%;border:1.5px solid {color};
               background:{color}1F;box-shadow:0 0 14px {color}33;
               color:{color};display:flex;align-items:center;justify-content:center;
               font-size:14px;font-weight:700;flex-shrink:0'>{num}</div>
          <div>
            <div style='font-size:14px;font-weight:600;color:#F0F0F0'>{title}</div>
            <div style='font-size:12px;color:#8B8FA8;margin-top:2px;line-height:1.5'>{desc}</div>
          </div>
        </div>
        """

    render(f"""
    <div style='background:linear-gradient(180deg, rgba(20,184,166,0.07), #1A1D27 38%);
         border:0.5px solid rgba(20,184,166,0.22);border-radius:16px;padding:22px 26px;
         box-sizing:border-box;height:{RIGHT_H}px;display:flex;flex-direction:column'>
      <div style='font-size:16px;font-weight:600;color:#F0F0F0;margin-bottom:6px'>
        How CleanSight works
      </div>
      <div style='flex:1;display:flex;flex-direction:column'>{rows}</div>
    </div>
    """)