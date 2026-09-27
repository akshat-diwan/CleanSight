import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Clean & Transform · CleanSight", layout="wide")
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

# Defensive defaults — older sessions created before these keys existed
if "original_df" not in st.session_state:
    st.session_state.original_df = st.session_state.df.copy()
if "cleaning_log" not in st.session_state:
    st.session_state.cleaning_log = []
if "inconsistency_fixed" not in st.session_state:
    st.session_state.inconsistency_fixed = []

df = st.session_state.df

# ================================================================
# BACKEND — detection + fix logic
# ================================================================

def is_id_column(df, col):
    return df[col].nunique() == len(df) and (
        "id" in col.lower() or str(df[col].dtype).startswith("int")
    )

def is_binary(df, col):
    return df[col].dropna().nunique() <= 2

def outlier_bounds(df, col):
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    return Q1 - 1.5 * IQR, Q3 + 1.5 * IQR, IQR

def apply_missing_fix(df, col, strategy, custom_value=None):
    if strategy.startswith("Median"):
        value = df[col].median()
        df[col] = df[col].fillna(value)
        return df, f"Filled {col} missing values with median ({value:.2f})"
    if strategy.startswith("Mean"):
        value = df[col].mean()
        df[col] = df[col].fillna(value)
        return df, f"Filled {col} missing values with mean ({value:.2f})"
    if strategy.startswith("Mode"):
        value = df[col].mode().iloc[0]
        df[col] = df[col].fillna(value)
        return df, f"Filled {col} missing values with mode ('{value}')"
    if strategy.startswith("Fill with 'Unknown'"):
        df[col] = df[col].fillna("Unknown")
        return df, f"Filled {col} missing values with 'Unknown'"
    if strategy.startswith("Custom value") and custom_value not in (None, ""):
        if pd.api.types.is_numeric_dtype(df[col]):
            try:
                custom_value = float(custom_value)
            except ValueError:
                return df, f"Skipped {col} — '{custom_value}' is not a valid number"
        df[col] = df[col].fillna(custom_value)
        return df, f"Filled {col} missing values with custom value ({custom_value})"
    if strategy.startswith("Drop rows"):
        before = len(df)
        df = df[df[col].notna()].reset_index(drop=True)
        return df, f"Dropped {before - len(df)} rows with missing values in {col}"
    return df, f"No change made to {col}"

def apply_outlier_fix(df, col, strategy):
    lower, upper, iqr = outlier_bounds(df, col)
    mask = (df[col] < lower) | (df[col] > upper)
    count = int(mask.sum())

    if strategy.startswith("Clip"):
        df[col] = df[col].clip(lower=lower, upper=upper)
        return df, f"Clipped {count} outliers in {col} to IQR bounds [{lower:.2f}, {upper:.2f}]"
    if strategy.startswith("Remove rows"):
        before = len(df)
        df = df[~mask | df[col].isna()].reset_index(drop=True)
        return df, f"Removed {before - len(df)} outlier rows from {col}"
    if strategy.startswith("Replace with median"):
        value = df[col].median()
        df.loc[mask, col] = value
        return df, f"Replaced {count} outliers in {col} with median ({value:.2f})"
    if strategy.startswith("Replace with mean"):
        value = df[col].mean()
        df.loc[mask, col] = value
        return df, f"Replaced {count} outliers in {col} with mean ({value:.2f})"
    return df, f"Kept outliers in {col}"

def drop_duplicates(df):
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    removed = before - len(df)
    return df, f"Removed {removed} duplicate rows"

NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20",
}

DATE_PATTERNS = [
    (r"^\d{4}-\d{1,2}-\d{1,2}$", "YYYY-MM-DD"),
    (r"^\d{1,2}/\d{1,2}/\d{4}$", "DD/MM/YYYY"),
    (r"^\d{1,2}-\d{1,2}-\d{4}$", "DD-MM-YYYY"),
    (r"^\d{1,2}/\d{1,2}/\d{2}$", "DD/MM/YY"),
    (r"^\d{4}/\d{1,2}/\d{1,2}$", "YYYY/MM/DD"),
]

