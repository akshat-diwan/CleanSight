import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Visualize · CleanSight", layout="wide")
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

CHART_COLOR = "#14B8A6"

def style_fig(fig, height=380):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#F0F0F0", height=height,
        margin=dict(t=40, b=10, l=10, r=10),
    )
    return fig

# ── Header ──
st.markdown(f"""
<div style='padding:24px 0 16px 0;border-bottom:0.5px solid rgba(255,255,255,0.06);
     margin-bottom:20px;font-family:Inter,sans-serif'>
  <div style='font-size:12px;font-weight:600;color:#14B8A6;letter-spacing:0.1em;
       text-transform:uppercase;margin-bottom:6px'>Visualize</div>
  <div>
    <div style='font-size:28px;font-weight:700;color:#F0F0F0;letter-spacing:-0.5px;
         line-height:1.2;margin-bottom:4px'>Understand Your Data</div>
    <div style='font-size:13px;color:#8B8FA8'>📄 {st.session_state.filename}</div>
  </div>
</div>
""", unsafe_allow_html=True)

numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
datetime_cols = df.select_dtypes(include="datetime").columns.tolist()

# ================================================================
# PART 1 — BUILD YOUR OWN CHART
# ================================================================

st.markdown("#### 🎛️ Build Your Own Chart")
st.caption("Pick a chart type and the columns you want to explore — CleanSight will explain what it shows.")

CHART_TYPES = ["Histogram", "Bar Chart", "Scatter Plot", "Box Plot", "Pie Chart", "Line Chart", "Correlation Heatmap"]

b1, b2 = st.columns([1, 3])
with b1:
    chart_type = st.selectbox("Chart type", CHART_TYPES, key="chart_type")

fig = None
explanation = None

with b2:
    if chart_type == "Histogram":
        col = st.selectbox("Column (numeric)", numeric_cols, key="hist_col") if numeric_cols else None
    elif chart_type == "Bar Chart":
        col = st.selectbox("Column (categorical)", cat_cols, key="bar_col") if cat_cols else None
    elif chart_type == "Pie Chart":
        col = st.selectbox("Column (categorical)", cat_cols, key="pie_col") if cat_cols else None
    elif chart_type == "Box Plot":
        c1, c2 = st.columns(2)
        with c1:
            col = st.selectbox("Column (numeric)", numeric_cols, key="box_col") if numeric_cols else None
        with c2:
            group_col = st.selectbox("Group by (optional)", ["None"] + cat_cols, key="box_group")
    elif chart_type == "Scatter Plot":
        c1, c2 = st.columns(2)
        with c1:
            x_col = st.selectbox("X axis (numeric)", numeric_cols, key="scatter_x") if numeric_cols else None
        with c2:
            y_options = [c for c in numeric_cols if c != x_col]
            y_col = st.selectbox("Y axis (numeric)", y_options, key="scatter_y") if y_options else None
    elif chart_type == "Line Chart":
        c1, c2 = st.columns(2)
        line_x_options = datetime_cols + numeric_cols
        with c1:
            x_col = st.selectbox("X axis", line_x_options, key="line_x") if line_x_options else None
        with c2:
            y_options = [c for c in numeric_cols if c != x_col]
            y_col = st.selectbox("Y axis (numeric)", y_options, key="line_y") if y_options else None
    elif chart_type == "Correlation Heatmap":
        cols = st.multiselect("Columns (numeric, 2+)", numeric_cols,
                               default=numeric_cols[:min(6, len(numeric_cols))], key="corr_cols")

generate = st.button("✨ Generate Chart", key="generate_chart", use_container_width=False)

