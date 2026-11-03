"""
CleanSight question answering.

Questions are turned into a small, safe "query plan" (a dict) and executed with pandas.
Plans come from (1) deterministic rules and (2) an LLM planner. The LLM never writes or runs code;
it only fills in the plan, and the numbers always come from the real data.
"""
import json
import re

import numpy as np
import pandas as pd

OPS = {
    "count_rows", "count_columns", "count", "percent", "mean", "median", "min", "max", "sum", "std",
    "unique", "missing", "duplicates", "correlation", "top_correlations", "value_counts",
    "describe", "columns", "none",
}

COLUMN_ALIASES = {
    "cholesterol": ["totchol"], "cholestrol": ["totchol"], "total cholesterol": ["totchol"],
    "blood pressure": ["sysbp", "diabp"], "systolic pressure": ["sysbp"], "diastolic pressure": ["diabp"],
    "heart rate": ["heartrate"], "blood sugar": ["glucose"], "cigarettes": ["cigsperday"],
    "hypertension": ["prevalenthyp"], "stroke": ["prevalentstroke"],
}

VALUE_ALIASES = {}
for _w in ("male", "males", "man", "men", "boy", "boys"):
    VALUE_ALIASES[_w] = {"m", "male"}
for _w in ("female", "females", "woman", "women", "girl", "girls"):
    VALUE_ALIASES[_w] = {"f", "female"}

STAT_WORDS = [
    ("mean", r"\baverage\b|\bmean\b|\bavg\b"),
    ("median", r"\bmedian\b"),
    ("max", r"\bhighest\b|\bmaximum\b|\bmax\b|\blargest\b|\bbiggest\b|\boldest\b"),
    ("min", r"\blowest\b|\bminimum\b|\bmin\b|\bsmallest\b|\byoungest\b"),
    ("sum", r"\btotal\b|\bsum of\b"),
    ("std", r"standard deviation|\bstd\b"),
]
STAT_LABEL = {"mean": "average", "median": "median", "max": "maximum", "min": "minimum",
              "sum": "total", "std": "standard deviation"}


def normalize(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _grams(question, max_n=4):
    tokens = re.findall(r"[a-z0-9]+", question.lower())
    grams = set()
    for n in range(1, max_n + 1):
        for i in range(len(tokens) - n + 1):
            grams.add("".join(tokens[i:i + n]))
    return tokens, grams


def get_column_matches(question, columns):
    """Columns the question seems to be about (exact/aliased first, then fuzzy)."""
    qn = normalize(question)
    exact = []
    for alias, targets in COLUMN_ALIASES.items():
        if normalize(alias) in qn:
            for t in targets:
                exact += [c for c in columns if normalize(c) == t]
    if exact:
        return list(dict.fromkeys(exact))

    words = re.findall(r"[a-zA-Z]+", question.lower())
    scores = []
    for col in columns:
        nc = normalize(col)
        score = 0
        if nc and nc in qn:
            score = len(nc) * 10
        for w in words:
            nw = normalize(w)
            if len(nw) < 3:
                continue
            if nw in nc:
                score = max(score, len(nw) * 4)
            if len(nw) >= 4:
                for i in range(len(nw) - 3):
                    if nw[i:i + 4] in nc:
                        score = max(score, 8)
        if score:
            scores.append((score, col))
    scores.sort(reverse=True, key=lambda t: t[0])
    return [c for _, c in scores]


def get_threshold(question):
    filler = r"(?:\W+(?:the|a|an|age|of|value|values|level|levels|is|are|than))*\W*"
    num = r"(-?\d+\.?\d*)"
    patterns = [
        (r"(?:greater than or equal to|at least|>=)" + filler + num, ">="),
        (r"(?:less than or equal to|at most|<=)" + filler + num, "<="),
        (r"(?:above|greater than|more than|over|higher than|older than|exceeds?)" + filler + num, ">"),
        (r"(?:below|less than|under|lower than|fewer than|younger than)" + filler + num, "<"),
        (r"(?:equal to|exactly|==)" + filler + num, "=="),
    ]
    for pattern, op in patterns:
        m = re.search(pattern, question.lower())
        if m:
            return op, float(m.group(1))
    return None, None


def _is_text_like(s):
    """Text/categorical column - works for pandas 2 (object) and pandas 3 (str) dtypes."""
    return (pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s)
            or isinstance(s.dtype, pd.CategoricalDtype) or pd.api.types.is_bool_dtype(s))


