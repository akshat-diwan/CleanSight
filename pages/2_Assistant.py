import os
import sys

import pandas as pd
import streamlit as st
from groq import Groq

# make the project root importable from pages/ (data_qa.py lives next to Home.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data_qa as dq

st.set_page_config(page_title="AI Assistant · CleanSight", layout="wide")
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
/* Hide default streamlit top header */
[data-testid="stHeader"] { display: none; }

/* Sticky top bar */
.top-bar {
    position: fixed;
    top: 0;
    left: 260px;
    right: 0;
    z-index: 999;
    padding: 12px 3rem 10px 3rem;
    border-bottom: 0.5px solid rgba(128,128,128,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    background: rgba(14,17,23,0.92);
}

/* Push content down so it doesn't hide behind fixed bar */
.main-content {
    margin-top: 90px;
}

/* User bubble — right aligned */
.chat-user {
    display: flex;
    justify-content: flex-end;
    margin: 10px 0;
}
.chat-user .bubble {
    background: rgba(20,184,166,0.13);
    border: 0.5px solid rgba(20,184,166,0.25);
    border-radius: 16px 16px 4px 16px;
    padding: 10px 15px;
    max-width: 68%;
    font-size: 14px;
    line-height: 1.6;
}

/* AI bubble — left aligned */
.chat-ai-row {
    display: flex;
    justify-content: flex-start;
    gap: 10px;
    margin: 10px 0;
    align-items: flex-start;
}
.ai-avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: rgba(20,184,166,0.1);
    color: #14B8A6;
    font-size: 11px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 4px;
    border: 0.5px solid rgba(20,184,166,0.2);
}
.ai-bubble-wrap {
    max-width: 72%;
    background: rgba(128,128,128,0.06);
    border: 0.5px solid rgba(128,128,128,0.13);
    border-radius: 16px 16px 16px 4px;
    padding: 12px 15px;
    font-size: 14px;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
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
    st.divider()
    if st.session_state.get("chat_history"):
        if st.button("🗑 Clear chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

if "df" not in st.session_state:
    st.info("Please upload a dataset on the home page first.")
    st.page_link("Home.py", label="← Go to home")
    st.stop()

df = st.session_state.df
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_API_KEY = None

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY isn't configured. Add it to .streamlit/secrets.toml locally, "
             "or to Settings > Secrets on Streamlit Cloud.")
    st.stop()

def build_context(df):
    rows = max(len(df), 1)

    # Numeric summary - min/max/median so the model never has to guess bounds
    num_cols = df.select_dtypes(include='number').columns.tolist()
    num_summary = ""
    for col in num_cols[:15]:
        s = df[col].dropna()
        if s.empty:
            continue
        line = (f"  - {col}: mean={s.mean():.2f}, median={s.median():.2f}, "
                f"std={s.std():.2f}, min={s.min():.2f}, max={s.max():.2f}")
        if s.nunique() <= 4:   # flag-like columns: give the exact counts
            vc = s.value_counts()
            line += " | counts: " + ", ".join(f"{k:g}: {int(v):,}" for k, v in vc.items())
        num_summary += line + "\n"

    # Text/category columns - full value counts when there are few categories
    text_cols = [c for c in df.columns
                 if not pd.api.types.is_numeric_dtype(df[c])
                 and (pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_object_dtype(df[c]))]
    str_summary = ""
    for col in text_cols[:15]:
        counts = df[col].value_counts(dropna=True)
        total = int(df[col].notna().sum()) or 1
        if len(counts) <= 12:
            vals = ", ".join(f"{str(k)[:30]}: {int(v):,} ({v / total:.0%})" for k, v in counts.items())
            str_summary += f"  - {col}: {len(counts)} unique | counts: {vals}\n"
        else:
            tops = ", ".join(f"{str(k)[:30]} ({v / total:.0%})" for k, v in counts.head(3).items())
            str_summary += f"  - {col}: {len(counts)} unique | top: {tops}\n"

    missing = {c: f"{int(v)} ({v / rows:.1%})" for c, v in df.isnull().sum().items() if v > 0}
    dupes = int(df.duplicated().sum())

    return f"""You are an expert data analyst assistant inside CleanSight.

Dataset profile:
- Shape: {df.shape[0]:,} rows x {df.shape[1]} columns
- Column names: {', '.join(df.columns.tolist())}
- Duplicate rows: {dupes:,}
- Missing values: {missing if missing else 'None'}
- Numeric columns:
{num_summary if num_summary else '  None'}
- Text/category columns:
{str_summary if str_summary else '  None'}

Response rules:
- Keep answers SHORT: under 120 words unless the user explicitly asks for detail.
- Use at most 5 brief bullets or 2 short paragraphs. No tables. No headers unless asked.
- For "summarise" requests cover only: size and shape, data quality (missing/duplicates), the likely target or key columns, one notable pattern, one suggested next step.
- Answer from the figures above. State the number directly when it is available.
- You cannot run code. Never show code, pandas snippets or step-by-step instructions for computing something. If a figure is not available above, say so in one sentence and suggest rephrasing the question (for example "how many rows have sex = M?").
- Never write placeholders like "~?". No filler sentences."""

def get_groq_response(df, history):
    client = Groq(api_key=GROQ_API_KEY)
    messages = [{"role": "system", "content": build_context(df)}]
    messages += history[-10:]  # keep only recent turns
    kwargs = dict(model="openai/gpt-oss-20b", messages=messages, max_tokens=2048)
    try:
        # gpt-oss is a reasoning model: reasoning tokens count toward max_tokens,
        # so keep reasoning light to leave room for the visible answer.
        resp = client.chat.completions.create(reasoning_effort="low", **kwargs)
    except Exception:
        resp = client.chat.completions.create(**kwargs)
    choice = resp.choices[0]
    text = (choice.message.content or "").strip()
    if choice.finish_reason == "length":
        text += "\n\n_The reply was cut short - ask me to continue or to focus on one part._"
    return text or "I couldn't generate a response - please try rephrasing."

def llm_plan(df, question, history):
    """Ask the model for a structured query plan (it never runs code - we execute the plan)."""
    users = [m["content"] for m in history[:-1] if m["role"] == "user"]
    prompt = dq.planner_prompt(df, question, users[-1] if users else None)
    client = Groq(api_key=GROQ_API_KEY)
    kwargs = dict(model="openai/gpt-oss-20b", messages=[{"role": "user", "content": prompt}],
                  max_tokens=800, temperature=0)
    try:
        resp = client.chat.completions.create(reasoning_effort="low", **kwargs)
    except Exception:
        resp = client.chat.completions.create(**kwargs)
    return dq.parse_plan(resp.choices[0].message.content, df)


def answer_question(df, history):
    """1) deterministic rules  2) LLM-built query plan executed on the data  3) conversational answer."""
    question = history[-1]["content"]

    plan = dq.local_plan(question, df)
    if plan:
        answer = dq.execute_plan(df, plan)
        if answer:
            return answer

    has_previous = any(m["role"] == "user" for m in history[:-1])
    if dq.looks_computational(question, has_previous):
        try:
            plan = llm_plan(df, question, history)
            if plan and plan.get("op") != "none":
                answer = dq.execute_plan(df, plan)
                if answer:
                    return answer
        except Exception as e:
            if "401" in str(e) or "invalid_api_key" in str(e):
                raise

    return get_groq_response(df, history)


def friendly_error(e):
    msg = str(e)
    if "401" in msg or "invalid_api_key" in msg:
        return ("⚠️ Groq rejected the API key (401). Check that GROQ_API_KEY in your "
                "secrets is complete and still active.")
    return f"Error: {msg}"

# ── Fixed top bar ──
st.markdown(f"""
<div class="top-bar">
  <div style='display:flex;align-items:center;justify-content:space-between'>
    <div style='display:flex;align-items:center;gap:14px'>
      <span style='font-size:19px;font-weight:500'>🤖 AI Assistant</span>
      <span style='font-size:12px;opacity:0.35'>GPT OSS 20B</span>
    </div>
    <div style='border:0.5px solid rgba(20,184,166,0.3);border-radius:8px;
         padding:5px 12px;font-size:12px;background:rgba(20,184,166,0.07);
         color:#14B8A6'>
      📋 {df.shape[0]:,} rows · {df.shape[1]} cols · {st.session_state.filename}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Main content (pushed below fixed bar) ──
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# ── Chat messages ──
if not st.session_state.chat_history:
    st.markdown("""
    <div style='text-align:center;padding:80px 0 40px 0;opacity:0.25;font-size:14px'>
      💬 Ask anything about your dataset
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-user">
                <div class="bubble">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg["content"])

# ── Suggestion chips ──
st.markdown("<p style='font-size:12px;opacity:0.35;margin:24px 0 6px 0'>Quick questions</p>",
            unsafe_allow_html=True)

suggestions = [
    "Summarise this dataset",
    "Find correlations",
    "Suggest cleaning steps",
    "What model should I use?",
]
chip_cols = st.columns(4)
for i, s in enumerate(suggestions):
    with chip_cols[i]:
        if st.button(s, use_container_width=True, key=f"chip_{i}"):
            st.session_state.chat_history.append({"role": "user", "content": s})
            with st.spinner(""):
                try:
                    reply = answer_question(df, st.session_state.chat_history)
                except Exception as e:
                    reply = friendly_error(e)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ── Chat input ──
user_input = st.chat_input("Ask about your data...")
if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.spinner(""):
        try:
            reply = answer_question(df, st.session_state.chat_history)
        except Exception as e:
            reply = friendly_error(e)
    st.session_state.chat_history.append({"role": "assistant", "content": reply})
    st.rerun()