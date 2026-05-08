import streamlit as st
import pandas as pd

st.set_page_config(page_title="Clean · InsightForge AI", layout="wide")
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
if "cleaning_log" not in st.session_state:
    st.session_state.cleaning_log = []

st.markdown("<h2 style='font-weight:500'>🧹 Clean & transform</h2>", unsafe_allow_html=True)
st.caption(f"AI-detected issues and fixes · {st.session_state.filename}")
st.divider()

# ── AI command bar ──
st.markdown("#### AI cleaning command")
ai_c1, ai_c2 = st.columns([3, 1])
with ai_c1:
    st.text_input("cmd", placeholder='"Clean everything" or "Only fix missing values"',
                  label_visibility="collapsed", key="clean_cmd")
with ai_c2:
    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
    st.button("🤖 Run AI clean", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

left, right = st.columns([1.4, 1], gap="large")

with left:
    st.markdown("#### Issues detected")

    # Build issues list with unique index to avoid duplicate keys
    issues = []
    for col in df.columns:
        missing = int(df[col].isnull().sum())
        dtype = str(df[col].dtype)
        if missing > 0:
            issues.append({
                "col": col,
                "issue": f"{missing} missing values",
                "sev": "warning",
                "fix": "Fill with median / mode / 0",
                "type": "missing"
            })
        if "int" in dtype or "float" in dtype:
            Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = int(((df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)).sum())
            if outliers > 0:
                issues.append({
                    "col": col,
                    "issue": f"{outliers} outliers",
                    "sev": "error",
                    "fix": "Replace with median (IQR method)",
                    "type": "outlier"
                })

    dupes = int(df.duplicated().sum())
    issues.append({
        "col": "Duplicate rows",
        "issue": f"{dupes} duplicates",
        "sev": "ok" if dupes == 0 else "warning",
        "fix": "Drop duplicate rows" if dupes > 0 else "No action needed",
        "type": "dupes"
    })

    SEV = {
        "warning": ("rgba(239,159,39,0.12)",  "#EF9F27"),
        "error":   ("rgba(226,75,74,0.12)",   "#E24B4A"),
        "ok":      ("rgba(29,158,117,0.12)",  "#1D9E75"),
    }

    if not issues:
        st.success("No issues detected — dataset looks clean!")
    else:
        for idx, issue in enumerate(issues):
            bg, fg = SEV[issue["sev"]]
            c1, c2, c3 = st.columns([1.2, 1.6, 0.7])
            with c1:
                st.markdown(f"**{issue['col']}**")
                st.markdown(
                    f"<span style='background:{bg};color:{fg};padding:2px 9px;"
                    f"border-radius:99px;font-size:11px'>{issue['issue']}</span>",
                    unsafe_allow_html=True)
            with c2:
                st.caption(f"💡 {issue['fix']}")
            with c3:
                if issue["sev"] != "ok":
                    # ← unique key uses both index AND type to guarantee uniqueness
                    st.button("Apply", key=f"fix_{idx}_{issue['type']}_{issue['col']}",
                              use_container_width=True)
            st.markdown(
                "<div style='border-top:0.5px solid rgba(128,128,128,0.08);margin:4px 0'></div>",
                unsafe_allow_html=True)

with right:
    st.markdown("#### After cleaning")
    total_missing = int(df.isnull().sum().sum())
    total_dupes = int(df.duplicated().sum())
    miss_color = "rgba(29,158,117,0.8)" if total_missing == 0 else "rgba(239,159,39,0.8)"
    dupe_color = "rgba(29,158,117,0.8)" if total_dupes == 0 else "rgba(239,159,39,0.8)"

    st.markdown(f"""
    <div style='border:0.5px solid rgba(128,128,128,0.15);border-radius:12px;padding:14px 16px;font-size:13px'>
      <div style='display:flex;justify-content:space-between;padding:6px 0;
           border-bottom:0.5px solid rgba(128,128,128,0.08)'>
        <span style='opacity:0.55'>Rows remaining</span><b>{df.shape[0]:,}</b>
      </div>
      <div style='display:flex;justify-content:space-between;padding:6px 0;
           border-bottom:0.5px solid rgba(128,128,128,0.08)'>
        <span style='opacity:0.55'>Missing values</span>
        <b style='color:{miss_color}'>{total_missing}</b>
      </div>
      <div style='display:flex;justify-content:space-between;padding:6px 0'>
        <span style='opacity:0.55'>Duplicates</span>
        <b style='color:{dupe_color}'>{total_dupes}</b>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Cleaning log")
    if not st.session_state.cleaning_log:
        st.markdown("""
        <div style='border:0.5px solid rgba(128,128,128,0.12);border-radius:10px;
             padding:20px;text-align:center;font-size:13px;opacity:0.4'>
          No actions taken yet
        </div>
        """, unsafe_allow_html=True)
    else:
        for entry in st.session_state.cleaning_log:
            st.markdown(f"✅ {entry}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.page_link("pages/4_ML_Studio.py", label="🧠 Ready? Go to ML studio →",
                 use_container_width=True)