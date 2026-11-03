"""
Chart specs, one-line explanations and static (matplotlib) rendering for the PDF report.

A chart is described by a small "spec" dict so it can be saved in session state and re-drawn later
from the *current* (cleaned) data:
  {"type": "Histogram", "col": c}            {"type": "Bar Chart", "col": c}
  {"type": "Pie Chart", "col": c}            {"type": "Box Plot", "col": c, "group": g_or_None}
  {"type": "Scatter Plot", "x": a, "y": b}   {"type": "Line Chart", "x": a, "y": b}
  {"type": "Correlation Heatmap", "cols": [..]}
"""
import re

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import seaborn as sns
except ImportError:  # seaborn is optional; heatmaps fall back to imshow
    sns = None

TEAL = "#14B8A6"
PALETTE = ["#14B8A6", "#7F77DD", "#EF9F27", "#E24B4A", "#5DCAA5", "#378ADD", "#D4537E", "#888780", "#97C459"]
STYLE = {
    "figure.facecolor": "white", "axes.facecolor": "white", "axes.edgecolor": "#C9CCD6",
    "axes.labelcolor": "#444A5A", "xtick.color": "#444A5A", "ytick.color": "#444A5A",
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 8,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.grid": True,
    "grid.color": "#EEF0F4", "grid.linewidth": 0.8, "axes.axisbelow": True,
}


# ----------------------------------------------------------------
# Column roles (ported from the original CleanSight app)
# ----------------------------------------------------------------

def is_text_col(s):
    return (pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s)
            or isinstance(s.dtype, pd.CategoricalDtype)) and not pd.api.types.is_numeric_dtype(s)


def likely_id(series, column_name):
    unique = series.nunique(dropna=True)
    rows = len(series)
    name = str(column_name).lower()
    return (unique == rows and rows > 0 and not pd.api.types.is_float_dtype(series)) \
        or bool(re.search(r"(^|_)(id|uuid|guid)($|_)", name))


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
        elif is_text_col(series):
            if unique <= 8:
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


# ----------------------------------------------------------------
# Specs
# ----------------------------------------------------------------

def default_chart_specs(df):
    """The automatic set (same selection logic as the Visualize page's Auto Insights)."""
    roles = classify_visual_columns(df)
    specs = []
    for c in highest_variance_columns(df, roles["continuous"], 3):
        specs.append({"type": "Histogram", "col": c})
    for c in roles["pie"][:2]:
        specs.append({"type": "Pie Chart", "col": c})
    continuous = roles["continuous"]
    if len(continuous) > 1:
        top = highest_variance_columns(df, continuous, 12)
        specs.append({"type": "Correlation Heatmap", "cols": top})
        corr = df[continuous].corr().abs()
        pairs = []
        for i, a in enumerate(continuous):
            for b in continuous[i + 1:]:
                v = corr.loc[a, b]
                if pd.notna(v):
                    pairs.append((v, a, b))
        for _, a, b in sorted(pairs, reverse=True)[:3]:
            specs.append({"type": "Scatter Plot", "x": a, "y": b})
    for c in list(dict.fromkeys(roles["bar"] + roles["low_card"] + roles["pie"]))[:2]:
        specs.append({"type": "Bar Chart", "col": c})
    return specs


def spec_columns(spec):
    t = spec["type"]
    if t in ("Histogram", "Bar Chart", "Pie Chart"):
        return [spec["col"]]
    if t == "Box Plot":
        return [spec["col"]] + ([spec["group"]] if spec.get("group") else [])
    if t in ("Scatter Plot", "Line Chart"):
        return [spec["x"], spec["y"]]
    if t == "Correlation Heatmap":
        return list(spec["cols"])
    return []


def spec_key(spec):
    return tuple((k, tuple(v) if isinstance(v, list) else v) for k, v in sorted(spec.items()))


def spec_title(spec):
    t = spec["type"]
    if t == "Histogram":
        return f"Histogram: {spec['col']}"
    if t == "Bar Chart":
        return f"Top values: {spec['col']}"
    if t == "Pie Chart":
        return f"Distribution: {spec['col']}"
    if t == "Box Plot":
        return f"Box plot: {spec['col']}" + (f" by {spec['group']}" if spec.get("group") else "")
    if t == "Scatter Plot":
        return f"Scatter: {spec['y']} vs {spec['x']}"
    if t == "Line Chart":
        return f"{spec['y']} over {spec['x']}"
    return "Correlation heatmap"