if generate:
    try:
        if chart_type == "Histogram" and col:
            fig = px.histogram(df, x=col, nbins=30, marginal="box",
                                title=f"Histogram: {col}", color_discrete_sequence=[CHART_COLOR])
            values = df[col].dropna()
            skew = values.skew()
            shape = "right-skewed (a long tail of high values)" if skew > 0.5 else \
                    "left-skewed (a long tail of low values)" if skew < -0.5 else "roughly symmetric"
            explanation = (f"**{col}** is {shape}, with a mean of {values.mean():.2f} "
                            f"and a median of {values.median():.2f}.")

        elif chart_type == "Bar Chart" and col:
            counts = df[col].astype(str).value_counts().head(15)
            fig = px.bar(x=counts.index.astype(str), y=counts.values,
                         labels={"x": col, "y": "Count"}, title=f"Top Values: {col}",
                         color_discrete_sequence=[CHART_COLOR])
            top_share = counts.iloc[0] / len(df.dropna(subset=[col])) * 100
            explanation = (f"**\"{counts.index[0]}\"** is the most common value in **{col}**, "
                            f"making up {top_share:.1f}% of non-null rows.")

        elif chart_type == "Pie Chart" and col:
            counts = df[col].value_counts().head(10)
            fig = px.pie(values=counts.values, names=counts.index, title=f"Distribution: {col}")
            top_share = counts.iloc[0] / counts.sum() * 100
            explanation = (f"**{col}** has {df[col].nunique()} distinct values; "
                            f"**\"{counts.index[0]}\"** accounts for {top_share:.1f}% of the top-10 shown.")

        elif chart_type == "Box Plot" and col:
            group = None if group_col == "None" else group_col
            fig = px.box(df, y=col, x=group, title=f"Box Plot: {col}" + (f" by {group}" if group else ""),
                         color_discrete_sequence=[CHART_COLOR])
            values = df[col].dropna()
            q1, q3 = values.quantile(0.25), values.quantile(0.75)
            iqr = q3 - q1
            outliers = int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum())
            explanation = (f"**{col}** has a median of {values.median():.2f}, "
                            f"with {outliers} values falling outside the IQR whiskers (outliers).")

        elif chart_type == "Scatter Plot" and x_col and y_col:
            fig = px.scatter(df, x=x_col, y=y_col, title=f"Scatter: {y_col} vs {x_col}",
                              color_discrete_sequence=[CHART_COLOR])
            r = df[[x_col, y_col]].corr().iloc[0, 1]
            strength = "strong" if abs(r) > 0.7 else "moderate" if abs(r) > 0.3 else "weak"
            direction = "positive" if r > 0 else "negative"
            explanation = (f"**{x_col}** and **{y_col}** show a {strength} {direction} relationship "
                            f"(correlation r = {r:.2f}).")

        elif chart_type == "Line Chart" and x_col and y_col:
            plot_df = df[[x_col, y_col]].dropna().sort_values(x_col)
            fig = px.line(plot_df, x=x_col, y=y_col, title=f"{y_col} over {x_col}",
                          color_discrete_sequence=[CHART_COLOR])
            if len(plot_df) > 2:
                slope = np.polyfit(range(len(plot_df)), plot_df[y_col], 1)[0]
                trend = "an upward trend" if slope > 0 else "a downward trend" if slope < 0 else "no clear trend"
                explanation = f"**{y_col}** shows {trend} as **{x_col}** increases."
            else:
                explanation = f"Showing **{y_col}** across **{x_col}**."

        elif chart_type == "Correlation Heatmap" and len(cols) > 1:
            corr = df[cols].corr()
            fig = px.imshow(corr, text_auto=".2f", title="Correlation Heatmap",
                             color_continuous_scale=["#1A1D27", CHART_COLOR])
            abs_corr = corr.abs()
            np.fill_diagonal(abs_corr.values, 0)
            max_pair = abs_corr.stack().idxmax()
            max_val = corr.loc[max_pair]
            explanation = (f"The strongest relationship is between **{max_pair[0]}** and **{max_pair[1]}** "
                            f"(r = {max_val:.2f}).")
        else:
            st.warning("Select all required columns for this chart type first.")
    except Exception as e:
        st.error(f"Couldn't build that chart: {e}")