def value_filters(question, df, max_unique=30):
    """Filters implied by category values mentioned in the question ('males', 'Android', ...)."""
    tokens, grams = _grams(question)
    token_set = set(tokens)
    alias_sets = [VALUE_ALIASES[t] for t in tokens if t in VALUE_ALIASES]
    found = {}
    for col in df.columns:
        s = df[col]
        if not _is_text_like(s):
            continue
        n = s.nunique(dropna=True)
        if n == 0 or n > max_unique:
            continue
        for v in s.dropna().astype(str).unique():
            nv = normalize(v)
            if not nv:
                continue
            hit = False
            if len(nv) >= 2:
                hit = (nv in grams or nv + "s" in grams
                       or (nv.endswith("s") and nv[:-1] in grams))
            if not hit and any(nv in a for a in alias_sets):
                hit = True
            if hit:
                found.setdefault(col, []).append(v)

    if token_set & {"smoker", "smokers"}:
        for col in df.columns:
            if "smok" in str(col).lower() and _is_text_like(df[col]):
                yes = [v for v in df[col].dropna().astype(str).unique() if normalize(v) in {"yes", "y", "true", "1"}]
                if yes:
                    found.setdefault(col, yes)

    return [{"column": c, "operator": "==" if len(v) == 1 else "in",
             "value": v[0] if len(v) == 1 else v} for c, v in found.items()]


# ----------------------------------------------------------------
# Rule-based planner
# ----------------------------------------------------------------

def _stat_op(low):
    for op, pattern in STAT_WORDS:
        if re.search(pattern, low):
            return op
    return None


def _id_like(s):
    return s.nunique(dropna=True) == len(s) and str(s.dtype).startswith("int")


def local_plan(question, df):
    """Plan for questions the rules can answer with confidence, else None."""
    low = question.lower().strip()
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not _id_like(df[c])]
    filters = value_filters(question, df)
    filter_cols = {f["column"] for f in filters}
    op_t, thr = get_threshold(question)
    matches = get_column_matches(question, list(df.columns))
    num_matches = [c for c in matches if c in numeric_cols and c not in filter_cols]
    count_intent = bool(re.search(r"\bhow many\b|\bnumber of\b|\bcount\b|\bhow much\b", low))
    percent_intent = bool(re.search(r"percent|percentage|proportion|\bshare\b|\bratio\b|\bfraction\b|%", low))

    # dataset-level questions
    if re.search(r"\bhow many (columns|features|variables|fields)\b|\bnumber of (columns|features|variables)\b", low):
        return {"op": "count_columns"}
    if "duplicate" in low:
        return {"op": "duplicates"}
    if re.search(r"\bmissing\b|\bnulls?\b|\bnan\b|\bempty\b", low):
        col = next((c for c in matches), None)
        return {"op": "missing", "column": col}
    if re.search(r"column names|list (all )?(the )?(columns|features|variables)|what (columns|features|variables)|which (columns|features|variables)", low):
        return {"op": "columns"}
    if not filters and op_t is None and re.search(
            r"\b(how many|number of|total|count)\b[^?]*\b(rows|records|entries|observations|samples)\b", low):
        return {"op": "count_rows"}

    # correlations
    if "correlat" in low or "relationship between" in low:
        if len(num_matches) >= 2:
            return {"op": "correlation", "column": num_matches[0], "column2": num_matches[1]}
        return {"op": "top_correlations"}

    # counts / percentages with value or numeric filters
    all_filters = list(filters)
    if op_t is not None and num_matches:
        all_filters.append({"column": num_matches[0], "operator": op_t, "value": thr})
    if all_filters and (count_intent or percent_intent):
        return {"op": "percent" if percent_intent and not count_intent else "count", "filters": all_filters,
                "show_percent": True}

    # numeric statistics (optionally filtered)
    stat = _stat_op(low)
    if stat and num_matches:
        return {"op": stat, "column": num_matches[0], "filters": all_filters}

    # distributions
    cat_matches = [c for c in matches if _is_text_like(df[c]) or df[c].nunique(dropna=True) <= 12]
    if cat_matches and (re.search(r"distribution|breakdown|\bhow many\b|\bcount\b", low)):
        return {"op": "value_counts", "column": cat_matches[0], "filters": all_filters}

    if re.search(r"\bunique\b|\bdistinct\b", low) and matches:
        return {"op": "unique", "column": matches[0]}
    return None


# ----------------------------------------------------------------
# LLM planner helpers
# ----------------------------------------------------------------

def looks_computational(question, has_previous=False):
    low = question.lower()
    words = re.findall(r"[a-z0-9]+", low)
    if re.search(r"\b(how many|how much|count|number of|percent|percentage|proportion|average|mean|median|"
                 r"max|min|maximum|minimum|highest|lowest|total|sum|most|least|top|correlat|distribution|"
                 r"unique|distinct|missing|duplicate|above|below|greater|less than|more than|fewer|each|per|"
                 r"how old|oldest|youngest)\b", low):
        return True
    return has_previous and len(words) <= 6


