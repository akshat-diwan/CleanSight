import io
import tempfile
from datetime import datetime

import streamlit as st
import pandas as pd
from fpdf import FPDF

try:
    from groq import Groq
except ImportError:
    Groq = None

st.set_page_config(page_title="Reports · CleanSight", layout="wide")
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
body, p, div, span, h1, h2, h3, h4, h5, h6, label, button, input, textarea, li, td, th {
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stIconMaterial"], [data-testid="stExpanderIcon"],
.material-symbols-rounded, .material-symbols-outlined, .material-icons {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
}
[data-testid="stSidebarCollapseButton"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("assets/logo.svg")
    st.caption("Automated data profiling & cleaning")
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
original_df = st.session_state.get("original_df", df)
cleaning_log = st.session_state.get("cleaning_log", [])

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
GROQ_MODEL = "openai/gpt-oss-20b"

st.markdown("<h2 style='font-weight:500'>📄 Reports</h2>", unsafe_allow_html=True)
st.caption(f"Export your full analysis · {st.session_state.filename}")
st.divider()


# ================================================================
# 1. DATASET PROFILE
# ================================================================

st.markdown("#### 📊 Dataset profile")

missing_before = int(original_df.isnull().sum().sum())
missing_now = int(df.isnull().sum().sum())
dupes_now = int(df.duplicated().sum())

p1, p2, p3, p4 = st.columns(4)
p1.metric("Rows", f"{df.shape[0]:,}")
p2.metric("Columns", df.shape[1])
p3.metric("Missing values (now)", f"{missing_now:,}")
p4.metric("Duplicate rows", dupes_now)

with st.expander("Column types & missing values", expanded=False):
    profile_rows = []
    for col in df.columns:
        profile_rows.append({
            "Column": col,
            "Type": str(df[col].dtype),
            "Missing": int(df[col].isnull().sum()),
            "Unique": int(df[col].nunique()),
        })
    st.dataframe(pd.DataFrame(profile_rows), use_container_width=True, hide_index=True)

with st.expander("Numeric summary", expanded=False):
    numeric_df = df.select_dtypes(include="number")
    if not numeric_df.empty:
        st.dataframe(numeric_df.describe().T, use_container_width=True)
    else:
        st.caption("No numeric columns in this dataset.")

with st.expander("Sample rows", expanded=False):
    st.dataframe(df.head(10), use_container_width=True)

st.divider()


# ================================================================
# 2. CLEANING LOG
# ================================================================

st.markdown("#### 🧹 Cleaning log")

c1, c2, c3 = st.columns(3)
c1.metric("Rows removed", len(original_df) - len(df))
c2.metric("Missing values fixed", max(missing_before - missing_now, 0))
c3.metric("Actions applied", len(cleaning_log))

if cleaning_log:
    st.markdown(
        "".join(
            f"<div style='padding:6px 0;border-bottom:0.5px solid rgba(255,255,255,0.06);"
            f"font-size:13px;opacity:0.85'>✓ {entry}</div>"
            for entry in cleaning_log
        ),
        unsafe_allow_html=True,
    )
else:
    st.info("No cleaning actions have been applied yet. Visit the Clean page to fix issues first.")

st.divider()


# ================================================================
# 3. AI-WRITTEN SUMMARY
# ================================================================

st.markdown("#### ✨ AI-written summary")


def build_summary_prompt(df, cleaning_log):
    num_cols = df.select_dtypes(include="number").columns.tolist()
    num_summary = "\n".join(
        f"  - {c}: mean={round(df[c].mean(), 2)}, std={round(df[c].std(), 2)}"
        for c in num_cols[:10]
    )
    missing = {c: int(v) for c, v in df.isnull().sum().items() if v > 0}
    log_text = "\n".join(f"  - {entry}" for entry in cleaning_log) or "  None"

    return f"""You are a data analyst writing a short plain-English report summary for CleanSight.

Dataset: {df.shape[0]:,} rows × {df.shape[1]} columns
Columns: {', '.join(df.columns.tolist())}
Remaining missing values: {missing if missing else 'None'}
Numeric summary:
{num_summary if num_summary else '  None'}

Cleaning actions already applied:
{log_text}

Write a concise summary (150-220 words) covering: overall data quality, what cleaning was
done and why it mattered, any remaining risks or missing data, and 2-3 practical
recommendations. Plain prose, no headers, no code."""


if "ai_summary" not in st.session_state:
    st.session_state.ai_summary = None

if st.button("✨ Generate AI summary", key="gen_summary"):
    if Groq is None:
        st.error("The `groq` package isn't installed. Run `pip install groq`.")
    else:
        with st.spinner("Writing summary..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)
                resp = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": build_summary_prompt(df, cleaning_log)}],
                    max_tokens=500,
                )
                st.session_state.ai_summary = resp.choices[0].message.content
            except Exception as e:
                st.error(f"Couldn't generate the summary: {e}")

if st.session_state.ai_summary:
    st.markdown(f"""
    <div style='border:0.5px solid rgba(20,184,166,0.3);border-radius:12px;
         padding:18px 20px;font-size:13px;background:rgba(20,184,166,0.06);
         line-height:1.8'>
      {st.session_state.ai_summary}
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style='border:0.5px solid rgba(20,184,166,0.3);border-radius:12px;
         padding:18px 20px;font-size:13px;background:rgba(20,184,166,0.06);
         line-height:1.8'>
      <span style='opacity:0.6'>Click "Generate AI summary" to have CleanSight write a
      plain-English summary of your dataset and cleaning results.</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()


# ================================================================
# 4. EXPORT
# ================================================================

st.markdown("#### Export")


def pdf_safe(text):
    """fpdf (classic) only supports latin-1. Swap common Unicode
    punctuation for ASCII equivalents, then drop anything else it
    can't encode instead of crashing the export."""
    if text is None:
        return ""
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u2248": "~",
        "\u2022": "-", "\u00a0": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def build_pdf(df, original_df, cleaning_log, summary):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 130, 130)
    pdf.cell(0, 12, "CleanSight Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 8, pdf_safe(f"{st.session_state.filename}  -  generated {datetime.now():%Y-%m-%d %H:%M}"), ln=True)
    pdf.ln(4)

    def section_title(text):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(0, 10, pdf_safe(text), ln=True)
        pdf.set_draw_color(20, 184, 166)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

    def body_line(text):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 6, pdf_safe(text))

    section_title("Dataset Profile")
    body_line(f"Rows: {df.shape[0]:,}   Columns: {df.shape[1]}")
    body_line(f"Missing values remaining: {int(df.isnull().sum().sum())}")
    body_line(f"Duplicate rows: {int(df.duplicated().sum())}")
    pdf.ln(4)

    section_title("Cleaning Log")
    if cleaning_log:
        for entry in cleaning_log:
            body_line(f"- {entry}")
    else:
        body_line("No cleaning actions were applied.")
    pdf.ln(4)

    section_title("AI Summary")
    body_line(summary if summary else "No AI summary was generated for this export.")

    return pdf.output(dest="S").encode("latin-1")


e1, e2 = st.columns(2)
with e1:
    try:
        pdf_bytes = build_pdf(df, original_df, cleaning_log, st.session_state.ai_summary)
        st.download_button(
            "📄 Export as PDF",
            data=pdf_bytes,
            file_name=f"cleansight_report_{st.session_state.filename.rsplit('.', 1)[0]}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"PDF export failed: {e}")
with e2:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📊 Export cleaned data as CSV",
        data=csv_bytes,
        file_name=f"cleaned_{st.session_state.filename}",
        mime="text/csv",
        use_container_width=True,
    )