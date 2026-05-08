import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="InsightForge AI",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)

with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
/* ── Nuke the blank card completely ── */
[data-testid="stFileUploader"] > div:first-child,
[data-testid="stFileUploader"] > div > div:first-child {
    display: none !important;
    height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ── Uploader dropzone ── */
section[data-testid="stFileUploaderDropzone"] {
    background: #12151F !important;
    border: 1.5px dashed rgba(55,138,221,0.35) !important;
    border-radius: 12px !important;
}
section[data-testid="stFileUploaderDropzone"] * {
    color: #8B8FA8 !important;
    background: transparent !important;
}
section[data-testid="stFileUploaderDropzone"] button {
    background: rgba(55,138,221,0.15) !important;
    color: #378ADD !important;
    border: 0.5px solid rgba(55,138,221,0.35) !important;
    border-radius: 8px !important;
}

/* ── Page link buttons ── */
[data-testid="stPageLink"] a {
    background: #1E2235 !important;
    border: 1px solid rgba(55,138,221,0.4) !important;
    border-radius: 10px !important;
    color: #378ADD !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 12px 16px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-decoration: none !important;
    transition: all 0.15s !important;
}
[data-testid="stPageLink"] a:hover {
    background: rgba(55,138,221,0.2) !important;
    color: #60AAEE !important;
}

/* ── Cards ── */
.upload-card {
    background: #1A1D27;
    border: 0.5px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 28px;
}
.feature-card {
    background: #1A1D27;
    border: 0.5px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 28px;
}
.card-title {
    font-size: 17px;
    font-weight: 600;
    color: #F0F0F0;
    margin: 0 0 18px 0;
}
.feature-row {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 0;
    border-bottom: 0.5px solid rgba(255,255,255,0.05);
}
.feature-row:last-child { border-bottom: none; }
.ficon {
    width: 40px; height: 40px;
    border-radius: 10px;
    display: flex; align-items: center;
    justify-content: center;
    font-size: 19px; flex-shrink: 0;
}
.fi-blue  { background: rgba(55,138,221,0.15); }
.fi-green { background: rgba(29,158,117,0.15); }
.fi-amber { background: rgba(239,159,39,0.15); }
.fi-pink  { background: rgba(212,83,126,0.15); }
.fi-teal  { background: rgba(93,202,165,0.15); }
.ftitle { font-size: 14px; font-weight: 600; color: #F0F0F0; }
.fsub   { font-size: 13px; color: #8B8FA8; margin-top: 2px; }

/* ── Stat pills ── */
.stat-row {
    display: flex; flex-wrap: wrap;
    gap: 8px; margin: 14px 0 20px 0;
}
.stat-pill {
    background: rgba(255,255,255,0.04);
    border: 0.5px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px; color: #8B8FA8;
    display: inline-flex; align-items: center; gap: 7px;
}
.stat-pill b { color: #F0F0F0; font-size: 14px; }
.stat-warn {
    background: rgba(239,159,39,0.08);
    border: 0.5px solid rgba(239,159,39,0.35);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px; color: #EF9F27;
    display: inline-flex; align-items: center; gap: 7px;
}
.stat-warn b { color: #EF9F27; font-size: 14px; }

.success-banner {
    background: rgba(29,158,117,0.08);
    border: 0.5px solid rgba(29,158,117,0.3);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 14px; color: #5DCAA5;
    margin: 14px 0 4px 0;
}
.start-label {
    font-size: 14px; font-weight: 500;
    color: #8B8FA8; margin: 4px 0 10px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    # Three-part branding: white · blue · white
    st.markdown("""
    <div style='padding:6px 0 14px 0'>
      <div style='font-size:17px;font-weight:700;line-height:1.4'>
        🔷&nbsp;<span style='color:#F0F0F0 !important'>Insight</span><span style='color:#378ADD !important'>Forge</span><span style='color:#F0F0F0 !important'>&nbsp;AI</span>
      </div>
      <div style='font-size:12px;color:#8B8FA8;margin-top:3px'>
        Data intelligence platform
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    if "df" in st.session_state:
        st.success(f"📄 {st.session_state.filename}")
        st.caption(f"{st.session_state.df.shape[0]:,} rows · {st.session_state.df.shape[1]} columns")
    st.divider()
    st.caption("Navigate using the pages above")

# ── Hero ──
st.markdown("""
<div style='padding:36px 0 32px 0;border-bottom:0.5px solid rgba(255,255,255,0.06);margin-bottom:32px'>
  <div style='display:inline-flex;align-items:center;gap:6px;
       background:rgba(55,138,221,0.1);border:0.5px solid rgba(55,138,221,0.3);
       border-radius:99px;padding:5px 14px;font-size:12px;color:#378ADD;
       margin-bottom:18px;letter-spacing:0.03em'>
    ✦ &nbsp;Powered by Llama 3.3 70B
  </div>
  <div style='font-size:46px;font-weight:700;line-height:1.15;
       letter-spacing:-0.5px;margin-bottom:14px'>
    <span style='color:#F0F0F0'>Your data, understood<br>by&nbsp;</span><span style='color:#378ADD'>InsightForge AI</span>
  </div>
  <div style='font-size:17px;color:#8B8FA8;line-height:1.6'>
    Upload any dataset and let AI profile, clean,<br>model, and explain it — in seconds.
  </div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1.5, 1], gap="large")

with left:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Upload your dataset</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "dataset",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed"
    )

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            st.session_state.df = df
            st.session_state.filename = uploaded.name
            st.session_state.chat_history = []
            st.session_state.cleaning_log = []

            num_cols = len(df.select_dtypes(include='number').columns)
            missing = int(df.isnull().sum().sum())

            warn_pill = f'<div class="stat-warn">⚠️ &nbsp;<b>{missing:,}</b>&nbsp; missing</div>' \
                        if missing > 0 else \
                        f'<div class="stat-pill">✅ &nbsp;<b>0</b>&nbsp; missing</div>'

            st.markdown(f"""
            <div class="success-banner">
              ✓ &nbsp;<b>{uploaded.name}</b>&nbsp; loaded successfully
            </div>
            <div class="stat-row">
              <div class="stat-pill">📊 &nbsp;<b>{df.shape[0]:,}</b>&nbsp; rows</div>
              <div class="stat-pill">⬛ &nbsp;<b>{df.shape[1]}</b>&nbsp; columns</div>
              <div class="stat-pill">🔵 &nbsp;<b>{num_cols}</b>&nbsp; numeric</div>
              {warn_pill}
            </div>
            <div class="start-label">Where would you like to start?</div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.page_link("pages/1_Profiler.py",
                             label="📊  Profile dataset",
                             use_container_width=True)
            with c2:
                st.page_link("pages/2_Assistant.py",
                             label="🤖  Ask AI",
                             use_container_width=True)
            with c3:
                st.page_link("pages/3_Clean.py",
                             label="🧹  Clean data",
                             use_container_width=True)

        except Exception as e:
            st.error(f"Could not read file: {e}")
    else:
        st.markdown("""
        <p style='font-size:13px;color:#8B8FA8;margin-top:6px'>
          Supports CSV and Excel &nbsp;·&nbsp; Max 200MB per file
        </p>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown("""
    <div class="feature-card">
      <div class="card-title">What InsightForge does</div>
      <div class="feature-row">
        <div class="ficon fi-blue">📊</div>
        <div><div class="ftitle">Data profiler</div>
        <div class="fsub">Instant overview, column types &amp; stats</div></div>
      </div>
      <div class="feature-row">
        <div class="ficon fi-green">🤖</div>
        <div><div class="ftitle">AI assistant</div>
        <div class="fsub">Ask anything in natural language</div></div>
      </div>
      <div class="feature-row">
        <div class="ficon fi-amber">🧹</div>
        <div><div class="ftitle">Clean &amp; transform</div>
        <div class="fsub">AI-detected issues with one-click fixes</div></div>
      </div>
      <div class="feature-row">
        <div class="ficon fi-pink">🧠</div>
        <div><div class="ftitle">ML studio</div>
        <div class="fsub">Train &amp; evaluate models automatically</div></div>
      </div>
      <div class="feature-row">
        <div class="ficon fi-teal">📄</div>
        <div><div class="ftitle">Reports</div>
        <div class="fsub">Export full analysis as PDF</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)