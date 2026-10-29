import html as html_lib
import streamlit as st
import pandas as pd
import numpy as np

try:
    from groq import Groq
except ImportError:
    Groq = None

st.set_page_config(page_title="Profiler · CleanSight", layout="wide")
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

[data-testid="stMetric"] {
    background: #1A1D27 !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important; font-weight: 500 !important;
    color: #8B8FA8 !important; text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stMetricValue"] {
    font-size: 20px !important; font-weight: 700 !important;
    color: #F0F0F0 !important; letter-spacing: -0.3px !important;
}

/* Column-list buttons styled as a file-tree / inbox list */
div[data-testid="stVerticalBlockBorderWrapper"] .stButton button {
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 10px 12px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #B8BCCC !important;
    width: 100% !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] .stButton button:hover {
    background: rgba(20,184,166,0.08) !important;
    color: #F0F0F0 !important;
}
</style>
""", unsafe_allow_html=True)

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
<div style='padding:24px 0 16px 0;border-bottom:0.5px solid rgba(255,255,255,0.06);
     margin-bottom:18px;font-family:Inter,sans-serif'>
  <div style='font-size:12px;font-weight:600;color:#14B8A6;letter-spacing:0.1em;
       text-transform:uppercase;margin-bottom:6px'>Data Profiler</div>
  <div style='display:flex;align-items:center;justify-content:space-between'>
    <div>
      <div style='font-size:28px;font-weight:700;color:#F0F0F0;letter-spacing:-0.5px;
           line-height:1.2;margin-bottom:4px'>Dataset Overview</div>
      <div style='font-size:13px;color:#8B8FA8'>📄 {st.session_state.filename}</div>
    </div>
    <div style='background:rgba(29,158,117,0.1);border:0.5px solid rgba(29,158,117,0.25);
         border-radius:99px;padding:5px 14px;font-size:12px;font-weight:500;color:#5DCAA5'>
      ✓ &nbsp;Loaded
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Thin global stats strip ──
total_missing = int(df.isnull().sum().sum())
total_dupes = int(df.duplicated().sum())
completeness = (1 - df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Rows", f"{df.shape[0]:,}")
s2.metric("Columns", df.shape[1])
s3.metric("Missing", f"{total_missing:,}")
s4.metric("Duplicates", f"{total_dupes:,}")
s5.metric("Completeness", f"{completeness:.1f}%")

st.markdown("<div style='margin:18px 0'></div>", unsafe_allow_html=True)

# ── Helpers ──
def infer_type(col):
    dtype = str(df[col].dtype)
    if "bool" in dtype:
        return "boolean"
    if "datetime" in dtype:
        return "datetime"
    if "int" in dtype or "float" in dtype:
        return "numeric"
    if df[col].nunique() < 20:
        return "category"
    return "string"

TYPE_COLORS = {
    "numeric":  ("rgba(20,184,166,0.12)",  "#14B8A6"),
    "category": ("rgba(127,119,221,0.12)", "#7F77DD"),
    "string":   ("rgba(136,135,128,0.12)", "#888780"),
    "boolean":  ("rgba(239,159,39,0.12)",  "#EF9F27"),
    "datetime": ("rgba(29,158,117,0.12)",  "#1D9E75"),
}

# ── AI Quick Insights helpers ──
def get_api_key():
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return None


def insight_facts(df):
    """Verified facts from the data - used for the AI prompt and the rule-based fallback."""
    rows, cols = df.shape
    miss = df.isnull().sum()
    miss = miss[miss > 0].sort_values(ascending=False)
    facts = {
        "rows": rows, "cols": cols,
        "completeness": 100 * (1 - int(miss.sum()) / max(rows * cols, 1)),
        "dupes": int(df.duplicated().sum()),
        "missing_cols": len(miss),
        "missing": [(c, int(v), 100 * v / max(rows, 1)) for c, v in miss.head(4).items()],
    }

    num = df.select_dtypes(include="number")
    usable = []
    for c in num.columns:
        n = num[c].nunique(dropna=True)
        is_id = n == rows and str(num[c].dtype).startswith("int")
        if n > 2 and not is_id:
            usable.append(c)

    pairs = []
    if len(usable) >= 2:
        corr = num[usable].corr()
        for i, a in enumerate(usable):
            for b in usable[i + 1:]:
                r = corr.loc[a, b]
                if pd.notna(r) and abs(r) >= 0.3:
                    pairs.append((a, b, float(r)))
    facts["corr"] = sorted(pairs, key=lambda t: abs(t[2]), reverse=True)[:3]

    skewed, outliers = [], []
    for c in usable:
        s = num[c].dropna()
        if len(s) > 10:
            sk = s.skew()
            if abs(sk) > 1:
                skewed.append((c, float(sk)))
            if s.nunique() >= 10:
                q1, q3 = s.quantile(0.25), s.quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    n_out = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
                    if n_out > 0:
                        outliers.append((c, n_out, 100 * n_out / rows))
    facts["skewed"] = sorted(skewed, key=lambda t: abs(t[1]), reverse=True)[:2]
    facts["outliers"] = sorted(outliers, key=lambda t: t[1], reverse=True)[:2]

    imbalance = []
    for c in df.columns:
        n = df[c].nunique(dropna=True)
        if 2 <= n <= 3:
            vc = df[c].value_counts(normalize=True)
            if vc.iloc[0] >= 0.7:
                imbalance.append((c, str(vc.index[0]), float(vc.iloc[0])))
    facts["imbalance"] = sorted(imbalance, key=lambda t: t[2], reverse=True)[:2]
    return facts


def facts_to_text(f):
    lines = [
        f"Rows: {f['rows']:,}; Columns: {f['cols']}",
        f"Completeness: {f['completeness']:.1f}%; Duplicate rows: {f['dupes']:,}",
        "Missing values: " + ("; ".join(f"{c} {n:,} ({p:.1f}%)" for c, n, p in f["missing"]) or "none")
        + (f" (+ {f['missing_cols'] - len(f['missing'])} more columns)" if f["missing_cols"] > len(f["missing"]) else ""),
        "IQR outliers: " + ("; ".join(f"{c} {n:,} rows ({p:.1f}%)" for c, n, p in f["outliers"]) or "none notable"),
        "Skewed columns: " + ("; ".join(f"{c} (skew {s:.1f})" for c, s in f["skewed"]) or "none notable"),
        "Strongest correlations: " + ("; ".join(f"{a} vs {b} r={r:.2f}" for a, b, r in f["corr"]) or "none above 0.3"),
        "Imbalanced columns: " + ("; ".join(f"{c} '{v}' = {s:.0%}" for c, v, s in f["imbalance"]) or "none"),
    ]
    return "\n".join(lines)


def rule_based_insights(f):
    out = []
    dup_txt = f"{f['dupes']:,} duplicate rows" if f["dupes"] else "no duplicate rows"
    out.append(f"📋 {f['rows']:,} rows × {f['cols']} columns — {f['completeness']:.1f}% complete with {dup_txt}.")
    if f["missing"]:
        c, n, p = f["missing"][0]
        out.append(f"🕳️ {c} has the most missing values ({n:,}, {p:.1f}%); {f['missing_cols']} column(s) are affected in total.")
    else:
        out.append("✅ No missing values detected in any column.")
    if f["outliers"]:
        c, n, p = f["outliers"][0]
        out.append(f"📌 {c} has {n:,} IQR outliers ({p:.1f}% of rows) — worth reviewing on the Clean page.")
    elif f["skewed"]:
        c, s = f["skewed"][0]
        out.append(f"📈 {c} is strongly skewed (skew {s:.1f}) — the median may describe it better than the mean.")
    if f["corr"]:
        a, b, r = f["corr"][0]
        direction = "positively" if r > 0 else "negatively"
        out.append(f"🔗 {a} and {b} are {direction} correlated (r = {r:.2f}).")
    if f["imbalance"]:
        c, v, s = f["imbalance"][0]
        out.append(f"⚖️ {c} is imbalanced — '{v}' makes up {s:.0%} of its values.")
    needs_clean = bool(f["missing"] or f["outliers"] or f["dupes"])
    next_step = ("➡️ Next step: head to Clean to fix the flagged issues." if needs_clean
                 else "➡️ Next step: explore relationships on the Visualize page.")
    return out[:4] + [next_step]


def ai_insights(facts_text):
    """Returns a list of insight strings, or None if the AI is unavailable or the reply is unusable."""
    key = get_api_key()
    if not key or Groq is None:
        return None
    prompt = f"""You are a data analyst writing quick insights for a dataset profiler.