def spec_is_valid(df, spec):
    """Columns still exist (data may have been replaced) and have the right kind."""
    try:
        cols = spec_columns(spec)
        if not cols or any(c not in df.columns for c in cols):
            return False
        t = spec["type"]
        num = lambda c: pd.api.types.is_numeric_dtype(df[c])
        if t in ("Histogram",):
            return num(spec["col"])
        if t == "Box Plot":
            return num(spec["col"])
        if t == "Scatter Plot":
            return num(spec["x"]) and num(spec["y"])
        if t == "Line Chart":
            return num(spec["y"])
        if t == "Correlation Heatmap":
            return len(cols) >= 2 and all(num(c) for c in cols)
        return True
    except Exception:
        return False


# ----------------------------------------------------------------
# One-line explanations (plain text, safe for the PDF)
# ----------------------------------------------------------------

def describe_chart(df, spec):
    t = spec["type"]
    if t == "Histogram":
        v = df[spec["col"]].dropna()
        skew = v.skew() if len(v) > 2 else 0
        shape = ("right-skewed, with a tail of high values" if skew > 0.5 else
                 "left-skewed, with a tail of low values" if skew < -0.5 else "roughly symmetric")
        return f"{spec['col']} is {shape}; its mean is {v.mean():,.2f} and its median is {v.median():,.2f}."
    if t == "Bar Chart":
        counts = df[spec["col"]].dropna().astype(str).value_counts()
        share = counts.iloc[0] / counts.sum() * 100
        return f"\"{counts.index[0]}\" is the most common value in {spec['col']}, at {share:.1f}% of non-empty rows."
    if t == "Pie Chart":
        counts = df[spec["col"]].dropna().astype(str).value_counts()
        share = counts.iloc[0] / counts.sum() * 100
        return (f"{spec['col']} has {df[spec['col']].nunique()} distinct values; "
                f"\"{counts.index[0]}\" is the largest at {share:.1f}%.")
    if t == "Box Plot":
        v = df[spec["col"]].dropna()
        q1, q3 = v.quantile(0.25), v.quantile(0.75)
        iqr = q3 - q1
        out = int(((v < q1 - 1.5 * iqr) | (v > q3 + 1.5 * iqr)).sum())
        by = f" across {spec['group']} groups" if spec.get("group") else ""
        return f"{spec['col']}{by} has a median of {v.median():,.2f} and {out:,} values outside the IQR whiskers (outliers)."
    if t == "Scatter Plot":
        r = df[[spec["x"], spec["y"]]].corr().iloc[0, 1]
        strength = "strong" if abs(r) > 0.7 else "moderate" if abs(r) > 0.3 else "weak"
        direction = "positive" if r > 0 else "negative"
        return f"{spec['x']} and {spec['y']} show a {strength} {direction} relationship (correlation r = {r:.2f})."
    if t == "Line Chart":
        d = df[[spec["x"], spec["y"]]].dropna().sort_values(spec["x"])
        if len(d) > 2:
            slope = np.polyfit(np.arange(len(d)), d[spec["y"]].to_numpy(dtype=float), 1)[0]
            trend = "an upward trend" if slope > 0 else "a downward trend" if slope < 0 else "no clear trend"
            return f"{spec['y']} shows {trend} as {spec['x']} increases."
        return f"Shows {spec['y']} across {spec['x']}."
    if t == "Correlation Heatmap":
        cols = [c for c in spec["cols"] if c in df.columns]
        corr_full = df[cols].corr()
        arr = np.nan_to_num(corr_full.abs().to_numpy(copy=True))
        np.fill_diagonal(arr, 0)
        i, j = np.unravel_index(np.argmax(arr), arr.shape)
        a, b, r = cols[i], cols[j], corr_full.iloc[i, j]
        return f"The strongest relationship is between {a} and {b} (r = {r:.2f}); deeper colours mean stronger links."
    return ""


# ----------------------------------------------------------------
# Static rendering
# ----------------------------------------------------------------

def _short(label, n=22):
    label = str(label)
    return label if len(label) <= n else label[: n - 1] + "…"