def classify_date_pattern(value):
    text = str(value).strip()
    for pattern, label in DATE_PATTERNS:
        if re.match(pattern, text):
            return label
    return None

def detect_inconsistencies(source_df):
    findings = []
    for column in source_df.select_dtypes(include=["object"]).columns:
        series = source_df[column].dropna().astype(str)
        if series.empty:
            continue

        groups = {}
        for value in series.unique():
            key = value.strip().lower()
            groups.setdefault(key, set()).add(value)

        case_variants = {key: v for key, v in groups.items() if len(v) > 1}
        if case_variants:
            examples = "; ".join(", ".join(sorted(v)) for v in list(case_variants.values())[:3])
            affected = int(series.apply(lambda v: v.strip().lower() in case_variants).sum())
            findings.append({
                "Select": True, "Column": column,
                "Issue Type": "Case / whitespace inconsistency",
                "Example Values": examples, "Affected Rows": affected,
                "_fix": "case",
            })

        word_hits = {}
        for value in series.unique():
            normalized = value.strip().lower()
            if normalized in NUMBER_WORDS:
                word_hits.setdefault(NUMBER_WORDS[normalized], set()).add(value)
            elif re.fullmatch(r"\d+", normalized):
                word_hits.setdefault(normalized, set()).add(value)

        number_variants = {digit: v for digit, v in word_hits.items() if len(v) > 1}
        if number_variants:
            examples = "; ".join(", ".join(sorted(v)) for v in list(number_variants.values())[:3])

            def is_affected(v, number_variants=number_variants):
                stripped = v.strip().lower()
                if stripped in NUMBER_WORDS and NUMBER_WORDS[stripped] in number_variants:
                    return True
                if re.fullmatch(r"\d+", v.strip()) and v.strip() in number_variants:
                    return True
                return False

            affected = int(series.apply(is_affected).sum())
            findings.append({
                "Select": True, "Column": column,
                "Issue Type": "Mixed word/number representation",
                "Example Values": examples, "Affected Rows": affected,
                "_fix": "number_word",
            })

        patterns_found = {}
        for value in series.unique():
            label = classify_date_pattern(value)
            if label:
                patterns_found.setdefault(label, []).append(value)

        if len(patterns_found) > 1:
            examples = "; ".join(f"{label}: {vals[0]}" for label, vals in patterns_found.items())
            affected = int(series.apply(lambda v: classify_date_pattern(v) is not None).sum())
            findings.append({
                "Select": True, "Column": column,
                "Issue Type": "Inconsistent date format",
                "Example Values": examples, "Affected Rows": affected,
                "_fix": "date",
            })

    return findings

def apply_inconsistency_fixes(target_df, selected_findings):
    actions = []
    for finding in selected_findings:
        column = finding["Column"]
        fix_type = finding["_fix"]
        if column not in target_df.columns:
            continue

        if fix_type == "case":
            counts = target_df[column].astype(str).value_counts()
            groups = {}
            for value in target_df[column].dropna().astype(str).unique():
                groups.setdefault(value.strip().lower(), []).append(value)
            mapping = {}
            for variants in groups.values():
                if len(variants) > 1:
                    canonical = max(variants, key=lambda v: counts.get(v, 0))
                    for variant in variants:
                        mapping[variant] = canonical
            if mapping:
                target_df[column] = target_df[column].astype(str).replace(mapping)
                actions.append(f"Standardized case/whitespace variants in {column}")

        elif fix_type == "number_word":
            def normalize_number(value):
                text = str(value).strip().lower()
                return NUMBER_WORDS.get(text, value)
            target_df[column] = target_df[column].apply(normalize_number)
            actions.append(f"Converted word-form numbers to digits in {column}")

        elif fix_type == "date":
            def normalize_date(value):
                try:
                    parsed = pd.to_datetime(value, errors="raise", dayfirst=True)
                    return parsed.strftime("%Y-%m-%d")
                except Exception:
                    return value
            target_df[column] = target_df[column].apply(normalize_date)
            actions.append(f"Standardized date format in {column} to YYYY-MM-DD")

    return target_df, actions

