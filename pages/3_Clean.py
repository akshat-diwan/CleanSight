import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Clean & Transform · InsightForge AI", layout="wide")
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.image("assets/logo.svg")
    st.caption("Data intelligence platform")
    st.divider()
    if "df" in st.session_state:
        st.success(f"📄 {st.session_state.filename}")
        st.caption(f"{st.session_state.df.shape[0]:,} rows · {st.session_state.df.shape[1]} columns")
    else:
        st.warning("No dataset loaded")
        if st.button("← Upload a Dataset", key="sidebar_upload"):
            st.switch_page("Home.py")
    st.divider()
    st.caption("Navigate using the pages above")

if "df" not in st.session_state:
    st.info("Please upload a dataset on the home page first.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

# ── Session state init ──
if "cleaning_log" not in st.session_state:
    st.session_state.cleaning_log = []
if "original_df" not in st.session_state:
    st.session_state.original_df = st.session_state.df.copy()

df = st.session_state.df

# ── Helper functions ──
def is_id_column(df, col):
    col_lower = col.lower()
    if any(x in col_lower for x in ["id", "code", "key", "index", "uuid", "ref", "no.", "num"]):
        return True
    if df[col].nunique() == len(df):
        return True
    return False

def is_binary(df, col):
    return df[col].dropna().nunique() <= 2

# ── Backend cleaning functions ──
def fill_missing_numeric(df, col):
    median = df[col].median()
    df[col] = df[col].fillna(median)
    return df, f"Filled {col} missing values with median ({median:.2f})"

def fill_missing_categorical(df, col):
    mode = df[col].mode()[0]
    df[col] = df[col].fillna(mode)
    return df, f"Filled {col} missing values with mode ('{mode}')"

def remove_outliers(df, col):
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    outlier_count = int(((df[col] < lower) | (df[col] > upper)).sum())
    df[col] = df[col].clip(lower=lower, upper=upper)
    return df, f"Clipped {outlier_count} outliers in {col} to IQR bounds [{lower:.2f}, {upper:.2f}]"

def drop_duplicates(df):
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    removed = before - len(df)
    return df, f"Removed {removed} duplicate rows"

def detect_issues(df):
    issues = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = int(df[col].isnull().sum())
        is_numeric = "int" in dtype or "float" in dtype
        is_id = is_id_column(df, col)
        binary = is_binary(df, col)

        # ── Missing values ──
        if missing > 0 and not is_id and not ("bool" in dtype) and not (is_numeric and binary):
            issues.append({
                "col": col,
                "issue": f"{missing} missing values",
                "sev": "warning",
                "fix": "Fill with median" if is_numeric else "Fill with mode",
                "type": "missing_num" if is_numeric else "missing_cat",
                "count": missing
            })

        # ── Outliers ──
        if is_numeric and not is_id and not binary:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            if IQR == 0:
                continue
            outliers = int(((df[col] < Q1 - 1.5*IQR) |
                           (df[col] > Q3 + 1.5*IQR)).sum())
            if outliers > 0:
                issues.append({
                    "col": col,
                    "issue": f"{outliers} outliers",
                    "sev": "error",
                    "fix": "Clip to IQR bounds",
                    "type": "outlier",
                    "count": outliers
                })

    # ── Duplicates ──
    dupes = int(df.duplicated().sum())
    issues.append({
        "col": "Duplicate Rows",
        "issue": f"{dupes} duplicates",
        "sev": "ok" if dupes == 0 else "warning",
        "fix": "Drop duplicate rows" if dupes > 0 else "No action needed",
        "type": "dupes",
        "count": dupes
    })
    return issues

def get_skipped_columns(df):
    skipped = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        is_numeric = "int" in dtype or "float" in dtype
        missing = int(df[col].isnull().sum())
        reasons = []

        if is_id_column(df, col):
            reasons.append(("🔑", "ID column",
                "Identifiers are never cleaned — filling or clipping would corrupt joins and lookups"))
        elif "bool" in dtype:
            reasons.append(("⚡", "Boolean dtype",
                "True/False columns are skipped — imputing booleans introduces false signal"))
        elif is_numeric and is_binary(df, col):
            reasons.append(("🚩", "Binary flag (0/1)",
                "Filling missing values would skew class balance; outlier detection is meaningless on flags"))
        elif not is_numeric and missing == 0:
            reasons.append(("✓", "No issues",
                "No missing values found — nothing to clean"))

        if reasons:
            skipped.append({
                "col": col,
                "icon": reasons[0][0],
                "tag": reasons[0][1],
                "reason": reasons[0][2]
            })
    return skipped

# ── Header ──
total_issues = sum(1 for i in detect_issues(df)
                   if i["count"] > 0 and i["sev"] != "ok")

st.markdown(f"""
<div style='padding:28px 0 20px 0;
     border-bottom:0.5px solid rgba(255,255,255,0.06);
     margin-bottom:24px;font-family:Inter,sans-serif'>
  <div style='font-size:12px;font-weight:600;color:#EF9F27;
       letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px'>
    Clean & Transform
  </div>
  <div style='display:flex;align-items:center;justify-content:space-between'>
    <div>
      <div style='font-size:32px;font-weight:700;color:#F0F0F0;
           letter-spacing:-0.5px;line-height:1.2;margin-bottom:6px'>
        Data Cleaning
      </div>
      <div style='font-size:13px;color:#8B8FA8'>
        📄 {st.session_state.filename}
      </div>
    </div>
    <div style='background:{"rgba(29,158,117,0.1)" if total_issues == 0 else "rgba(239,159,39,0.1)"};
         border:0.5px solid {"rgba(29,158,117,0.25)" if total_issues == 0 else "rgba(239,159,39,0.25)"};
         border-radius:99px;padding:5px 14px;
         font-size:12px;font-weight:500;
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
        "cmd",
        placeholder='"Clean everything" or "Fix missing values only"',
        label_visibility="collapsed", key="clean_cmd"
    )
with btn_col:
    run_ai = st.button("🤖  Run AI Clean", use_container_width=True, key="run_ai")

auto_col, reset_col, _ = st.columns([1, 1, 3])
with auto_col:
    auto_clean = st.button("⚡  Auto-Fix All Issues",
                           use_container_width=True, key="auto_clean")
with reset_col:
    reset_btn = st.button("↺  Reset to Original",
                          use_container_width=True, key="reset_btn")

# ── Handle auto clean ──
if auto_clean:
    issues = detect_issues(df)
    fixed = 0
    for issue in issues:
        if issue["sev"] == "ok" or issue["count"] == 0:
            continue
        if issue["type"] == "missing_num":
            df, log = fill_missing_numeric(df, issue["col"])
        elif issue["type"] == "missing_cat":
            df, log = fill_missing_categorical(df, issue["col"])
        elif issue["type"] == "outlier":
            df, log = remove_outliers(df, issue["col"])
        elif issue["type"] == "dupes" and issue["count"] > 0:
            df, log = drop_duplicates(df)
        else:
            continue
        st.session_state.cleaning_log.append(log)
        fixed += 1
    st.session_state.df = df
    st.success(f"✓ Fixed {fixed} issues automatically!")
    st.rerun()

# ── Handle reset ──
if reset_btn:
    st.session_state.df = st.session_state.original_df.copy()
    st.session_state.cleaning_log = []
    st.success("↺ Dataset reset to original.")
    st.rerun()

st.markdown("""
<div style='border-top:0.5px solid rgba(255,255,255,0.06);margin:16px 0'></div>
""", unsafe_allow_html=True)

# ── Main columns ──
left, right = st.columns([1.4, 1], gap="large")

with left:
    st.markdown("""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;
         letter-spacing:-0.3px;margin-bottom:14px'>
      Issues Detected
    </div>
    """, unsafe_allow_html=True)

    issues = detect_issues(df)

    SEV = {
        "warning": ("rgba(239,159,39,0.1)",  "#EF9F27", "rgba(239,159,39,0.25)"),
        "error":   ("rgba(226,75,74,0.1)",   "#E24B4A", "rgba(226,75,74,0.25)"),
        "ok":      ("rgba(29,158,117,0.1)",  "#1D9E75", "rgba(29,158,117,0.25)"),
    }

    any_issues = any(i["count"] > 0 for i in issues)

    if not any_issues:
        st.markdown("""
        <div style='background:rgba(29,158,117,0.08);
             border:0.5px solid rgba(29,158,117,0.25);
             border-radius:12px;padding:20px;
             text-align:center;font-size:14px;color:#5DCAA5'>
          ✓ &nbsp;No issues detected — dataset is clean!
        </div>
        """, unsafe_allow_html=True)
    else:
        for idx, issue in enumerate(issues):
            bg, fg, border = SEV[issue["sev"]]
            skip = issue["sev"] == "ok" or issue["count"] == 0

            c1, c2, c3 = st.columns([1.4, 1.8, 0.8])
            with c1:
                st.markdown(
                    f"<div style='font-size:14px;font-weight:600;"
                    f"color:#F0F0F0;margin-bottom:4px'>{issue['col']}</div>"
                    f"<span style='background:{bg};color:{fg};"
                    f"border:0.5px solid {border};"
                    f"padding:3px 10px;border-radius:99px;"
                    f"font-size:11px;font-weight:500'>{issue['issue']}</span>",
                    unsafe_allow_html=True)
            with c2:
                st.markdown(
                    f"<div style='font-size:12px;color:#8B8FA8;"
                    f"padding-top:4px'>💡 {issue['fix']}</div>",
                    unsafe_allow_html=True)
            with c3:
                if not skip:
                    if st.button("Apply",
                                 key=f"fix_{idx}_{issue['type']}",
                                 use_container_width=True):
                        if issue["type"] == "missing_num":
                            df, log = fill_missing_numeric(df, issue["col"])
                        elif issue["type"] == "missing_cat":
                            df, log = fill_missing_categorical(df, issue["col"])
                        elif issue["type"] == "outlier":
                            df, log = remove_outliers(df, issue["col"])
                        elif issue["type"] == "dupes":
                            df, log = drop_duplicates(df)
                        st.session_state.df = df
                        st.session_state.cleaning_log.append(log)
                        st.rerun()
                else:
                    st.markdown(
                        "<span style='font-size:12px;color:#5DCAA5'>✓ Clean</span>",
                        unsafe_allow_html=True)

            st.markdown(
                "<div style='border-top:0.5px solid rgba(255,255,255,0.05);"
                "margin:8px 0'></div>", unsafe_allow_html=True)

    # ── Skipped columns ──
    skipped = get_skipped_columns(df)
    if skipped:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(
            f"{len(skipped)} column{'s' if len(skipped) > 1 else ''} "
            f"skipped — click to see why"
        ):
            st.markdown("""
            <div style='font-size:12px;color:#8B8FA8;
                 margin-bottom:12px;line-height:1.6'>
              These columns were excluded from cleaning based on their
              data type or role. Here's the reasoning:
            </div>
            """, unsafe_allow_html=True)

            for item in skipped:
                st.markdown(f"""
                <div style='display:flex;align-items:flex-start;gap:12px;
                     padding:10px 0;
                     border-bottom:0.5px solid rgba(255,255,255,0.05);
                     font-family:Inter,sans-serif'>
                  <div style='font-size:16px;flex-shrink:0;margin-top:1px'>
                    {item['icon']}
                  </div>
                  <div>
                    <div style='display:flex;align-items:center;gap:8px;
                         margin-bottom:3px'>
                      <span style='font-size:13px;font-weight:600;
                           color:#F0F0F0'>{item['col']}</span>
                      <span style='background:rgba(55,138,221,0.1);
                           color:#378ADD;border:0.5px solid rgba(55,138,221,0.2);
                           padding:1px 8px;border-radius:99px;
                           font-size:10px;font-weight:500'>
                        {item['tag']}
                      </span>
                    </div>
                    <div style='font-size:12px;color:#8B8FA8;line-height:1.5'>
                      {item['reason']}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

with right:
    # ── After Cleaning stats ──
    st.markdown("""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;
         letter-spacing:-0.3px;margin-bottom:14px'>
      After Cleaning
    </div>
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
      <div style='display:flex;justify-content:space-between;
           padding:8px 0;border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <span style='font-size:13px;color:#8B8FA8'>Rows remaining</span>
        <b style='font-size:14px;color:#F0F0F0'>{len(df):,}</b>
      </div>
      <div style='display:flex;justify-content:space-between;
           padding:8px 0;border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <span style='font-size:13px;color:#8B8FA8'>Rows removed</span>
        <b style='font-size:14px;
           color:{"#E24B4A" if rows_removed > 0 else "#8B8FA8"}'>
           {rows_removed:,}</b>
      </div>
      <div style='display:flex;justify-content:space-between;
           padding:8px 0;border-bottom:0.5px solid rgba(255,255,255,0.05)'>
        <span style='font-size:13px;color:#8B8FA8'>Missing values</span>
        <b style='font-size:14px;color:{miss_color}'>{total_missing:,}</b>
      </div>
      <div style='display:flex;justify-content:space-between;padding:8px 0'>
        <span style='font-size:13px;color:#8B8FA8'>Duplicates</span>
        <b style='font-size:14px;color:{dupe_color}'>{total_dupes:,}</b>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Cleaning log ──
    st.markdown("""
    <div style='font-size:18px;font-weight:700;color:#F0F0F0;
         letter-spacing:-0.3px;margin-bottom:12px'>
      Cleaning Log
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.cleaning_log:
        st.markdown("""
        <div style='background:#1A1D27;
             border:0.5px solid rgba(255,255,255,0.07);
             border-radius:12px;padding:20px;
             text-align:center;font-size:13px;color:#8B8FA8'>
          No actions taken yet
        </div>
        """, unsafe_allow_html=True)
    else:
        for entry in reversed(st.session_state.cleaning_log):
            st.markdown(f"""
            <div style='display:flex;align-items:flex-start;
                 gap:10px;padding:8px 0;
                 border-bottom:0.5px solid rgba(255,255,255,0.05)'>
              <div style='width:20px;height:20px;border-radius:50%;
                   background:rgba(29,158,117,0.15);color:#5DCAA5;
                   font-size:10px;display:flex;align-items:center;
                   justify-content:center;flex-shrink:0;margin-top:1px'>✓</div>
              <div style='font-size:13px;color:#F0F0F0;line-height:1.5'>
                {entry}
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Download ──
    if st.session_state.cleaning_log:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:14px;font-weight:500;
             color:#8B8FA8;margin-bottom:10px'>
          Export Cleaned Dataset
        </div>
        """, unsafe_allow_html=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️  Download Cleaned CSV",
            data=csv,
            file_name=f"cleaned_{st.session_state.filename}",
            mime="text/csv",
            use_container_width=True
        )

# ── Navigation ──
st.markdown("""
<div style='border-top:0.5px solid rgba(255,255,255,0.06);
     margin:24px 0 16px 0'></div>
<p style='font-size:13px;font-weight:500;color:#8B8FA8;margin-bottom:10px'>
  Continue With
</p>
""", unsafe_allow_html=True)

n1, n2 = st.columns(2)
with n1:
    if st.button("🧠  Train ML Model",
                 use_container_width=True, key="nav_ml"):
        st.switch_page("pages/4_ML_Studio.py")
with n2:
    if st.button("🤖  Ask AI About This Data",
                 use_container_width=True, key="nav_assistant"):
        st.switch_page("pages/2_Assistant.py")