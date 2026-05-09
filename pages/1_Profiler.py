import streamlit as st
import pandas as pd

st.set_page_config(page_title="Profiler · InsightForge AI", layout="wide")
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }

/* Metric cards — lighter, colored accents */
[data-testid="stMetric"] {
    background: #1A1D27 !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 16px 18px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    font-weight: 500 !important;
    color: #8B8FA8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stMetricValue"] {
    font-size: 26px !important;
    font-weight: 700 !important;
    color: #F0F0F0 !important;
    letter-spacing: -0.3px !important;
}
[data-testid="stMetricDelta"] {
    font-size: 12px !important;
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
        st.caption(f"{st.session_state.df.shape[0]:,} rows · {st.session_state.df.shape[1]} columns")
    else:
        st.warning("No dataset loaded")
        if st.button("← Upload a dataset", key="sidebar_upload"):
            st.switch_page("Home.py")
    st.divider()
    st.caption("Navigate using the pages above")

if "df" not in st.session_state:
    st.info("Please upload a dataset on the home page first.")
    if st.button("← Go to home"):
        st.switch_page("Home.py")
    st.stop()

df = st.session_state.df

# ── Header ──
st.markdown(f"""
<div style='padding:28px 0 20px 0;
     border-bottom:0.5px solid rgba(255,255,255,0.06);
     margin-bottom:24px;font-family:Inter,sans-serif'>
  <div style='font-size:12px;font-weight:600;color:#378ADD;
       letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px'>
    Data Profiler
  </div>
  <div style='display:flex;align-items:center;
       justify-content:space-between'>
    <div>
      <div style='font-size:32px;font-weight:700;color:#F0F0F0;
           letter-spacing:-0.5px;line-height:1.2;margin-bottom:6px'>
        Dataset Overview
      </div>
      <div style='font-size:13px;color:#8B8FA8'>
        📄 {st.session_state.filename}
      </div>
    </div>
    <div style='background:rgba(29,158,117,0.1);
         border:0.5px solid rgba(29,158,117,0.25);
         border-radius:99px;padding:5px 14px;
         font-size:12px;font-weight:500;color:#5DCAA5'>
      ✓ &nbsp;Loaded
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Metrics row 1 — colored accent borders ──
total_missing = int(df.isnull().sum().sum())
total_dupes = int(df.duplicated().sum())
num_cols_count = len(df.select_dtypes(include='number').columns)
cat_cols_count = len(df.select_dtypes(include='object').columns)
mem_usage = f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB"
completeness = f"{((1 - df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100):.1f}%"

# Custom colored metric cards via HTML
def metric_card(label, value, accent, icon, sub=None):
    sub_html = f"<div style='font-size:12px;color:{accent};margin-top:4px;opacity:0.8'>{sub}</div>" if sub else ""
    return f"""
    <div style='background:#1A1D27;border:0.5px solid rgba(255,255,255,0.07);
         border-top:2px solid {accent};
         border-radius:12px;padding:16px 18px;height:100%'>
      <div style='font-size:11px;font-weight:600;color:#8B8FA8;
           text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px'>
        {icon} &nbsp;{label}
      </div>
      <div style='font-size:26px;font-weight:700;color:#F0F0F0;
           letter-spacing:-0.3px'>{value}</div>
      {sub_html}
    </div>"""

r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)

with r1c1:
    st.markdown(metric_card("Rows", f"{df.shape[0]:,}", "#378ADD", "📊"), unsafe_allow_html=True)
with r1c2:
    st.markdown(metric_card("Columns", f"{df.shape[1]}", "#7F77DD", "⬛"), unsafe_allow_html=True)
with r1c3:
    miss_accent = "#EF9F27" if total_missing > 0 else "#1D9E75"
    st.markdown(metric_card("Missing", f"{total_missing:,}", miss_accent, "⚠️"), unsafe_allow_html=True)
with r1c4:
    dupe_accent = "#E24B4A" if total_dupes > 0 else "#1D9E75"
    st.markdown(metric_card("Duplicates", f"{total_dupes:,}", dupe_accent, "🔁"), unsafe_allow_html=True)
with r1c5:
    st.markdown(metric_card("Numeric cols", f"{num_cols_count}", "#378ADD", "🔢"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
with r2c1:
    st.markdown(metric_card("Categorical", f"{cat_cols_count}", "#7F77DD", "🏷️"), unsafe_allow_html=True)
with r2c2:
    st.markdown(metric_card("Memory usage", mem_usage, "#EF9F27", "💾"), unsafe_allow_html=True)
with r2c3:
    comp_accent = "#1D9E75" if float(completeness[:-1]) > 95 else "#EF9F27"
    st.markdown(metric_card("Completeness", completeness, comp_accent, "✅"), unsafe_allow_html=True)
with r2c4:
    st.markdown(metric_card("Total cells", f"{df.shape[0] * df.shape[1]:,}", "#378ADD", "🔲"), unsafe_allow_html=True)

st.markdown("""
<div style='border-top:0.5px solid rgba(255,255,255,0.06);margin:24px 0'></div>
""", unsafe_allow_html=True)

# ── Column overview + AI insights ──
left, right = st.columns([1.3, 1], gap="large")

with left:
    st.markdown("""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;
         letter-spacing:-0.3px;margin-bottom:14px'>
      Column overview
    </div>
    """, unsafe_allow_html=True)

    TYPE_COLORS = {
        "numeric":  ("rgba(55,138,221,0.12)",  "#378ADD"),
        "category": ("rgba(127,119,221,0.12)", "#7F77DD"),
        "string":   ("rgba(136,135,128,0.12)", "#888780"),
        "boolean":  ("rgba(239,159,39,0.12)",  "#EF9F27"),
        "datetime": ("rgba(29,158,117,0.12)",  "#1D9E75"),
    }

    h1, h2, h3, h4 = st.columns([2, 1.2, 0.8, 0.8])
    for col_obj, label in zip([h1, h2, h3, h4],
                               ["Column", "Type", "Missing", "Unique"]):
        col_obj.markdown(
            f"<span style='font-size:11px;font-weight:600;color:#8B8FA8;"
            f"text-transform:uppercase;letter-spacing:0.07em'>{label}</span>",
            unsafe_allow_html=True)

    st.markdown(
        "<div style='border-top:0.5px solid rgba(255,255,255,0.08);"
        "margin:6px 0 4px 0'></div>", unsafe_allow_html=True)

    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = int(df[col].isnull().sum())
        unique = int(df[col].nunique())
        miss_pct = round(missing / len(df) * 100, 1)

        if "bool" in dtype:
            col_type = "boolean"
        elif "datetime" in dtype:
            col_type = "datetime"
        elif "int" in dtype or "float" in dtype:
            col_type = "numeric"
        elif df[col].nunique() < 20:
            col_type = "category"
        else:
            col_type = "string"

        bg, fg = TYPE_COLORS.get(col_type, ("rgba(128,128,128,0.1)", "gray"))
        miss_color = "#EF9F27" if missing > 0 else "#5DCAA5"

        r1, r2, r3, r4 = st.columns([2, 1.2, 0.8, 0.8])
        with r1:
            st.markdown(
                f"<span style='font-size:13px;font-weight:500;"
                f"color:#F0F0F0'>{col}</span>",
                unsafe_allow_html=True)
        with r2:
            st.markdown(
                f"<span style='background:{bg};color:{fg};"
                f"padding:3px 10px;border-radius:99px;"
                f"font-size:11px;font-weight:500'>{col_type}</span>",
                unsafe_allow_html=True)
        with r3:
            st.markdown(
                f"<span style='font-size:13px;color:{miss_color};"
                f"font-weight:500'>{missing}</span>"
                f"<span style='font-size:11px;color:#8B8FA8'> {miss_pct}%</span>",
                unsafe_allow_html=True)
        with r4:
            st.markdown(
                f"<span style='font-size:13px;color:#8B8FA8'>{unique:,}</span>",
                unsafe_allow_html=True)

        st.markdown(
            "<div style='border-top:0.5px solid rgba(255,255,255,0.05);"
            "margin:4px 0'></div>", unsafe_allow_html=True)

with right:
    st.markdown("""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;
         letter-spacing:-0.3px;margin-bottom:14px'>
      AI Quick Insights
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='background:rgba(55,138,221,0.06);
         border:0.5px solid rgba(55,138,221,0.18);
         border-radius:12px;padding:16px 18px;line-height:1.9'>
      <div style='font-size:13px;font-weight:600;color:#378ADD;margin-bottom:8px'>
        ✨ AI insights
      </div>
      <div style='font-size:13px;color:#8B8FA8'>
        Will appear here once backend is connected.<br><br>
        · Missing value explanations<br>
        · Correlation highlights<br>
        · Class imbalance warnings<br>
        · Suggested next steps
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;
         letter-spacing:-0.3px;margin-bottom:14px'>
      Numeric Summary
    </div>
    """, unsafe_allow_html=True)

    num_df = df.select_dtypes(include="number")
    if not num_df.empty:
        st.dataframe(num_df.describe().round(2), use_container_width=True)
    else:
        st.markdown(
            "<p style='color:#8B8FA8;font-size:13px'>No numeric columns found.</p>",
            unsafe_allow_html=True)

# ── Data sample ──
st.markdown("""
<div style='border-top:0.5px solid rgba(255,255,255,0.06);margin:24px 0 20px 0'></div>
<div style='font-size:18px;font-weight:700;color:#F0F0F0;
     letter-spacing:-0.3px;margin-bottom:14px'>
  Data Sample
  <span style='font-size:13px;font-weight:400;color:#8B8FA8;margin-left:10px'>
    first 5 rows
  </span>
</div>
""", unsafe_allow_html=True)

st.dataframe(df.head(5), use_container_width=True, hide_index=True)

# ── Navigation ──
st.markdown("""
<div style='border-top:0.5px solid rgba(255,255,255,0.06);margin:24px 0 16px 0'></div>
<p style='font-size:13px;font-weight:500;color:#8B8FA8;margin-bottom:10px'>
  Continue with
</p>
""", unsafe_allow_html=True)

n1, n2, n3 = st.columns(3)
with n1:
    if st.button("🤖  Ask AI about this Data",
                 use_container_width=True, key="nav_assistant"):
        st.switch_page("pages/2_Assistant.py")
with n2:
    if st.button("🧹  Clean this Dataset",
                 use_container_width=True, key="nav_clean"):
        st.switch_page("pages/3_Clean.py")
with n3:
    if st.button("🧠  Go to ML Studio",
                 use_container_width=True, key="nav_ml"):
        st.switch_page("pages/4_ML_Studio.py")