def detect_issues(df):
    """Ordered flat list, column by column: missing then outlier, then duplicates last."""
    issues = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = int(df[col].isnull().sum())
        is_numeric = "int" in dtype or "float" in dtype
        is_id = is_id_column(df, col)
        binary = is_binary(df, col)

        if missing > 0 and not is_id and not ("bool" in dtype) and not (is_numeric and binary):
            issues.append({
                "col": col, "kind": "missing", "count": missing,
                "pct": round(missing / len(df) * 100, 1), "numeric": is_numeric,
            })

        if is_numeric and not is_id and not binary and df[col].nunique(dropna=True) >= 10:
            lower, upper, iqr = outlier_bounds(df, col)
            if iqr == 0:
                continue
            count = int(((df[col] < lower) | (df[col] > upper)).sum())
            if count > 0:
                issues.append({
                    "col": col, "kind": "outlier", "count": count,
                    "pct": round(count / len(df) * 100, 1),
                    "lower": lower, "upper": upper,
                })

    dupe_count = int(df.duplicated().sum())
    if dupe_count > 0:
        issues.append({"col": "Duplicate Rows", "kind": "dupes", "count": dupe_count, "pct": None})

    return issues

def get_skipped_columns(df):
    skipped = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        is_numeric = "int" in dtype or "float" in dtype
        missing = int(df[col].isnull().sum())

        if is_id_column(df, col):
            skipped.append({"col": col, "tag": "ID Column", "missing": missing,
                "reason": "Identifiers are never cleaned — filling or clipping would corrupt joins and lookups"})
        elif "bool" in dtype:
            skipped.append({"col": col, "tag": "Boolean", "missing": missing,
                "reason": "True/False columns are skipped — imputing booleans introduces false signal"})
        elif is_numeric and is_binary(df, col):
            skipped.append({"col": col, "tag": "Binary Flag", "missing": missing,
                "reason": "Filling missing values would skew class balance; outlier detection is meaningless on 0/1 flags"})
        elif not is_numeric and missing == 0:
            skipped.append({"col": col, "tag": "No Issues", "missing": missing,
                "reason": "No missing values found and outlier detection does not apply to text columns"})
    return skipped

def finding_key(f):
    return (f["Column"], f["_fix"])

def run_auto_fix(df, issues):
    fixed = 0
    for issue in issues:
        if issue["kind"] == "missing":
            strategy = "Median" if issue["numeric"] else "Mode"
            df, log = apply_missing_fix(df, issue["col"], strategy)
        elif issue["kind"] == "outlier":
            df, log = apply_outlier_fix(df, issue["col"], "Clip to IQR bounds")
        elif issue["kind"] == "dupes":
            df, log = drop_duplicates(df)
        else:
            continue
        st.session_state.cleaning_log.append(log)
        fixed += 1
    return df, fixed

# ================================================================
# HEADER
# ================================================================

issues = detect_issues(df)
total_issues = len(issues)

if "inconsistency_findings" not in st.session_state:
    st.session_state.inconsistency_findings = detect_inconsistencies(df)
fixed_keys = {finding_key(f) for f in st.session_state.inconsistency_fixed}
pending_inconsistencies = [f for f in st.session_state.inconsistency_findings if finding_key(f) not in fixed_keys]

