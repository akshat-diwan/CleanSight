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

# ── Sidebar ──
with st.sidebar:
    st.markdown("### 🔷 InsightForge AI")
    st.divider()
    if "df" in st.session_state:
        st.success(f"📄 {st.session_state.filename}")
        st.caption(f"{st.session_state.df.shape[0]:,} rows · {st.session_state.df.shape[1]} columns")
    st.divider()
    st.caption("Navigate using the pages above")

# ── Hero ──
st.markdown("""
<h1 style='font-size:32px;font-weight:500;margin-bottom:4px'>
Insight<span style='color:#378ADD'>Forge</span> AI
</h1>
<p style='font-size:15px;opacity:0.5;margin-top:0'>
Autonomous data analysis, cleaning, and ML — powered by AI
</p>
""", unsafe_allow_html=True)

st.divider()

col1, col2 = st.columns([1.6, 1], gap="large")

with col1:
    st.markdown("#### Upload your dataset")
    uploaded = st.file_uploader(
        "Upload",
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

            st.success(f"✓ Loaded **{uploaded.name}** — {df.shape[0]:,} rows × {df.shape[1]} columns")
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Where would you like to start?**")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.page_link("pages/1_Profiler.py", label="📊  Profile dataset", use_container_width=True)
            with c2:
                st.page_link("pages/2_Assistant.py", label="🤖  Ask AI", use_container_width=True)
            with c3:
                st.page_link("pages/3_Clean.py", label="🧹  Clean data", use_container_width=True)

        except Exception as e:
            st.error(f"Could not read file: {e}")

with col2:
    st.markdown("#### What InsightForge does")
    features = [
        ("📊", "Profiler", "Instant dataset overview & stats"),
        ("🤖", "AI assistant", "Ask questions in natural language"),
        ("🧹", "Clean & transform", "AI-detected issues & fixes"),
        ("🧠", "ML studio", "Train & evaluate models"),
        ("📄", "Reports", "Export full analysis as PDF"),
    ]
    for icon, title, desc in features:
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:12px;padding:9px 0;
             border-bottom:0.5px solid rgba(128,128,128,0.1)'>
          <span style='font-size:18px'>{icon}</span>
          <div>
            <div style='font-size:13px;font-weight:500'>{title}</div>
            <div style='font-size:12px;opacity:0.5'>{desc}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)