def render_chart(df, spec):
    """Draw a spec with matplotlib and return the Figure (caller saves/closes it)."""
    t = spec["type"]
    with plt.rc_context(STYLE):
        if t == "Correlation Heatmap":
            cols = [c for c in spec["cols"] if c in df.columns][:14]
            fig, ax = plt.subplots(figsize=(6.6, 5.2))
            corr = df[cols].corr()
            ax.grid(False)
            if sns is not None:
                sns.heatmap(corr, ax=ax, cmap="vlag", center=0, vmin=-1, vmax=1,
                            annot=len(cols) <= 10, fmt=".2f", annot_kws={"size": 7},
                            linewidths=0.4, cbar_kws={"shrink": 0.8})
            else:
                im = ax.imshow(corr.to_numpy(), cmap="coolwarm", vmin=-1, vmax=1)
                ax.set_xticks(range(len(cols)))
                ax.set_yticks(range(len(cols)))
                ax.set_xticklabels(cols)
                ax.set_yticklabels(cols)
                fig.colorbar(im, ax=ax, shrink=0.8)
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
            plt.setp(ax.get_yticklabels(), rotation=0)

        elif t == "Histogram":
            fig, ax = plt.subplots(figsize=(6.6, 3.5))
            v = df[spec["col"]].dropna()
            bins = 1 if v.nunique() < 2 else int(min(30, max(5, v.nunique())))
            ax.hist(v, bins=bins, color=TEAL, edgecolor="white", linewidth=0.4)
            ax.axvline(v.median(), color="#E24B4A", linestyle="--", linewidth=1, label=f"median {v.median():,.2f}")
            ax.set_xlabel(spec["col"])
            ax.set_ylabel("Count")
            ax.legend(frameon=False, fontsize=7)

        elif t == "Bar Chart":
            fig, ax = plt.subplots(figsize=(6.6, 3.5))
            counts = df[spec["col"]].dropna().astype(str).value_counts().head(10)
            labels = [_short(k) for k in counts.index][::-1]
            ax.barh(labels, counts.to_numpy()[::-1], color=TEAL)
            ax.set_xlabel("Count")
            ax.grid(axis="y", visible=False)

        elif t == "Pie Chart":
            fig, ax = plt.subplots(figsize=(6.6, 3.5))
            counts = df[spec["col"]].dropna().astype(str).value_counts()
            if len(counts) > 8:
                other = counts.iloc[8:].sum()
                counts = pd.concat([counts.iloc[:8], pd.Series({"Other": other})])
            ax.grid(False)
            wedges, _, autotexts = ax.pie(
                counts.to_numpy(), colors=PALETTE[:len(counts)], startangle=90, counterclock=False,
                autopct=lambda p: f"{p:.0f}%" if p >= 4 else "", pctdistance=0.78,
                wedgeprops={"edgecolor": "white", "linewidth": 1})
            for at in autotexts:
                at.set_color("white")
                at.set_fontsize(7)
            ax.legend(wedges, [_short(k) for k in counts.index], loc="center left",
                      bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=7)
            ax.axis("equal")

        elif t == "Box Plot":
            fig, ax = plt.subplots(figsize=(6.6, 3.5))
            work = df[[spec["col"]] + ([spec["group"]] if spec.get("group") else [])].dropna()
            if len(work) > 100000:
                work = work.sample(100000, random_state=0)
            if spec.get("group"):
                groups = work[spec["group"]].astype(str).value_counts().head(8).index.tolist()
                data = [work.loc[work[spec["group"]].astype(str) == g, spec["col"]] for g in groups]
                labels = [_short(g, 14) for g in groups]
            else:
                data, labels = [work[spec["col"]]], [spec["col"]]
            bp = ax.boxplot(data, patch_artist=True, widths=0.5 if len(data) > 1 else 0.3,
                            flierprops={"marker": "o", "markersize": 2.5, "markerfacecolor": "#E24B4A",
                                        "markeredgecolor": "none", "alpha": 0.5},
                            medianprops={"color": "#1F2937", "linewidth": 1.3})
            for patch in bp["boxes"]:
                patch.set_facecolor(TEAL)
                patch.set_alpha(0.75)
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels, rotation=20 if len(labels) > 3 else 0, ha="right" if len(labels) > 3 else "center")
            ax.set_ylabel(spec["col"])
            ax.grid(axis="x", visible=False)

        elif t == "Scatter Plot":
            fig, ax = plt.subplots(figsize=(6.6, 3.5))
            d = df[[spec["x"], spec["y"]]].dropna()
            if len(d) > 3000:
                d = d.sample(3000, random_state=0)
            ax.scatter(d[spec["x"]], d[spec["y"]], s=8, alpha=0.45, color=TEAL, edgecolors="none")
            if len(d) > 2 and d[spec["x"]].std() > 0:
                m, b = np.polyfit(d[spec["x"]].to_numpy(dtype=float), d[spec["y"]].to_numpy(dtype=float), 1)
                xs = np.array([d[spec["x"]].min(), d[spec["x"]].max()], dtype=float)
                ax.plot(xs, m * xs + b, color="#E24B4A", linewidth=1.2)
            ax.set_xlabel(spec["x"])
            ax.set_ylabel(spec["y"])

        elif t == "Line Chart":
            fig, ax = plt.subplots(figsize=(6.6, 3.5))
            d = df[[spec["x"], spec["y"]]].dropna().sort_values(spec["x"])
            step = max(1, len(d) // 2000)
            d = d.iloc[::step]
            ax.plot(d[spec["x"]], d[spec["y"]], color=TEAL, linewidth=1.4)
            ax.set_xlabel(spec["x"])
            ax.set_ylabel(spec["y"])
        else:
            raise ValueError(f"Unknown chart type: {t}")

        ax.set_title(spec_title(spec), loc="left")
        fig.tight_layout()
    return fig