st.markdown(f"""
<div style='padding:24px 0 16px 0;border-bottom:0.5px solid rgba(255,255,255,0.06);
     margin-bottom:20px;font-family:Inter,sans-serif'>
  <div style='font-size:12px;font-weight:600;color:#EF9F27;letter-spacing:0.1em;
       text-transform:uppercase;margin-bottom:6px'>Clean & Transform</div>
  <div style='display:flex;align-items:center;justify-content:space-between'>
    <div>
      <div style='font-size:28px;font-weight:700;color:#F0F0F0;letter-spacing:-0.5px;
           line-height:1.2;margin-bottom:4px'>Data Cleaning</div>
      <div style='font-size:13px;color:#8B8FA8'>📄 {st.session_state.filename}</div>
    </div>
    <div style='background:{"rgba(29,158,117,0.1)" if total_issues == 0 else "rgba(239,159,39,0.1)"};
         border:0.5px solid {"rgba(29,158,117,0.25)" if total_issues == 0 else "rgba(239,159,39,0.25)"};
         border-radius:99px;padding:5px 14px;font-size:12px;font-weight:500;
         color:{"#5DCAA5" if total_issues == 0 else "#EF9F27"}'>
      {"✓ Dataset is Clean" if total_issues == 0 else f"{total_issues} issues remaining"}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── AI Command bar ──
st.markdown("""
<div style='font-size:16px;font-weight:600;color:#F0F0F0;margin-bottom:10px'>
  AI Cleaning Command
</div>
""", unsafe_allow_html=True)

cmd_col, btn_col = st.columns([3, 1])
with cmd_col:
    clean_cmd = st.text_input(
        "cmd", placeholder='"Clean everything" or "Fix missing values only"',
        label_visibility="collapsed", key="clean_cmd"
    )
with btn_col:
    run_ai = st.button("🤖  Run AI Clean", use_container_width=True, key="run_ai")

auto_col, reset_col, _ = st.columns([1, 1, 3])
with auto_col:
    auto_clean = st.button("⚡  Auto-Fix All Issues", use_container_width=True, key="auto_clean")
with reset_col:
    reset_btn = st.button("↺  Reset to Original", use_container_width=True, key="reset_btn")

# ── AI command parser (keyword-based, not an LLM call) ──
if run_ai:
    cmd = (clean_cmd or "").lower().strip()
    if not cmd:
        st.warning("Type a command first, e.g. \"clean everything\" or \"fix missing values only\".")
    else:
        matched = [i for i in issues if
                   ("missing" in cmd and i["kind"] == "missing") or
                   ("outlier" in cmd and i["kind"] == "outlier") or
                   ("duplicate" in cmd and i["kind"] == "dupes") or
                   ("everything" in cmd or "all" in cmd)]
        if not matched:
            st.warning("Couldn't match that to missing values, outliers, or duplicates. "
                        "Try \"clean everything\", \"fix missing values only\", "
                        "\"fix outliers\", or \"remove duplicates\".")
        else:
            df, fixed = run_auto_fix(df, matched)
            st.session_state.df = df
            st.success(f"✓ AI Clean applied {fixed} fix(es) based on your command.")
            st.rerun()

if auto_clean:
    df, fixed = run_auto_fix(df, issues)
    st.session_state.df = df
    st.success(f"✓ Fixed {fixed} issues automatically!")
    st.rerun()

if reset_btn:
    st.session_state.df = st.session_state.original_df.copy()
    st.session_state.cleaning_log = []
    st.session_state.inconsistency_fixed = []
    st.session_state.inconsistency_findings = detect_inconsistencies(st.session_state.original_df)
    st.success("↺ Dataset reset to original.")
    st.rerun()

# ── Skipped columns note (inline banner, matches reference) ──
skipped = get_skipped_columns(df)
skipped_with_missing = [s for s in skipped if s["missing"] > 0]
if skipped_with_missing:
    detail = ", ".join(f"{s['col']}: {s['missing']}" for s in skipped_with_missing)
    total_skipped_missing = sum(s["missing"] for s in skipped_with_missing)
    st.info(f"**Note:** {total_skipped_missing} missing values exist in skipped columns "
            f"({detail}). These were not cleaned because they are ID, boolean, or binary columns.")

st.markdown("<div style='border-top:0.5px solid rgba(255,255,255,0.06);margin:16px 0'></div>",
            unsafe_allow_html=True)

# ================================================================
# MAIN — Issues Detected (left) | After Cleaning (right)
# ================================================================

left, right = st.columns([1.4, 1], gap="large", vertical_alignment="top")

with left:
    st.markdown("""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;
         letter-spacing:-0.3px;margin-bottom:14px'>Issues Detected</div>
    """, unsafe_allow_html=True)

    if not issues:
        st.markdown("""
        <div style='background:rgba(29,158,117,0.08);border:0.5px solid rgba(29,158,117,0.25);
             border-radius:12px;padding:20px;text-align:center;font-size:14px;color:#5DCAA5'>
          ✓ &nbsp;No issues detected — dataset is clean!
        </div>
        """, unsafe_allow_html=True)
    else:
        for idx, issue in enumerate(issues):
            col = issue["col"]

            if issue["kind"] == "missing":
                badge = f"{issue['count']} missing values"
                options = (
                    ["Median (recommended)", "Mean", "Custom value", "Drop rows"]
                    if issue["numeric"] else
                    ["Mode (recommended)", "Fill with 'Unknown'", "Custom value", "Drop rows"]
                )
                hint = "Best for skewed data" if issue["numeric"] else "Most frequent value"

                c1, c2, c3 = st.columns([1.3, 1.9, 0.8])
                with c1:
                    st.markdown(
                        f"<div style='font-size:14px;font-weight:600;color:#F0F0F0;margin-bottom:4px'>{col}</div>"
                        f"<span style='background:rgba(239,159,39,0.1);color:#EF9F27;"
                        f"border:0.5px solid rgba(239,159,39,0.25);padding:3px 10px;"
                        f"border-radius:99px;font-size:11px;font-weight:500'>{badge}</span>",
                        unsafe_allow_html=True)
                with c2:
                    strategy = st.selectbox("Strategy", options, key=f"missing_strategy_{idx}_{col}",
                                             label_visibility="collapsed")
                    custom_value = None
                    if strategy.startswith("Custom value"):
                        custom_value = st.text_input("Custom value", key=f"missing_custom_{idx}_{col}",
                                                      label_visibility="collapsed")
                    st.markdown(f"<div style='font-size:11px;color:#8B8FA8;margin-top:4px'>💡 {hint}</div>",
                                unsafe_allow_html=True)
                with c3:
                    if st.button("Apply", key=f"apply_missing_{idx}_{col}", use_container_width=True):
                        df, log = apply_missing_fix(df, col, strategy, custom_value)
                        st.session_state.df = df
                        st.session_state.cleaning_log.append(log)
                        st.rerun()

            elif issue["kind"] == "outlier":
                badge = f"{issue['count']} outliers"
                with st.expander(f"{col}  —  {badge}"):
                    fig = px.box(df, y=col, title=f"Box Plot: {col}",
                                 color_discrete_sequence=["#14B8A6"])
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#F0F0F0", height=260, margin=dict(t=40, b=10, l=10, r=10),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"IQR bounds: [{issue['lower']:.2f}, {issue['upper']:.2f}]")

                    oc1, oc2 = st.columns([2.3, 0.8])
                    with oc1:
                        strategy = st.selectbox(
                            "Strategy",
                            ["Clip to IQR bounds (recommended)", "Remove rows",
                             "Replace with median", "Replace with mean", "Keep as is"],
                            key=f"outlier_strategy_{idx}_{col}", label_visibility="collapsed",
                        )
                        st.markdown("<div style='font-size:11px;color:#8B8FA8;margin-top:4px'>"
                                    "💡 Cap values at boundaries, no data loss</div>",
                                    unsafe_allow_html=True)
                    with oc2:
                        if st.button("Apply", key=f"apply_outlier_{idx}_{col}", use_container_width=True):
                            df, log = apply_outlier_fix(df, col, strategy)
                            st.session_state.df = df
                            st.session_state.cleaning_log.append(log)
                            st.rerun()

            elif issue["kind"] == "dupes":
                c1, c2, c3 = st.columns([1.3, 1.9, 0.8])
                with c1:
                    st.markdown(
                        f"<div style='font-size:14px;font-weight:600;color:#F0F0F0;margin-bottom:4px'>Duplicate Rows</div>"
                        f"<span style='background:rgba(226,75,74,0.1);color:#E24B4A;"
                        f"border:0.5px solid rgba(226,75,74,0.25);padding:3px 10px;"
                        f"border-radius:99px;font-size:11px;font-weight:500'>{issue['count']} duplicates</span>",
                        unsafe_allow_html=True)
                with c2:
                    st.markdown("<div style='font-size:12px;color:#8B8FA8;padding-top:8px'>"
                                "💡 Keeps the first occurrence, drops the rest</div>", unsafe_allow_html=True)
                with c3:
                    if st.button("Apply", key=f"apply_dupes_{idx}", use_container_width=True):
                        df, log = drop_duplicates(df)
                        st.session_state.df = df
                        st.session_state.cleaning_log.append(log)
                        st.rerun()

            st.markdown("<div style='border-top:0.5px solid rgba(255,255,255,0.05);margin:8px 0'></div>",
                        unsafe_allow_html=True)

    # ── Skipped columns detail popover ──
    if skipped:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.popover(f"Skipped Columns ({len(skipped)}) — Click to See Why", use_container_width=True):
            for item in skipped:
                st.markdown(f"""
                <div style='display:flex;align-items:flex-start;gap:12px;padding:10px 0;
                     border-bottom:0.5px solid rgba(255,255,255,0.05)'>
                  <div>
                    <div style='display:flex;align-items:center;gap:8px;margin-bottom:3px'>
                      <span style='font-size:13px;font-weight:600;color:#F0F0F0'>{item['col']}</span>
                      <span style='background:rgba(20,184,166,0.1);color:#14B8A6;
                           border:0.5px solid rgba(20,184,166,0.2);padding:1px 8px;
                           border-radius:99px;font-size:10px;font-weight:500'>{item['tag']}</span>
                    </div>
                    <div style='font-size:12px;color:#8B8FA8;line-height:1.5'>{item['reason']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ── Data inconsistency detection ──
    st.markdown("<div style='margin:24px 0 14px 0'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;letter-spacing:-0.3px;margin-bottom:6px'>
      🔍 Data Inconsistency Detection
      <span style='color:#8B8FA8;font-weight:400;font-size:13px'>({len(pending_inconsistencies)} pending)</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Case/whitespace variants, mixed word-vs-digit numbers, and inconsistent date formats.")

    all_findings = st.session_state.inconsistency_findings
    if all_findings:
        status_rows = [{
            "Status": "✓ Corrected" if finding_key(f) in fixed_keys else "Pending",
            "Column": f["Column"], "Issue Type": f["Issue Type"],
            "Example Values": f["Example Values"], "Affected Rows": f["Affected Rows"],
        } for f in all_findings]
        st.dataframe(pd.DataFrame(status_rows), hide_index=True, use_container_width=True)

        if pending_inconsistencies:
            for idx, finding in enumerate(pending_inconsistencies):
                pc1, pc2, pc3 = st.columns([1.4, 2.2, 0.8])
                with pc1:
                    st.markdown(
                        f"<div style='font-size:14px;font-weight:600;color:#F0F0F0'>{finding['Column']}</div>"
                        f"<span style='background:rgba(20,184,166,0.1);color:#5EEAD4;"
                        f"border:0.5px solid rgba(20,184,166,0.35);padding:3px 10px;"
                        f"border-radius:99px;font-size:11px;font-weight:500'>{finding['Issue Type']}</span>",
                        unsafe_allow_html=True)
                with pc2:
                    st.markdown(
                        f"<div style='font-size:12px;color:#8B8FA8;padding-top:4px'>"
                        f"e.g. {finding['Example Values']} · {finding['Affected Rows']} rows affected</div>",
                        unsafe_allow_html=True)
                with pc3:
                    if st.button("Fix", key=f"fix_incons_{idx}_{finding['_fix']}", use_container_width=True):
                        df, actions = apply_inconsistency_fixes(df, [finding])
                        st.session_state.df = df
                        st.session_state.inconsistency_fixed.append(finding)
                        st.session_state.cleaning_log.extend(actions)
                        st.rerun()
                st.markdown("<div style='border-top:0.5px solid rgba(255,255,255,0.05);margin:8px 0'></div>",
                            unsafe_allow_html=True)
        else:
            st.success("All detected inconsistencies have been corrected.")
    else:
        st.info("No case, number-format, or date-format inconsistencies detected.")

with right:
    st.markdown("""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;
         letter-spacing:-0.3px;margin-bottom:14px'>After Cleaning</div>
    """, unsafe_allow_html=True)

    total_missing = int(df.isnull().sum().sum())
    total_dupes = int(df.duplicated().sum())
    original_rows = len(st.session_state.original_df)
    rows_removed = original_rows - len(df)
    miss_color = "#5DCAA5" if total_missing == 0 else "#EF9F27"
    dupe_color = "#5DCAA5" if total_dupes == 0 else "#EF9F27"

    st.markdown(f"""
    <div style='background:#1A1D27;border:0.5px solid rgba(255,255,255,0.07);
         border-radius:12px;padding:16px 18px;margin-bottom:14px'>
      <div style='display:flex;justify-content:space-between;padding:8px 0;
           border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <span style='font-size:13px;color:#8B8FA8'>Rows Remaining</span>
        <b style='font-size:14px;color:#F0F0F0'>{len(df):,}</b>
      </div>
      <div style='display:flex;justify-content:space-between;padding:8px 0;
           border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <span style='font-size:13px;color:#8B8FA8'>Rows Removed</span>
        <b style='font-size:14px;color:{"#E24B4A" if rows_removed > 0 else "#8B8FA8"}'>{rows_removed:,}</b>
      </div>
      <div style='display:flex;justify-content:space-between;padding:8px 0;
           border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <span style='font-size:13px;color:#8B8FA8'>Missing Values</span>
        <b style='font-size:14px;color:{miss_color}'>{total_missing:,}</b>
      </div>
      <div style='display:flex;justify-content:space-between;padding:8px 0'>
        <span style='font-size:13px;color:#8B8FA8'>Duplicates</span>
        <b style='font-size:14px;color:{dupe_color}'>{total_dupes:,}</b>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;
         letter-spacing:-0.3px;margin-bottom:12px'>Cleaning Log</div>
    """, unsafe_allow_html=True)

    if not st.session_state.cleaning_log:
        st.markdown("""
        <div style='background:#1A1D27;border:0.5px solid rgba(255,255,255,0.07);
             border-radius:12px;padding:20px;text-align:center;font-size:13px;color:#8B8FA8'>
          No actions taken yet
        </div>
        """, unsafe_allow_html=True)
    else:
        log_rows = ""
        for entry in reversed(st.session_state.cleaning_log):
            log_rows += (
                "<div style=\"display:flex;align-items:flex-start;gap:10px;padding:8px 0;"
                "border-bottom:0.5px solid rgba(255,255,255,0.05)\">"
                "<div style=\"width:20px;height:20px;border-radius:50%;"
                "background:rgba(29,158,117,0.15);color:#5DCAA5;font-size:10px;"
                "display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px\">✓</div>"
                f"<div style=\"font-size:13px;color:#F0F0F0;line-height:1.5\">{entry}</div></div>"
            )
        st.markdown(
            "<div style=\"background:#1A1D27;border:0.5px solid rgba(255,255,255,0.07);"
            "border-radius:12px;padding:8px 14px;max-height:300px;overflow-y:auto;"
            "scrollbar-width:thin;scrollbar-color:#2A2D3A #1A1D27\">" + log_rows + "</div>",
            unsafe_allow_html=True)

    if st.session_state.cleaning_log:
        st.markdown("<br>", unsafe_allow_html=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️  Download Cleaned CSV", data=csv,
            file_name=f"cleaned_{st.session_state.filename}",
            mime="text/csv", use_container_width=True
        )

# ── Navigation ──
st.markdown("""
<div style='border-top:0.5px solid rgba(255,255,255,0.06);margin:24px 0 16px 0'></div>
<p style='font-size:13px;font-weight:500;color:#8B8FA8;margin-bottom:10px'>
  Continue With
</p>
""", unsafe_allow_html=True)

n1, n2, n3 = st.columns(3)
with n1:
    if st.button("📊  Visualize this Data", use_container_width=True, key="nav_visualize"):
        st.switch_page("pages/4_Visualize.py")
with n2:
    if st.button("📄  Generate Report", use_container_width=True, key="nav_report"):
        st.switch_page("pages/5_Reports.py")
with n3:
    if st.button("🤖  Ask AI About This Data", use_container_width=True, key="nav_assistant"):
        st.switch_page("pages/2_Assistant.py")