def planner_prompt(df, question, previous_question=None):
    lines = []
    for c in list(df.columns)[:60]:
        s = df[c]
        n = s.nunique(dropna=True)
        if pd.api.types.is_numeric_dtype(s):
            if n <= 6:
                info = "numeric, values: " + ", ".join(str(v) for v in sorted(s.dropna().unique().tolist())[:6])
            else:
                info = f"numeric, range {s.min():.4g} to {s.max():.4g}"
        else:
            vals = s.dropna().astype(str).value_counts().head(12).index.tolist()
            info = f"text, {n} unique" + (", values: " + ", ".join(vals) if n <= 12 else ", e.g. " + ", ".join(vals[:5]))
        lines.append(f"- {c}: {info}")
    prev = f"\nPrevious question (use it to resolve follow-ups like 'and females?'): {previous_question}" if previous_question else ""
    return f"""You translate a question about a dataset into a JSON query plan. Reply with ONE JSON object and nothing else.

Columns:
{chr(10).join(lines)}

JSON schema:
{{"op": "<count_rows|count_columns|count|percent|mean|median|min|max|sum|std|unique|missing|duplicates|correlation|top_correlations|value_counts|describe|columns|none>",
 "column": "<column name or null>", "column2": "<second column or null>",
 "filters": [{{"column": "<name>", "operator": "<== | != | > | >= | < | <= | in>", "value": "<string, number or list>"}}],
 "group_by": "<column or null>", "top": "<integer or null>"}}

Rules:
- Use exact column names and exact category values from the list above (for example "males" -> the matching value of the sex column).
- "how many ..." -> op "count" with filters. "what percent / share ..." -> op "percent" with filters.
- average / median / min / max / sum of a column (optionally filtered or grouped) -> that op with "column".
- Use op "none" if the question needs advice, explanation, or is not a single calculation on this data.{prev}

Question: {question}"""


def parse_plan(text, df):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        plan = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(plan, dict) or plan.get("op") not in OPS:
        return None
    if not isinstance(plan.get("filters"), list):
        plan["filters"] = []
    return plan


# ----------------------------------------------------------------
# Executor
# ----------------------------------------------------------------

def _resolve_col(df, name):
    if name in (None, "", "null", "None"):
        return None
    if name in df.columns:
        return name
    n = normalize(name)
    for c in df.columns:
        if normalize(c) == n:
            return c
    return None


def _apply_filters(df, filters):
    """Returns (mask, description) or (None, None) when a filter can't be applied."""
    mask = pd.Series(True, index=df.index)
    parts = []
    for f in filters or []:
        col = _resolve_col(df, f.get("column"))
        op = f.get("operator", "==")
        val = f.get("value")
        if col is None or op not in {"==", "!=", ">", ">=", "<", "<=", "in"}:
            return None, None
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            try:
                vals = [float(x) for x in (val if isinstance(val, list) else [val])]
            except (TypeError, ValueError):
                return None, None
            v = vals[0]
            m = {"==": s == v, "!=": s != v, ">": s > v, ">=": s >= v, "<": s < v, "<=": s <= v,
                 "in": s.isin(vals)}[op]
            shown = ", ".join(f"{x:g}" for x in vals)
        else:
            ss = s.astype(str).str.strip().str.lower()
            vals = [str(x).strip().lower() for x in (val if isinstance(val, list) else [val])]
            if op in ("==", "in"):
                m = ss.isin(vals) & s.notna()
            elif op == "!=":
                m = ~ss.isin(vals) & s.notna()
            else:
                return None, None
            shown = ", ".join(str(x) for x in (val if isinstance(val, list) else [val]))
        mask &= m.fillna(False)
        parts.append(f"{col} {'in' if op == 'in' else op} {shown}" if op == "in" else f"{col} {op} {shown}")
    return mask, " and ".join(parts)


def _where(desc):
    return f" where **{desc}**" if desc else ""


def _bullets(items):
    return "\n".join(f"- **{k}**: {v}" for k, v in items)


def execute_plan(df, plan):
    """Run a plan and return a Markdown answer, or None if it can't be answered."""
    try:
        return _execute(df, plan)
    except Exception:
        return None