if fig is not None:
    st.plotly_chart(style_fig(fig), use_container_width=True)
    if explanation:
        st.markdown(f"""
        <div style='background:rgba(20,184,166,0.06);border:0.5px solid rgba(20,184,166,0.18);
             border-radius:10px;padding:12px 16px;font-size:13px;color:#B8BCCC;line-height:1.6'>
          💡 {explanation}
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='border-top:0.5px solid rgba(255,255,255,0.06);margin:32px 0 20px 0'></div>",
            unsafe_allow_html=True)

# ================================================================
# PART 2 — AUTO-GENERATED INSIGHTS (ported from CleanSight standalone app)
# ================================================================

st.markdown("#### 📊 Auto Insights")
st.caption("CleanSight's own picks — a quick visual overview without any setup.")

def likely_id(series, column_name):
    unique = series.nunique(dropna=True)
    rows = len(series)
    name = str(column_name).lower()
    return (
        unique == rows and rows > 0 and not pd.api.types.is_float_dtype(series)
    ) or bool(re.search(r"(^|_)(id|uuid|guid)($|_)", name))

def classify_visual_columns(source):
    roles = {"continuous": [], "low_card": [], "pie": [], "bar": [], "ids": []}
    for column in source.columns:
        series = source[column]
        unique = series.nunique(dropna=True)
        if not unique:
            continue
        if likely_id(series, column):
            roles["ids"].append(column)
        elif pd.api.types.is_numeric_dtype(series):
            (roles["low_card"] if unique < 10 else roles["continuous"]).append(column)
        elif unique <= 8:
            roles["pie"].append(column)
        elif unique <= 30:
            roles["bar"].append(column)
    return roles

def highest_variance_columns(source, columns, limit):
    scored = []
    for column in columns:
        values = source[column].dropna()
        if not values.empty:
            mean = abs(values.mean())
            score = values.std() / mean if mean > 1e-9 else values.std()
            scored.append((score, column))
    return [column for _, column in sorted(scored, reverse=True)[:limit]]

roles = classify_visual_columns(df)

if roles["ids"]:
    st.caption("Excluded from auto charts as likely identifiers: " + ", ".join(map(str, roles["ids"])))

auto_col1, auto_col2 = st.columns(2)
slot = 0

def next_slot():
    global slot
    col = auto_col1 if slot % 2 == 0 else auto_col2
    slot += 1
    return col

for column in highest_variance_columns(df, roles["continuous"], 3):
    with next_slot():
        figure = px.histogram(df, x=column, nbins=30, marginal="box",
                               title=f"Histogram: {column}", color_discrete_sequence=[CHART_COLOR])
        st.plotly_chart(style_fig(figure, 320), use_container_width=True)
        values = df[column].dropna()
        skew = values.skew()
        shape = "right-skewed" if skew > 0.5 else "left-skewed" if skew < -0.5 else "roughly symmetric"
        st.caption(f"💡 {column} is {shape}, mean {values.mean():.2f}.")

for column in roles["pie"][:2]:
    with next_slot():
        counts = df[column].value_counts().head(10)
        figure = px.pie(values=counts.values, names=counts.index, title=f"Distribution: {column}")
        st.plotly_chart(style_fig(figure, 320), use_container_width=True)
        st.caption(f"💡 \"{counts.index[0]}\" is the most common value ({counts.iloc[0]/counts.sum()*100:.1f}%).")

continuous = roles["continuous"]
if len(continuous) > 1:
    with next_slot():
        figure = px.imshow(df[continuous].corr(), text_auto=".2f", title="Correlation Heatmap",
                            color_continuous_scale=["#1A1D27", CHART_COLOR])
        st.plotly_chart(style_fig(figure, 320), use_container_width=True)
        st.caption("💡 Shows how strongly each numeric column moves with the others.")

    correlations = df[continuous].corr().abs()
    pairs = []
    for i, column_a in enumerate(continuous):
        for column_b in continuous[i + 1:]:
            value = correlations.loc[column_a, column_b]
            if pd.notna(value):
                pairs.append((value, column_a, column_b))

    for score, x_column, y_column in sorted(pairs, reverse=True)[:3]:
        with next_slot():
            figure = px.scatter(df, x=x_column, y=y_column, title=f"Scatter: {y_column} vs {x_column}",
                                 color_discrete_sequence=[CHART_COLOR])
            st.plotly_chart(style_fig(figure, 320), use_container_width=True)
            st.caption(f"💡 Correlation r = {score:.2f} between {x_column} and {y_column}.")

bar_candidates = list(dict.fromkeys(roles["bar"] + roles["low_card"] + roles["pie"]))[:2]
for column in bar_candidates:
    with next_slot():
        counts = df[column].astype(str).value_counts().head(10)
        figure = px.bar(x=counts.index.astype(str), y=counts.values,
                         labels={"x": column, "y": "Count"}, title=f"Top Values: {column}",
                         color_discrete_sequence=[CHART_COLOR])
        st.plotly_chart(style_fig(figure, 320), use_container_width=True)
        st.caption(f"💡 \"{counts.index[0]}\" appears most often in {column}.")

if slot == 0:
    st.info("Not enough distinct column types in this dataset to generate automatic charts.")

# ── Navigation ──
st.markdown("""
<div style='border-top:0.5px solid rgba(255,255,255,0.06);margin:24px 0 16px 0'></div>
<p style='font-size:13px;font-weight:500;color:#8B8FA8;margin-bottom:10px'>
  Continue With
</p>
""", unsafe_allow_html=True)

n1, n2 = st.columns(2)
with n1:
    if st.button("📄  Generate Report", use_container_width=True, key="nav_report"):
        st.switch_page("pages/5_Reports.py")
with n2:
    if st.button("🤖  Ask AI About This Data", use_container_width=True, key="nav_assistant"):
        st.switch_page("pages/2_Assistant.py")