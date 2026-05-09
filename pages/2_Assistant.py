import streamlit as st
from groq import Groq

st.set_page_config(page_title="AI Assistant · InsightForge AI", layout="wide")
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
    background: rgba(55,138,221,0.13);
    border: 0.5px solid rgba(55,138,221,0.25);
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
    background: rgba(55,138,221,0.1);
    color: #378ADD;
    font-size: 11px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 4px;
    border: 0.5px solid rgba(55,138,221,0.2);
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

GROQ_API_KEY = "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"

def build_context(df):
    # Numeric summary — mean and std only, max 10 cols
    num_cols = df.select_dtypes(include='number').columns.tolist()
    num_summary = ""
    for col in num_cols[:10]:
        mean = round(df[col].mean(), 2)
        std = round(df[col].std(), 2)
        num_summary += f"  - {col}: mean={mean}, std={std}\n"

    # String/object columns — just name, unique count, top 3 values
    str_cols = df.select_dtypes(include='object').columns.tolist()
    str_summary = ""
    for col in str_cols[:8]:  # max 8 string cols
        unique = df[col].nunique()
        # top 3 most frequent values, truncated to 30 chars each
        top3 = df[col].value_counts().head(3).index.tolist()
        top3_clean = [str(v)[:30] for v in top3]
        str_summary += f"  - {col}: {unique} unique | top: {', '.join(top3_clean)}\n"

    # Missing values — only columns that have them
    missing = {c: int(v) for c, v in df.isnull().sum().items() if v > 0}

    return f"""You are an expert data analyst assistant inside InsightForge AI.

Dataset profile:
- Shape: {df.shape[0]:,} rows × {df.shape[1]} columns
- Column names: {', '.join(df.columns.tolist())}
- Dtypes: {', '.join([f"{c}({str(t)[:5]})" for c, t in df.dtypes.items()])}
- Missing values: {missing if missing else 'None'}
- Numeric columns (mean, std):
{num_summary if num_summary else '  None'}
- Text/category columns (unique count + top values):
{str_summary if str_summary else '  None'}

Be specific, concise, and practical. Format responses with markdown headers and bullets.
NEVER write code unless the user explicitly asks for it. No filler sentences."""

def get_groq_response(df, history):
    client = Groq(api_key=GROQ_API_KEY)
    messages = [{"role": "system", "content": build_context(df)}]
    messages += history
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024
    )
    return resp.choices[0].message.content

# ── Fixed top bar ──
st.markdown(f"""
<div class="top-bar">
  <div style='display:flex;align-items:center;justify-content:space-between'>
    <div style='display:flex;align-items:center;gap:14px'>
      <span style='font-size:19px;font-weight:500'>🤖 AI Assistant</span>
      <span style='font-size:12px;opacity:0.35'>Llama 3.3 70B</span>
    </div>
    <div style='border:0.5px solid rgba(55,138,221,0.3);border-radius:8px;
         padding:5px 12px;font-size:12px;background:rgba(55,138,221,0.07);
         color:#378ADD'>
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
                    reply = get_groq_response(df, st.session_state.chat_history)
                except Exception as e:
                    reply = f"Error: {e}"
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ── Chat input ──
user_input = st.chat_input("Ask about your data...")
if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.spinner(""):
        try:
            reply = get_groq_response(df, st.session_state.chat_history)
        except Exception as e:
            reply = f"Error: {e}"
    st.session_state.chat_history.append({"role": "assistant", "content": reply})
    st.rerun()