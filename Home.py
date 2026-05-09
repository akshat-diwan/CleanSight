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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid] {
    font-family: 'Inter', sans-serif !important;
}

/* Force sidebar open */
[data-testid="stSidebar"] {
    display: block !important;
    visibility: visible !important;
    width: 260px !important;
    background-color: #1A1D27 !important;
    border-right: 0.5px solid rgba(255,255,255,0.07) !important;
}

/* Uploader internals */
[data-testid="stFileUploader"] > div > div:first-child {
    display: none !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: #12151F !important;
    border: 1.5px dashed rgba(55,138,221,0.3) !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploaderDropzone"] * {
    color: #8B8FA8 !important;
    background: transparent !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: rgba(55,138,221,0.15) !important;
    color: #378ADD !important;
    border: 0.5px solid rgba(55,138,221,0.35) !important;
    border-radius: 8px !important;
}

/* Page links */
[data-testid="stPageLink"] a,
[data-testid="stPageLink"] a p {
    background: rgba(55,138,221,0.1) !important;
    border: 1px solid rgba(55,138,221,0.35) !important;
    border-radius: 10px !important;
    color: #60AAEE !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    text-align: center !important;
    text-decoration: none !important;
    padding: 11px 8px !important;
    display: flex !important;
    justify-content: center !important;
}
[data-testid="stPageLink"] a:hover,
[data-testid="stPageLink"] a:hover p {
    background: rgba(55,138,221,0.2) !important;
    color: #90CAFF !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.image("assets/logo.svg")
    st.caption("Data Intelligence Platform")
    st.divider()
    if "df" in st.session_state:
        st.success(f"📄 {st.session_state.filename}")
        st.caption(
            f"{st.session_state.df.shape[0]:,} rows · "
            f"{st.session_state.df.shape[1]} columns"
        )
    st.divider()
    st.caption("Navigate using the pages above")
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
st.markdown("""
<div style='padding:44px 0 36px 0;
     border-bottom:0.5px solid rgba(255,255,255,0.06);
     margin-bottom:36px;font-family:Inter,sans-serif'>

  <div style='display:inline-flex;align-items:center;gap:7px;
       background:rgba(55,138,221,0.08);
       border:0.5px solid rgba(55,138,221,0.25);
       border-radius:99px;padding:5px 15px;
       font-size:12px;font-weight:500;
       color:#378ADD;margin-bottom:22px;letter-spacing:0.05em'>
    ✦ &nbsp;AI-Powered Data Analysis
  </div>

  <div style='font-size:50px;font-weight:800;line-height:1.1;
       letter-spacing:-1.5px;margin-bottom:18px'>
    <span style='color:#F0F0F0'>Your Personal Data Scientist, </span><br>
    <span style='color:#F0F0F0'>Insight</span><span style='color:#378ADD'>Forge</span><span style='color:#F0F0F0'> AI </span>
  </div>

  <div style='font-size:17px;color:#8B8FA8;line-height:1.7;
       font-weight:400;max-width:540px'>
    InsightForge AI Profiles, Cleans, Models and Explains
    your Dataset, No Code Required.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Two columns ──
left, right = st.columns([1.5, 1], gap="large")

with left:
    # Title outside card to avoid awkward nested card
    st.markdown(
        "<p style='font-size:16px;font-weight:600;color:#F0F0F0;"
        "margin-bottom:12px;font-family:Inter,sans-serif'>"
        "Upload your dataset</p>",
        unsafe_allow_html=True
    )

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

            st.session_state.df = df
            st.session_state.filename = uploaded.name
            st.session_state.chat_history = []
            st.session_state.cleaning_log = []

            num_cols = len(df.select_dtypes(include='number').columns)
            missing = int(df.isnull().sum().sum())

            # Success
            st.markdown(f"""
            <div style='background:rgba(29,158,117,0.08);
                 border:0.5px solid rgba(29,158,117,0.28);
                 border-radius:10px;padding:13px 16px;
                 font-size:14px;color:#5DCAA5;
                 margin:12px 0;font-family:Inter,sans-serif'>
              ✓ &nbsp;<b>{uploaded.name}</b>&nbsp; loaded successfully
            </div>
            """, unsafe_allow_html=True)

            # Stats
            warn_c = "#EF9F27" if missing > 0 else "#5DCAA5"
            warn_bg = "rgba(239,159,39,0.08)" if missing > 0 else "rgba(29,158,117,0.08)"
            warn_bd = "rgba(239,159,39,0.28)" if missing > 0 else "rgba(29,158,117,0.28)"
            warn_icon = "⚠️" if missing > 0 else "✅"

            st.markdown(f"""
            <div style='display:flex;flex-wrap:wrap;gap:8px;
                 margin:4px 0 22px 0;font-family:Inter,sans-serif'>
              <div style='background:rgba(55,138,221,0.07);
                   border:0.5px solid rgba(55,138,221,0.2);border-radius:8px;
                   padding:9px 16px;font-size:13px;color:#8B8FA8;
                   display:inline-flex;align-items:center;gap:8px'>
                📊&nbsp;<b style='color:#F0F0F0;font-size:15px'>{df.shape[0]:,}</b>&nbsp;rows
              </div>
              <div style='background:rgba(255,255,255,0.03);
                   border:0.5px solid rgba(255,255,255,0.1);border-radius:8px;
                   padding:9px 16px;font-size:13px;color:#8B8FA8;
                   display:inline-flex;align-items:center;gap:8px'>
                ▦&nbsp;<b style='color:#F0F0F0;font-size:15px'>{df.shape[1]}</b>&nbsp;columns
              </div>
              <div style='background:rgba(55,138,221,0.07);
                   border:0.5px solid rgba(55,138,221,0.2);border-radius:8px;
                   padding:9px 16px;font-size:13px;color:#8B8FA8;
                   display:inline-flex;align-items:center;gap:8px'>
                🔢&nbsp;<b style='color:#F0F0F0;font-size:15px'>{num_cols}</b>&nbsp;numeric
              </div>
              <div style='background:{warn_bg};
                   border:0.5px solid {warn_bd};border-radius:8px;
                   padding:9px 16px;font-size:13px;color:{warn_c};
                   display:inline-flex;align-items:center;gap:8px'>
                {warn_icon}&nbsp;<b style='color:{warn_c};font-size:15px'>{missing:,}</b>&nbsp;missing
              </div>
            </div>

            <div style='font-size:14px;font-weight:500;color:#8B8FA8;
                 margin-bottom:10px;font-family:Inter,sans-serif'>
              Where would you like to start?
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("📊  Profile dataset", use_container_width=True, key="nav_profile"):
                    st.switch_page("pages/1_Profiler.py")
            with c2:
                if st.button("🤖  Ask AI", use_container_width=True, key="nav_assistant"):
                    st.switch_page("pages/2_Assistant.py")
            with c3:
                if st.button("🧹  Clean data", use_container_width=True, key="nav_clean"):
                    st.switch_page("pages/3_Clean.py")

        except Exception as e:
            st.error(f"Could not read file: {e}")
    else:
        st.markdown(
            "<p style='font-size:13px;color:#8B8FA8;"
            "margin-top:8px;font-family:Inter,sans-serif'>"
            "Supports CSV and Excel &nbsp;·&nbsp; Max 200MB per file</p>",
            unsafe_allow_html=True
        )

with right:
    st.markdown("""
    <div style='background:#1A1D27;border:0.5px solid rgba(255,255,255,0.07);
         border-radius:16px;padding:26px;font-family:Inter,sans-serif'>

      <div style='font-size:16px;font-weight:600;color:#F0F0F0;margin-bottom:20px'>
        What InsightForge does
      </div>

      <div style='display:flex;align-items:center;gap:14px;padding:11px 0;border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <div style='width:40px;height:40px;border-radius:10px;background:rgba(55,138,221,0.15);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0'>📊</div>
        <div><div style='font-size:14px;font-weight:600;color:#F0F0F0'>Data profiler</div>
        <div style='font-size:12px;color:#8B8FA8;margin-top:2px'>Column types, stats & data quality overview</div></div>
      </div>

      <div style='display:flex;align-items:center;gap:14px;padding:11px 0;border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <div style='width:40px;height:40px;border-radius:10px;background:rgba(29,158,117,0.15);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0'>🤖</div>
        <div><div style='font-size:14px;font-weight:600;color:#F0F0F0'>AI assistant</div>
        <div style='font-size:12px;color:#8B8FA8;margin-top:2px'>Ask questions about your data naturally</div></div>
      </div>

      <div style='display:flex;align-items:center;gap:14px;padding:11px 0;border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <div style='width:40px;height:40px;border-radius:10px;background:rgba(239,159,39,0.15);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0'>🧹</div>
        <div><div style='font-size:14px;font-weight:600;color:#F0F0F0'>Clean & transform</div>
        <div style='font-size:12px;color:#8B8FA8;margin-top:2px'>AI-detected issues with one-click fixes</div></div>
      </div>

      <div style='display:flex;align-items:center;gap:14px;padding:11px 0;border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <div style='width:40px;height:40px;border-radius:10px;background:rgba(212,83,126,0.15);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0'>🧠</div>
        <div><div style='font-size:14px;font-weight:600;color:#F0F0F0'>ML studio</div>
        <div style='font-size:12px;color:#8B8FA8;margin-top:2px'>Train & evaluate models automatically</div></div>
      </div>

      <div style='display:flex;align-items:center;gap:14px;padding:11px 0'>
        <div style='width:40px;height:40px;border-radius:10px;background:rgba(93,202,165,0.15);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0'>📄</div>
        <div><div style='font-size:14px;font-weight:600;color:#F0F0F0'>Reports</div>
        <div style='font-size:12px;color:#8B8FA8;margin-top:2px'>Export full analysis as PDF</div></div>
      </div>

    </div>
    """, unsafe_allow_html=True)