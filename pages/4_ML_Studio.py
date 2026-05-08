import streamlit as st

st.set_page_config(page_title="ML Studio · InsightForge AI", layout="wide")
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🔷 InsightForge AI")
    st.divider()
    if "df" in st.session_state:
        st.success(f"📄 {st.session_state.filename}")
        st.caption(f"{st.session_state.df.shape[0]:,} rows · {st.session_state.df.shape[1]} columns")
    else:
        st.warning("No dataset loaded")
        st.page_link("app.py", label="← Upload a dataset")

if "df" not in st.session_state:
    st.info("Please upload a dataset on the home page first.")
    st.page_link("app.py", label="← Go to home")
    st.stop()

df = st.session_state.df

st.markdown("<h2 style='font-weight:500'>🧠 ML studio</h2>", unsafe_allow_html=True)
st.caption(f"Train and evaluate models · {st.session_state.filename}")
st.divider()

st.markdown("#### Model configuration")
cfg1, cfg2, cfg3 = st.columns(3)
with cfg1:
    target = st.selectbox("Target column", df.columns.tolist(), index=len(df.columns)-1)
with cfg2:
    task = st.selectbox("Task type", ["Auto-detect", "Classification", "Regression"])
with cfg3:
    model_choice = st.selectbox("Model", [
        "Auto (AI picks best)", "Random Forest",
        "XGBoost", "Logistic Regression", "Linear Regression"
    ])

feat_cols = [c for c in df.columns if c != target]
selected_features = st.multiselect("Feature columns", feat_cols, default=feat_cols)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="primary-btn" style="display:inline-block">', unsafe_allow_html=True)
train_clicked = st.button("🚀 Train model")
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

res_left, res_right = st.columns(2, gap="large")

with res_left:
    st.markdown("#### Model metrics")
    st.markdown("""
    <div style='border:0.5px solid rgba(128,128,128,0.15);border-radius:12px;
         padding:36px;text-align:center;font-size:13px;opacity:0.4'>
      Metrics will appear here after training
    </div>
    """, unsafe_allow_html=True)

with res_right:
    st.markdown("#### Feature importance")
    st.markdown("""
    <div style='border:0.5px solid rgba(128,128,128,0.15);border-radius:12px;
         padding:36px;text-align:center;font-size:13px;opacity:0.4'>
      Chart will appear here after training
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.markdown("#### AI model explanation")
st.markdown("""
<div style='border:0.5px solid rgba(55,138,221,0.3);border-radius:12px;
     padding:14px 16px;font-size:13px;background:rgba(55,138,221,0.06)'>
  <span style='color:#378ADD'>💡</span>
  <span style='opacity:0.6'> After training, AI will explain results in plain English —
  what metrics mean, which features matter, and what to improve.</span>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.page_link("pages/5_Reports.py", label="📄 Generate report →")