def _execute(df, plan):
    op = plan.get("op")
    if op in (None, "none"):
        return None

    mask, desc = _apply_filters(df, plan.get("filters"))
    if mask is None:
        return None
    sub = df[mask]
    col = _resolve_col(df, plan.get("column"))
    col2 = _resolve_col(df, plan.get("column2"))
    group = _resolve_col(df, plan.get("group_by"))
    top = plan.get("top") if isinstance(plan.get("top"), int) and plan.get("top") > 0 else 15

    if op == "count_rows":
        return f"The dataset has **{len(df):,}** rows."
    if op == "count_columns":
        return f"The dataset has **{df.shape[1]}** columns."
    if op == "columns":
        names = ", ".join(f"`{c}`" for c in df.columns[:80])
        return f"The dataset has **{df.shape[1]}** columns: {names}."
    if op == "duplicates":
        d = int(df.duplicated().sum())
        return f"There are **{d:,}** duplicate rows ({d / max(len(df), 1):.1%} of all rows)."

    if op == "missing":
        if col:
            m = int(df[col].isnull().sum())
            return f"**{col}** has **{m:,}** missing values ({m / max(len(df), 1):.1%} of rows)."
        miss = df.isnull().sum()
        miss = miss[miss > 0].sort_values(ascending=False)
        if miss.empty:
            return "There are **no** missing values in the dataset."
        items = [(c, f"{int(v):,} ({v / len(df):.1%})") for c, v in miss.head(10).items()]
        return f"**{int(miss.sum()):,}** missing values across **{len(miss)}** columns:\n" + _bullets(items)

    if op in ("count", "percent"):
        if not plan.get("filters") and col:
            n = int(df[col].notna().sum())
            return f"**{col}** has **{n:,}** non-empty values."
        if not plan.get("filters"):
            return None
        n, total = int(mask.sum()), len(df)
        if group:
            counts = sub[group].dropna().astype(str).value_counts().head(top)
            items = [(k, f"{int(v):,} ({v / max(n, 1):.1%})") for k, v in counts.items()]
            return f"Rows{_where(desc)}, grouped by **{group}** ({n:,} rows):\n" + _bullets(items)
        if op == "percent":
            return (f"**{n / max(total, 1):.1%}** of the {total:,} rows match **{desc}** "
                    f"({n:,} rows).")
        return (f"There are **{n:,}** rows{_where(desc)} "
                f"— **{n / max(total, 1):.1%}** of the {total:,} rows in the dataset.")

    if op in ("mean", "median", "min", "max", "sum", "std"):
        if col is None or not pd.api.types.is_numeric_dtype(df[col]):
            return None
        label = STAT_LABEL[op]
        if group:
            agg = sub.groupby(group)[col].agg(op).dropna().sort_values(ascending=False).head(top)
            items = [(str(k), f"{v:,.2f}") for k, v in agg.items()]
            return f"The **{label}** of **{col}** by **{group}**{_where(desc)}:\n" + _bullets(items)
        values = sub[col].dropna()
        if values.empty:
            return None
        v = getattr(values, op)()
        return f"The **{label}** of **{col}**{_where(desc)} is **{v:,.2f}** (based on {len(values):,} rows)."

    if op == "unique":
        if col is None:
            return None
        s = sub[col].dropna()
        n = int(s.nunique())
        text = f"**{col}** has **{n:,}** unique values"
        if n <= 15:
            text += ": " + ", ".join(f"`{v}`" for v in s.astype(str).unique())
        return text + "."

    if op == "correlation":
        if col is None or col2 is None:
            return None
        valid = df[[col, col2]].dropna()
        if len(valid) < 3 or not all(pd.api.types.is_numeric_dtype(df[c]) for c in (col, col2)):
            return None
        r = float(valid[col].corr(valid[col2]))
        strength = "strong" if abs(r) > 0.7 else "moderate" if abs(r) > 0.3 else "weak"
        return (f"The Pearson correlation between **{col}** and **{col2}** is **{r:.3f}** "
                f"({strength}, {'positive' if r > 0 else 'negative'}), from {len(valid):,} complete rows. "
                f"This shows association, not causation.")

    if op == "top_correlations":
        cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
                and not _id_like(df[c]) and df[c].nunique(dropna=True) > 2]
        if len(cols) < 2:
            return "There aren't enough numeric columns to compute correlations."
        corr = df[cols].corr()
        pairs = []
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                r = corr.loc[a, b]
                if pd.notna(r):
                    pairs.append((abs(r), r, a, b))
        pairs.sort(reverse=True)
        items = [(f"{a} ↔ {b}", f"r = {r:.2f}") for _, r, a, b in pairs[:5]]
        return "Strongest correlations between numeric columns:\n" + _bullets(items)

    if op == "value_counts":
        if col is None:
            return None
        counts = sub[col].dropna().astype(str).value_counts().head(top)
        total = max(int(sub[col].notna().sum()), 1)
        items = [(k, f"{int(v):,} ({v / total:.1%})") for k, v in counts.items()]
        return f"Distribution of **{col}**{_where(desc)}:\n" + _bullets(items)

    if op == "describe":
        if col is None:
            return None
        s = sub[col].dropna()
        if pd.api.types.is_numeric_dtype(df[col]):
            items = [(k, f"{v:,.2f}") for k, v in s.describe().items()]
            return f"Summary of **{col}**:\n" + _bullets(items)
        counts = s.astype(str).value_counts().head(5)
        items = [(k, f"{int(v):,}") for k, v in counts.items()]
        return f"**{col}** has {s.nunique():,} unique values. Most common:\n" + _bullets(items)
    return None