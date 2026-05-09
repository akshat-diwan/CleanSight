import streamlit as st
import pandas as pd

st.set_page_config(page_title="Profiler · InsightForge AI", layout="wide")
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.image("assets/logo.svg")
    st.caption("Data Intelligence Platform")
    st.divider()
    st.caption("Navigate using the pages above")
    st.divider()
    st.divider()
    if "df" in st.session_state:
        st.success(f"📄 {st.session_state.filename}")
        st.caption(f"{st.session_state.df.shape[0]:,} rows · {st.session_state.df.shape[1]} columns")
    else:
        st.warning("No dataset loaded")
        st.page_link("Home.py", label="← Upload a dataset")

if "df" not in st.session_state:
    st.info("Please upload a dataset on the home page first.")
    st.page_link("Home.py", label="← Go to home")
    st.stop()

df = st.session_state.df

st.markdown("<h2 style='font-weight:500'>📊 Data profiler</h2>", unsafe_allow_html=True)
st.caption(f"Dataset overview · {st.session_state.filename}")
st.divider()

# ── Metrics ──
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Rows", f"{df.shape[0]:,}")
c2.metric("Columns", f"{df.shape[1]}")
c3.metric("Missing values", f"{df.isnull().sum().sum():,}")
c4.metric("Duplicates", f"{df.duplicated().sum():,}")
c5.metric("Numeric cols", f"{len(df.select_dtypes(include='number').columns)}")

st.divider()

left, right = st.columns([1.3, 1], gap="large")

with left:
    st.markdown("#### Column overview")

    TYPE_COLORS = {
        "numeric":  ("rgba(55,138,221,0.12)",  "#378ADD"),
        "category": ("rgba(127,119,221,0.12)", "#7F77DD"),
        "string":   ("rgba(136,135,128,0.12)", "#888780"),
        "boolean":  ("rgba(239,159,39,0.12)",  "#EF9F27"),
        "datetime": ("rgba(29,158,117,0.12)",  "#1D9E75"),
    }

    # Build as a proper dataframe with styled display
    col_data = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = int(df[col].isnull().sum())
        unique = int(df[col].nunique())
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
        col_data.append({
            "Column": col,
            "Type": col_type,
            "Missing": missing,
            "Unique": unique,
        })

    col_df = pd.DataFrame(col_data)

    # Render each row natively using st.columns inside a container
    header1, header2, header3, header4 = st.columns([2, 1.2, 0.8, 0.8])
    header1.markdown("<span style='font-size:12px;opacity:0.5'>Column</span>", unsafe_allow_html=True)
    header2.markdown("<span style='font-size:12px;opacity:0.5'>Type</span>", unsafe_allow_html=True)
    header3.markdown("<span style='font-size:12px;opacity:0.5'>Missing</span>", unsafe_allow_html=True)
    header4.markdown("<span style='font-size:12px;opacity:0.5'>Unique</span>", unsafe_allow_html=True)

    st.markdown("<div style='border-top:0.5px solid rgba(128,128,128,0.15);margin-bottom:4px'></div>",
                unsafe_allow_html=True)

    for _, row in col_df.iterrows():
        bg, fg = TYPE_COLORS.get(row["Type"], ("rgba(128,128,128,0.1)", "gray"))
        miss_color = "#EF9F27" if row["Missing"] > 0 else "#1D9E75"
        r1, r2, r3, r4 = st.columns([2, 1.2, 0.8, 0.8])
        with r1:
            st.markdown(f"<span style='font-size:13px;font-weight:500'>{row['Column']}</span>",
                        unsafe_allow_html=True)
        with r2:
            st.markdown(
                f"<span style='background:{bg};color:{fg};padding:2px 9px;"
                f"border-radius:99px;font-size:11px'>{row['Type']}</span>",
                unsafe_allow_html=True)
        with r3:
            st.markdown(
                f"<span style='font-size:12px;color:{miss_color}'>{row['Missing']}</span>",
                unsafe_allow_html=True)
        with r4:
            st.markdown(
                f"<span style='font-size:12px;opacity:0.5'>{row['Unique']}</span>",
                unsafe_allow_html=True)
        st.markdown(
            "<div style='border-top:0.5px solid rgba(128,128,128,0.07);margin:2px 0'></div>",
            unsafe_allow_html=True)

with right:
    st.markdown("#### AI quick insights")
    st.markdown("""
    <div style='border:0.5px solid rgba(55,138,221,0.3);border-radius:12px;
         padding:14px 16px;font-size:13px;line-height:2;
         background:rgba(55,138,221,0.06)'>
      <span style='color:#378ADD;font-weight:500'>✨ AI insights</span>
      <span style='opacity:0.6'> will appear here once backend is connected.</span><br>
      <span style='opacity:0.45'>
        · Missing value explanations<br>
        · Correlation highlights<br>
        · Class imbalance warnings<br>
        · Suggested next steps
      </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Numeric summary")
    num_df = df.select_dtypes(include="number")
    if not num_df.empty:
        st.dataframe(num_df.describe().round(2), use_container_width=True)
    else:
        st.caption("No numeric columns found.")

st.divider()
st.markdown("#### Data sample — first 5 rows")
st.dataframe(df.head(5), use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)
n1, n2, n3 = st.columns(3)
with n1:
    st.page_link("pages/2_Assistant.py", label="🤖 Ask AI about this data →", use_container_width=True)
with n2:
    st.page_link("pages/3_Clean.py", label="🧹 Clean this dataset →", use_container_width=True)
with n3:
    st.page_link("pages/4_ML_Studio.py", label="🧠 Go to ML studio →", use_container_width=True)