Use ONLY the facts below. Do not invent numbers.
Write exactly 4 insights, one per line, each starting with one relevant emoji and at most 22 words.
Cover, where the facts allow: overall data quality, the most important missing-value or outlier issue, the most notable relationship or imbalance, and one concrete next step.
No headers, no markdown, no extra text.

Facts:
{facts_text}"""
    kwargs = dict(model="openai/gpt-oss-20b", messages=[{"role": "user", "content": prompt}], max_tokens=1500)
    try:
        client = Groq(api_key=key)
        try:
            resp = client.chat.completions.create(reasoning_effort="low", **kwargs)
        except Exception:
            resp = client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        if choice.finish_reason == "length":
            return None
        lines = [l.strip().lstrip("-•*0123456789.) ").strip() for l in (choice.message.content or "").splitlines()]
        lines = [l for l in lines if len(l) > 15]
        return lines[:5] if len(lines) >= 3 else None
    except Exception:
        return None


if "profiler_selected_col" not in st.session_state:
    st.session_state.profiler_selected_col = "__overview__"

# ================================================================
# COMMAND CENTER — split pane: column list (left) + detail (right)
# ================================================================

left, right = st.columns([1, 2.2], gap="medium")

with left:
    st.markdown("""
    <div style='font-size:13px;font-weight:600;color:#8B8FA8;
         text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px'>
      Columns
    </div>
    """, unsafe_allow_html=True)

    with st.container(height=560, border=True):
        overview_active = "▸ " if st.session_state.profiler_selected_col == "__overview__" else ""
        if st.button(f"{overview_active}🏠  Overview", key="col_overview", use_container_width=True):
            st.session_state.profiler_selected_col = "__overview__"
            st.rerun()

        st.markdown(
            "<div style='border-top:0.5px solid rgba(255,255,255,0.06);margin:6px 0'></div>",
            unsafe_allow_html=True)

        for col in df.columns:
            col_type = infer_type(col)
            _, fg = TYPE_COLORS.get(col_type, ("rgba(128,128,128,0.1)", "gray"))
            missing = int(df[col].isnull().sum())
            active = "▸ " if st.session_state.profiler_selected_col == col else ""
            flag = " ⚠️" if missing > 0 else ""
            if st.button(f"{active}{col}{flag}", key=f"col_btn_{col}", use_container_width=True):
                st.session_state.profiler_selected_col = col
                st.rerun()

with right:
    selected = st.session_state.profiler_selected_col

    if selected == "__overview__":
        sig = (st.session_state.filename, df.shape, total_missing, total_dupes)
        cache = st.session_state.get("profiler_insights")

        hl, hr = st.columns([3, 1])
        with hl:
            st.markdown(
                "<div style='font-size:18px;font-weight:700;color:#F0F0F0;"
                "letter-spacing:-0.3px;margin-bottom:6px'>✨ AI Quick Insights</div>",
                unsafe_allow_html=True)
        with hr:
            regen = st.button("↻ Regenerate", key="regen_insights", use_container_width=True)

        if regen or not cache or cache["sig"] != sig:
            facts = insight_facts(df)
            with st.spinner("Analyzing your dataset..."):
                items = ai_insights(facts_to_text(facts))
                source = "ai"
                if not items:
                    items = rule_based_insights(facts)
                    source = "rules"
            cache = {"sig": sig, "items": items, "source": source}
            st.session_state.profiler_insights = cache

        rows_html = "".join(
            "<div style='padding:9px 0;border-bottom:0.5px solid rgba(255,255,255,0.05);"
            "font-size:13.5px;color:#D5D8E3;line-height:1.6'>" + html_lib.escape(item) + "</div>"
            for item in cache["items"]
        )
        footer = ("Generated by GPT-OSS 20B from your dataset's computed statistics"
                  if cache["source"] == "ai"
                  else "Rule-based insights computed from your data (AI summary unavailable right now)")
        st.markdown(
            "<div style='background:rgba(20,184,166,0.06);border:0.5px solid rgba(20,184,166,0.18);"
            "border-radius:12px;padding:8px 18px 12px 18px;margin-bottom:22px'>"
            + rows_html +
            "<div style='font-size:11px;color:#6B7089;margin-top:10px'>" + footer + "</div></div>",
            unsafe_allow_html=True)

        st.markdown("""
        <div style='font-size:18px;font-weight:700;color:#F0F0F0;
             letter-spacing:-0.3px;margin-bottom:14px'>Data Sample</div>
        """, unsafe_allow_html=True)
        st.dataframe(df.head(8), use_container_width=True, hide_index=True)

    else:
        col = selected
        series = df[col]
        col_type = infer_type(col)
        bg, fg = TYPE_COLORS.get(col_type, ("rgba(128,128,128,0.1)", "gray"))
        missing = int(series.isnull().sum())
        miss_pct = round(missing / len(df) * 100, 1)
        unique = int(series.nunique())

        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:10px;margin-bottom:16px'>
          <div style='font-size:22px;font-weight:700;color:#F0F0F0'>{col}</div>
          <span style='background:{bg};color:{fg};padding:4px 12px;border-radius:99px;
               font-size:11px;font-weight:600'>{col_type}</span>
        </div>
        """, unsafe_allow_html=True)

        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Missing", f"{missing} ({miss_pct}%)")
        d2.metric("Unique values", f"{unique:,}")
        d3.metric("Dtype", str(series.dtype))
        if col_type == "numeric":
            d4.metric("Mean", f"{series.mean():.2f}" if series.notna().any() else "—")
        else:
            d4.metric("Most common", str(series.mode()[0]) if not series.mode().empty else "—")

        st.markdown("<div style='margin:14px 0'></div>", unsafe_allow_html=True)

        # Flags
        flags = []
        if missing > 0:
            flags.append(("⚠️ Missing values", f"{missing} rows ({miss_pct}%)", "#EF9F27"))
        if col_type == "numeric" and series.notna().sum() > 4:
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outliers = int(((series < lower) | (series > upper)).sum())
            if outliers > 0:
                flags.append(("📌 Outliers (IQR)", f"{outliers} rows outside [{lower:.1f}, {upper:.1f}]", "#E24B4A"))
        if col_type in ("string", "category") and unique == len(df):
            flags.append(("🆔 Likely identifier", "Every value is unique", "#7F77DD"))

        if flags:
            for label, detail, color in flags:
                st.markdown(f"""
                <div style='background:#1A1D27;border:0.5px solid rgba(255,255,255,0.07);
                     border-left:3px solid {color};border-radius:8px;padding:10px 14px;
                     margin-bottom:8px;font-size:13px'>
                  <span style='color:{color};font-weight:600'>{label}</span>
                  <span style='color:#8B8FA8'> — {detail}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<div style='margin:10px 0'></div>", unsafe_allow_html=True)

        # Distribution
        st.markdown("""
        <div style='font-size:14px;font-weight:600;color:#F0F0F0;margin-bottom:10px'>
          Distribution
        </div>
        """, unsafe_allow_html=True)

        if col_type == "numeric" and series.notna().sum() > 1:
            counts, bin_edges = np.histogram(series.dropna(), bins=min(20, series.nunique()))
            labels = [f"{bin_edges[i]:.1f}" for i in range(len(counts))]
            st.bar_chart(pd.DataFrame({"count": counts}, index=labels))
            st.dataframe(series.describe().to_frame().T.round(2), use_container_width=True, hide_index=True)
        elif series.notna().sum() > 0:
            top_values = series.value_counts().head(12)
            st.bar_chart(top_values)
        else:
            st.caption("No non-null values to visualize.")

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
    if st.button("📊  Visualize this Data",
                 use_container_width=True, key="nav_visualize"):
        st.switch_page("pages/4_Visualize.py")