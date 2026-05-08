import streamlit as st

st.set_page_config(page_title="Reports · InsightForge AI", layout="wide")
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

st.markdown("<h2 style='font-weight:500'>📄 Reports</h2>", unsafe_allow_html=True)
st.caption(f"Export your full analysis · {st.session_state.filename}")
st.divider()

st.markdown("#### What's included")
s1, s2, s3 = st.columns(3, gap="medium")

sections = [
    ("📊", "Dataset profile",
     ["Shape and column types", "Missing value summary", "Numeric statistics", "Data sample"]),
    ("🧹", "Cleaning log",
     ["Issues detected", "Fixes applied", "Before vs after stats", "Rows removed"]),
    ("🧠", "ML results",
     ["Model used", "Accuracy / metrics", "Feature importance", "AI explanation"]),
]

for col, (icon, title, items) in zip([s1, s2, s3], sections):
    with col:
        items_html = "".join(
            f"<div style='padding:3px 0;opacity:0.6;font-size:13px'>· {item}</div>"
            for item in items
        )
        st.markdown(f"""
        <div style='border:0.5px solid rgba(128,128,128,0.15);border-radius:12px;padding:16px'>
          <div style='font-size:20px;margin-bottom:8px'>{icon}</div>
          <div style='font-weight:500;font-size:14px;margin-bottom:8px'>{title}</div>
          {items_html}
        </div>
        """, unsafe_allow_html=True)

st.divider()
st.markdown("#### AI-written summary")
st.markdown("""
<div style='border:0.5px solid rgba(55,138,221,0.3);border-radius:12px;
     padding:18px 20px;font-size:13px;background:rgba(55,138,221,0.06);
     line-height:1.8'>
  <span style='color:#378ADD'>✨</span>
  <span style='opacity:0.6'> The AI will write a plain-English summary of your entire
  analysis here — covering dataset quality, cleaning decisions, model performance,
  and key recommendations. Auto-generated on export.</span>
</div>
""", unsafe_allow_html=True)

st.divider()
st.markdown("#### Export")
e1, e2, e3, e4 = st.columns(4)
with e1:
    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
    st.button("📄 Export as PDF", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
with e2:
    st.button("📊 Export as CSV", use_container_width=True)
with e3:
    st.button("📋 Export as Excel", use_container_width=True)
with e4:
    st.button("📝 Copy AI summary", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
st.caption("Export functionality will be enabled once the backend is connected.")