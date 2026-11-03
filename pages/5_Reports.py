import html as html_lib
import json
import os
import re
import sys
import tempfile
from datetime import datetime

import streamlit as st
import pandas as pd
from fpdf import FPDF

try:
    from groq import Groq
except ImportError:
    Groq = None

# chart_utils.py (matplotlib charts for the PDF) lives next to Home.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import chart_utils as cu
except Exception:  # matplotlib missing etc. - the report still works, just without charts
    cu = None

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

/* Hero */
.rp-hero {
    position: relative; overflow: hidden; border-radius: 22px;
    border: 0.5px solid rgba(20,184,166,0.22); padding: 34px 40px; margin-bottom: 8px;
    background:
        radial-gradient(480px 240px at 95% 0%, rgba(20,184,166,0.22), transparent 65%),
        radial-gradient(380px 220px at 0% 100%, rgba(127,119,221,0.16), transparent 65%),
        radial-gradient(rgba(255,255,255,0.045) 1px, transparent 1px), #14171F;
    background-size: auto, auto, 22px 22px, auto;
}
.rp-hero-inner { display: flex; align-items: center; justify-content: space-between; gap: 30px; }
.rp-badge {
    display: inline-flex; align-items: center; gap: 8px; background: rgba(20,184,166,0.10);
    border: 0.5px solid rgba(20,184,166,0.3); border-radius: 99px; padding: 5px 15px;
    font-size: 12px; font-weight: 500; color: #5EEAD4; margin-bottom: 16px; letter-spacing: 0.05em;
}
.rp-chip {
    display: inline-block; font-size: 12px; color: #B8BCCC; padding: 5px 13px; margin: 0 8px 8px 0;
    border-radius: 99px; background: rgba(255,255,255,0.04); border: 0.5px solid rgba(255,255,255,0.1);
}
.rp-ring {
    position: relative; width: 112px; height: 112px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
}
.rp-ring::before { content: ''; position: absolute; inset: 10px; border-radius: 50%; background: #181B25; }
.rp-ring-text { position: relative; text-align: center; }
@media (max-width: 1000px) { .rp-ring-box { display: none; } .rp-hero { padding: 26px 22px; } }

/* Stat cards */
.rp-stats { display: grid; gap: 12px; margin: 4px 0 14px 0; }
.rp-stat {
    border-radius: 14px; padding: 14px 18px; border: 0.5px solid rgba(255,255,255,0.07);
    transition: transform .2s ease, box-shadow .2s ease;
}
.rp-stat:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(0,0,0,0.35); }
.rp-stat-label { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: #8B8FA8; }
.rp-stat-value { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; color: #F0F0F0; margin-top: 4px; }
.rp-stat-sub { font-size: 11.5px; color: #8B8FA8; margin-top: 2px; }

/* Cleaning log + summary cards */
.rp-log {
    background: #1A1D27; border: 0.5px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 6px 18px; max-height: 320px; overflow-y: auto;
}
.rp-log-row { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 0.5px solid rgba(255,255,255,0.05); }
.rp-log-row:last-child { border-bottom: none; }
.rp-log-num {
    width: 24px; height: 24px; border-radius: 50%; flex-shrink: 0; margin-top: 1px;
    background: rgba(239,159,39,0.15); color: #EF9F27; font-size: 11px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
}
.rp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 8px; }
.rp-sum-card { border-radius: 14px; padding: 16px 20px; border: 0.5px solid rgba(255,255,255,0.07); }
.rp-sum-title { font-size: 13px; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.01em; }
.rp-sum-text { font-size: 13.5px; line-height: 1.7; color: #D5D8E3; margin: 0 0 6px 0; }
.rp-sum-li { display: flex; gap: 10px; font-size: 13.5px; line-height: 1.65; color: #D5D8E3; margin-bottom: 7px; }
.rp-dot { width: 7px; height: 7px; border-radius: 50%; margin-top: 9px; flex-shrink: 0; }
@media (max-width: 900px) { .rp-grid { grid-template-columns: 1fr; } }

/* Expanders + buttons */
[data-testid="stExpander"] {
    background: #1A1D27 !important; border: 0.5px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important; margin-bottom: 8px;
}
[data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg, rgba(20,184,166,0.28), rgba(127,119,221,0.22)) !important;
    border: 0.5px solid rgba(20,184,166,0.45) !important; border-radius: 12px !important;
    color: #F0F0F0 !important; font-weight: 600 !important; padding: 10px 0 !important;
}
[data-testid="stDownloadButton"] button:hover { border-color: #14B8A6 !important; box-shadow: 0 8px 24px rgba(20,184,166,0.2); }
</style>
""", unsafe_allow_html=True)


def render(markup):
    """Render raw HTML; flattens newlines so Markdown never treats it as a code block."""
    st.markdown(re.sub(r"\n\s*", " ", markup.strip()), unsafe_allow_html=True)


def esc(value):
    """HTML-escape text and neutralise '$' so st.markdown never renders it as math."""
    return html_lib.escape(str(value)).replace("$", "&#36;")


def section_header(icon, title, subtitle, color):
    render(f"""
    <div style='display:flex;align-items:center;gap:14px;background:linear-gradient(90deg,{color}1F,transparent 85%);
         border-left:3px solid {color};border-radius:10px;padding:12px 18px;margin:30px 0 14px 0'>
      <div style='width:34px;height:34px;border-radius:9px;background:{color}26;display:flex;
           align-items:center;justify-content:center;font-size:17px'>{icon}</div>
      <div>
        <div style='font-size:16px;font-weight:700;color:#F0F0F0'>{title}</div>
        <div style='font-size:12px;color:#8B8FA8;margin-top:1px'>{subtitle}</div>
      </div>
    </div>
    """)


def stat_cards(items):
    cards = "".join(
        f"<div class='rp-stat' style='background:linear-gradient(160deg,{c}24,#1A1D27 70%);border-top:2px solid {c}'>"
        f"<div class='rp-stat-label'>{label}</div><div class='rp-stat-value'>{value}</div>"
        + (f"<div class='rp-stat-sub'>{sub}</div>" if sub else "") + "</div>"
        for label, value, c, sub in items
    )
    render(f"<div class='rp-stats' style='grid-template-columns:repeat({len(items)},1fr)'>{cards}</div>")


# ── Sidebar ──
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

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_API_KEY = None
GROQ_MODEL = "openai/gpt-oss-20b"

missing_before = int(original_df.isnull().sum().sum())
missing_now = int(df.isnull().sum().sum())
dupes_now = int(df.duplicated().sum())
cells = max(df.shape[0] * df.shape[1], 1)
completeness = 100 * (1 - missing_now / cells)
ring_color = "#14B8A6" if completeness >= 95 else "#EF9F27" if completeness >= 85 else "#E24B4A"

# ================================================================
# HERO
# ================================================================

render(f"""
<div class='rp-hero'>
  <div class='rp-hero-inner'>
    <div style='min-width:0'>
      <div class='rp-badge'>📄 &nbsp;Analysis Report</div>
      <div style='font-size:34px;font-weight:800;letter-spacing:-1px;line-height:1.15;color:#F0F0F0'>
        Your data, <span style='background:linear-gradient(90deg,#14B8A6,#5EEAD4 60%,#A7F3D0);
        -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent'>summarised</span>
      </div>
      <div style='font-size:13.5px;color:#9CA1B5;margin:8px 0 18px 0'>📄 {esc(st.session_state.filename)}
        &nbsp;·&nbsp; generated {datetime.now():%d %b %Y, %H:%M}</div>
      <div>
        <span class='rp-chip'>{df.shape[0]:,} rows</span>
        <span class='rp-chip'>{df.shape[1]} columns</span>
        <span class='rp-chip'>{len(cleaning_log)} cleaning action{'s' if len(cleaning_log) != 1 else ''}</span>
        <span class='rp-chip'>{'AI summary ready' if st.session_state.get('ai_summary') else 'AI summary not generated'}</span>
      </div>
    </div>
    <div class='rp-ring-box' style='display:flex;align-items:center;gap:18px;flex-shrink:0'>
      <div class='rp-ring' style='background:conic-gradient({ring_color} 0 {completeness:.1f}%, rgba(255,255,255,0.08) {completeness:.1f}% 100%)'>
        <div class='rp-ring-text'>
          <div style='font-size:22px;font-weight:800;color:#F0F0F0'>{completeness:.1f}%</div>
          <div style='font-size:10px;color:#8B8FA8;letter-spacing:0.06em'>COMPLETE</div>
        </div>
      </div>
    </div>
  </div>
</div>
""")

# ================================================================
# 1. DATASET PROFILE
# ================================================================

section_header("📊", "Dataset profile", "Current shape and quality of the dataset", "#14B8A6")

stat_cards([
    ("Rows", f"{df.shape[0]:,}", "#14B8A6", None),
    ("Columns", f"{df.shape[1]}", "#7F77DD", None),
    ("Missing values", f"{missing_now:,}", "#EF9F27" if missing_now else "#1D9E75",
     f"was {missing_before:,} before cleaning" if missing_before != missing_now else "unchanged"),
    ("Duplicate rows", f"{dupes_now:,}", "#E24B4A" if dupes_now else "#1D9E75", None),
])

with st.expander("Column types & missing values", expanded=False):
    profile_rows = [{
        "Column": col, "Type": str(df[col].dtype),
        "Missing": int(df[col].isnull().sum()), "Unique": int(df[col].nunique()),
    } for col in df.columns]
    st.dataframe(pd.DataFrame(profile_rows), use_container_width=True, hide_index=True)

with st.expander("Numeric summary", expanded=False):
    numeric_df = df.select_dtypes(include="number")
    if not numeric_df.empty:
        st.dataframe(numeric_df.describe().T, use_container_width=True)
    else:
        st.caption("No numeric columns in this dataset.")

with st.expander("Sample rows", expanded=False):
    st.dataframe(df.head(10), use_container_width=True)

# ================================================================
# 2. CLEANING LOG
# ================================================================

section_header("🧹", "Cleaning log", "Everything that was changed, in the order it happened", "#EF9F27")

rows_removed = len(original_df) - len(df)
stat_cards([
    ("Rows removed", f"{rows_removed:,}", "#E24B4A" if rows_removed else "#8B8FA8", None),
    ("Missing values fixed", f"{max(missing_before - missing_now, 0):,}", "#1D9E75", None),
    ("Actions applied", f"{len(cleaning_log)}", "#EF9F27", None),
])

if cleaning_log:
    rows_html = "".join(
        f"<div class='rp-log-row'><div class='rp-log-num'>{i}</div>"
        f"<div style='font-size:13px;color:#E4E6EE;line-height:1.55;padding-top:2px'>{esc(str(entry))}</div></div>"
        for i, entry in enumerate(cleaning_log, 1)
    )
    render(f"<div class='rp-log'>{rows_html}</div>")
else:
    render("""
    <div style='background:#1A1D27;border:0.5px dashed rgba(239,159,39,0.35);border-radius:14px;
         padding:22px;text-align:center;font-size:13px;color:#8B8FA8'>
      No cleaning actions have been applied yet &mdash; visit the <b style='color:#EF9F27'>Clean</b> page to fix issues first.
    </div>
    """)

# ================================================================
# 3. AI-WRITTEN SUMMARY
# ================================================================

section_header("✨", "AI-written summary", "A short plain-English readout of quality, cleaning and next steps", "#7F77DD")

SUMMARY_SECTIONS = [
    ("OVERVIEW", "Overview", "📋", "#14B8A6"),
    ("CLEANING", "Cleaning applied", "🧹", "#EF9F27"),
    ("RISKS", "Remaining risks", "⚠️", "#E24B4A"),
    ("RECOMMENDATIONS", "Recommendations", "💡", "#5DCAA5"),
]


def build_summary_prompt(df, cleaning_log):
    num_cols = df.select_dtypes(include="number").columns.tolist()
    num_summary = "\n".join(
        f"  - {c}: mean={round(df[c].mean(), 2)}, std={round(df[c].std(), 2)}"
        for c in num_cols[:10]
    )
    missing = {c: int(v) for c, v in df.isnull().sum().items() if v > 0}
    log_text = "\n".join(f"  - {entry}" for entry in cleaning_log) or "  None"

    return f"""You are a data analyst writing a short report summary for CleanSight.

Dataset: {df.shape[0]:,} rows x {df.shape[1]} columns
Columns: {', '.join(df.columns.tolist())}
Remaining missing values: {missing if missing else 'None'}
Numeric summary:
{num_summary if num_summary else '  None'}

Cleaning actions already applied:
{log_text}

Reply with ONE JSON object and nothing else, using exactly these keys:
{{"overview": "2 sentences on size and overall data quality (max 45 words)",
 "cleaning": "2 sentences on what was cleaned and why it mattered; say so if nothing was cleaned (max 45 words)",
 "risks": "2 sentences on leftover missing data or other concerns (max 45 words)",
 "recommendations": ["tip 1 (max 18 words)", "tip 2 (max 18 words)", "tip 3 (max 18 words)"]}}
Use only the figures given. Plain text inside the strings: no markdown symbols, no code."""


def _lines_from_value(value):
    """JSON value (string or list) -> [(is_bullet, text), ...]."""
    if isinstance(value, list):
        return [(True, re.sub(r"[*#`]+", "", str(v)).strip()) for v in value if str(v).strip()]
    text = re.sub(r"[*#`]+", "", str(value or "")).strip()
    return [(False, text)] if text else []


def parse_summary(text):
    """Return [(key, [(is_bullet, text), ...]), ...] in display order, or None if unstructured.

    1) JSON object with overview / cleaning / risks / recommendations (what the prompt asks for)
    2) fallback: ALL-CAPS "HEADING:" blocks, matched by keyword (so a typo like
       'REMEMBERING RISKS' still lands in the right card) or by position when there are exactly four.
    """
    if not text:
        return None

    # 1) JSON
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict):
                aliases = {"OVERVIEW": ("overview", "summary"), "CLEANING": ("cleaning", "cleaning_applied", "cleaning applied"),
                           "RISKS": ("risks", "remaining_risks", "remaining risks"),
                           "RECOMMENDATIONS": ("recommendations", "recommendation", "tips")}
                found = {}
                for key, names in aliases.items():
                    for name in names:
                        if name in data:
                            lines = _lines_from_value(data[name])
                            if lines:
                                found[key] = lines
                            break
                if len(found) >= 2:
                    return [(k, found[k]) for k, *_ in SUMMARY_SECTIONS if k in found]
        except Exception:
            pass

    # 2) heading-based text
    plain = re.sub(r"[*#`]+", "", text)
    pattern = r"(?m)^[ \t]*([A-Z][A-Z &/]{3,30}?)[ \t]*:[ \t]*"
    parts = re.split(pattern, plain)
    heads = [parts[i].strip() for i in range(1, len(parts) - 1, 2)]
    bodies = [parts[i + 1] for i in range(1, len(parts) - 1, 2)]
    if len(heads) < 2:
        return None

    def keyword(head):
        h = head.upper()
        if "OVER" in h or "SUMMARY" in h: return "OVERVIEW"
        if "CLEAN" in h: return "CLEANING"
        if "RISK" in h or "CONCERN" in h: return "RISKS"
        if "RECOMMEND" in h or "NEXT" in h or "TIP" in h: return "RECOMMENDATIONS"
        return None

    keys = [keyword(h) for h in heads]
    order = [k for k, *_ in SUMMARY_SECTIONS]
    if len(heads) == 4 and (None in keys or len(set(keys)) < 4):
        keys = order  # fixed order requested in the prompt -> position decides
    found = {}
    for key, body in zip(keys, bodies):
        if key is None or key in found:
            continue
        lines = []
        for raw in body.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            bullet = bool(re.match(r"^([-•]|\d+[.)])\s+", raw))
            lines.append((bullet, re.sub(r"^([-•]|\d+[.)])\s+", "", raw)))
        if lines:
            found[key] = lines
    if len(found) < 2:
        return None
    return [(k, found[k]) for k in order if k in found]


def render_summary_html(lines, color):
    out, bullets = "", []
    def flush():
        nonlocal out, bullets
        if bullets:
            out += "".join(
                f"<div class='rp-sum-li'><span class='rp-dot' style='background:{color}'></span>"
                f"<span>{esc(b)}</span></div>" for b in bullets)
            bullets = []
    for is_bullet, txt in lines:
        if is_bullet:
            bullets.append(txt)
        else:
            flush()
            out += f"<p class='rp-sum-text'>{esc(txt)}</p>"
    flush()
    return out


if "ai_summary" not in st.session_state:
    st.session_state.ai_summary = None

if st.button("✨ Generate AI summary", key="gen_summary"):
    if Groq is None:
        st.error("The `groq` package isn't installed. Run `pip install groq`.")
    elif not GROQ_API_KEY:
        st.error("GROQ_API_KEY isn't configured. Add it to .streamlit/secrets.toml locally, "
                 "or to Settings > Secrets on Streamlit Cloud.")
    else:
        with st.spinner("Writing summary..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)
                kwargs = dict(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": build_summary_prompt(df, cleaning_log)}],
                    max_tokens=2000,
                )
                try:
                    # reasoning model: keep reasoning light so the visible answer isn't cut off
                    resp = client.chat.completions.create(reasoning_effort="low", **kwargs)
                except Exception:
                    resp = client.chat.completions.create(**kwargs)
                st.session_state.ai_summary = (resp.choices[0].message.content or "").strip()
                if resp.choices[0].finish_reason == "length":
                    st.warning("The summary was cut short - click Generate again for a complete one.")
            except Exception as e:
                if "401" in str(e) or "invalid_api_key" in str(e):
                    st.error("Groq rejected the API key (401). Check that GROQ_API_KEY in your secrets is complete and still active.")
                else:
                    st.error(f"Couldn't generate the summary: {e}")

summary_text = st.session_state.ai_summary
parsed = parse_summary(summary_text)

if parsed:
    cards = ""
    for key, lines in parsed:
        _, title, icon, color = next(s for s in SUMMARY_SECTIONS if s[0] == key)
        cards += (
            f"<div class='rp-sum-card' style='background:linear-gradient(160deg,{color}22,#1A1D27 65%);"
            f"border-top:2px solid {color}'>"
            f"<div class='rp-sum-title' style='color:{color}'>{icon}&nbsp; {title}</div>"
            f"{render_summary_html(lines, color)}</div>"
        )
    render(f"<div class='rp-grid'>{cards}</div>"
           "<div style='font-size:11px;color:#6B7089;margin-top:12px'>Generated by GPT-OSS 20B from your dataset's computed statistics and cleaning log</div>")
elif summary_text:
    # Unstructured reply: still show it cleanly (markdown symbols stripped, paragraphs kept)
    paras = "".join(f"<p class='rp-sum-text'>{esc(p.strip())}</p>"
                    for p in re.sub(r"[*#`{}\"]+", "", summary_text).split("\n") if p.strip())
    render(f"<div class='rp-sum-card' style='background:linear-gradient(160deg,#7F77DD22,#1A1D27 65%);"
           f"border-top:2px solid #7F77DD'>{paras}</div>")
else:
    render("""
    <div style='background:linear-gradient(160deg,rgba(127,119,221,0.14),#1A1D27 65%);
         border:0.5px dashed rgba(127,119,221,0.4);border-radius:14px;padding:26px;text-align:center'>
      <div style='font-size:26px;margin-bottom:6px'>✨</div>
      <div style='font-size:14px;color:#D5D8E3;font-weight:600'>No summary yet</div>
      <div style='font-size:12.5px;color:#8B8FA8;margin-top:4px'>
        Click &ldquo;Generate AI summary&rdquo; and CleanSight will write an overview, a cleaning recap,
        remaining risks and recommendations.</div>
    </div>
    """)

# ================================================================
# 4. EXPORT
# ================================================================

section_header("📦", "Export", "Take the report and the cleaned data with you", "#5DCAA5")


def pdf_safe(text):
    """fpdf (classic) only supports latin-1. Swap common Unicode punctuation for ASCII
    equivalents, then drop anything else it can't encode instead of crashing the export."""
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


def build_pdf(df, original_df, cleaning_log, summary, custom_specs=(), include_visuals=False):
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
    sections = parse_summary(summary)
    if sections:
        for key, lines in sections:
            title = next(s[1] for s in SUMMARY_SECTIONS if s[0] == key)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(20, 130, 130)
            pdf.cell(0, 7, pdf_safe(title), ln=True)
            for is_bullet, txt in lines:
                body_line(("- " if is_bullet else "") + txt)
            pdf.ln(2)
    elif summary:
        body_line(re.sub(r"[*#`]+", "", summary))
    else:
        body_line("No AI summary was generated for this export.")

    if include_visuals and cu is not None:
        pdf.add_page()
        section_title("Visualizations")

        def sub_heading(text):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(20, 130, 130)
            pdf.cell(0, 8, pdf_safe(text), ln=True)
            pdf.ln(1)

        def add_chart(spec):
            """Draw one chart (matplotlib PNG) with a one-line explanation underneath."""
            img_w = 150  # mm
            try:
                fig = cu.render_chart(df, spec)
                w_in, h_in = fig.get_size_inches()
                img_h = img_w * h_in / w_in
                caption = cu.describe_chart(df, spec)
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tmp.close()
                fig.savefig(tmp.name, dpi=130)
                cu.plt.close(fig)
            except Exception:
                body_line(f"(Chart unavailable: {spec.get('type', 'chart')})")
                return
            try:
                if pdf.get_y() + img_h + 14 > pdf.page_break_trigger:
                    pdf.add_page()
                y = pdf.get_y()
                pdf.image(tmp.name, x=(210 - img_w) / 2, y=y, w=img_w)
                pdf.set_y(y + img_h + 1)
            finally:
                try:
                    os.remove(tmp.name)
                except OSError:
                    pass
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(90, 90, 90)
            pdf.set_x((210 - img_w) / 2)
            pdf.multi_cell(img_w, 5, pdf_safe(caption))
            pdf.ln(5)

        auto_specs = [s for s in cu.default_chart_specs(df) if cu.spec_is_valid(df, s)]
        sub_heading(f"Automatic insights ({len(auto_specs)})")
        if auto_specs:
            for spec in auto_specs:
                add_chart(spec)
        else:
            body_line("Not enough distinct column types to generate automatic charts.")

        pdf.ln(2)
        sub_heading(f"Your custom charts ({len(custom_specs)})")
        if custom_specs:
            for spec in custom_specs:
                add_chart(spec)
        else:
            body_line("No custom charts were added. On the Visualize page, build a chart and click "
                      "\"Add this chart to my report\" to include it here.")

    return pdf.output(dest="S").encode("latin-1")


custom_specs = [s for s in st.session_state.get("custom_charts", []) if cu is not None and cu.spec_is_valid(df, s)]
auto_count = len([s for s in cu.default_chart_specs(df) if cu.spec_is_valid(df, s)]) if cu is not None else 0

include_visuals = st.checkbox(
    f"Include visualizations in the PDF ({auto_count} automatic + {len(custom_specs)} custom chart"
    f"{'s' if len(custom_specs) != 1 else ''}, each with a one-line explanation)",
    value=cu is not None, key="pdf_include_visuals", disabled=cu is None)
if cu is None:
    st.caption("Charts are unavailable because matplotlib couldn't be loaded.")
elif include_visuals and not custom_specs:
    st.caption("Tip: build your own charts on the Visualize page and add them to the report.")

pdf_sig = (st.session_state.filename, df.shape, missing_now, len(cleaning_log), summary_text or "",
           tuple(cu.spec_key(s) for s in custom_specs) if cu is not None else (), include_visuals)

e1, e2 = st.columns(2, gap="medium")
with e1:
    render("<div style='font-size:12.5px;color:#8B8FA8;margin-bottom:8px'>"
           "<b style='color:#5EEAD4'>PDF report</b> &mdash; profile, cleaning log, AI summary and charts</div>")
    if st.button("🛠️ Build PDF report", key="build_pdf_btn", use_container_width=True):
        with st.spinner("Building the report and drawing charts..."):
            try:
                st.session_state.pdf_report = {
                    "sig": pdf_sig,
                    "bytes": build_pdf(df, original_df, cleaning_log, summary_text, custom_specs, include_visuals),
                }
            except Exception as e:
                st.error(f"PDF export failed: {e}")
    ready = st.session_state.get("pdf_report")
    if ready and ready["sig"] == pdf_sig:
        st.download_button(
            "📄 Download PDF report",
            data=ready["bytes"],
            file_name=f"cleansight_report_{st.session_state.filename.rsplit('.', 1)[0]}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    elif ready:
        st.caption("Your data, summary or charts changed since this PDF was built - build it again.")
with e2:
    render(f"<div style='font-size:12.5px;color:#8B8FA8;margin-bottom:8px'>"
           f"<b style='color:#5EEAD4'>Cleaned data</b> &mdash; {df.shape[0]:,} rows × {df.shape[1]} columns as CSV</div>")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📊 Export cleaned data as CSV",
        data=csv_bytes,
        file_name=f"cleaned_{st.session_state.filename}",
        mime="text/csv",
        use_container_width=True,
    )