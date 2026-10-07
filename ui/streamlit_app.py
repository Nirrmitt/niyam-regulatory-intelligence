import html
import os

import httpx
import streamlit as st


API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
REQUEST_TIMEOUT = 60.0
EXAMPLE_QUESTIONS = [
    "What disclosures are required for material risk exposures?",
    "What governance responsibilities does the regulator describe?",
    "What should a bank report to its stakeholders?",
]

st.set_page_config(
    page_title="Niyam | Regulatory Intelligence",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
        --ink: #172c2b;
        --muted: #637775;
        --teal: #176b62;
        --mint: #d8eee4;
        --paper: #f6f8f4;
        --line: #e2eae3;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 87% 3%, rgba(198, 230, 212, .62), transparent 26rem),
            linear-gradient(180deg, #f7faf6 0%, #f4f7f3 100%);
        color: var(--ink);
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { right: 1rem; }
    .block-container { max-width: 1240px; padding-top: 1.5rem; padding-bottom: 4rem; }
    [data-testid="stSidebar"] {
        background: #eef4ed;
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] > div { padding-top: 1.6rem; }
    .brand-row { display: flex; align-items: center; gap: 12px; margin-bottom: 2.8rem; }
    .brand-mark {
        display: grid; place-items: center; width: 43px; height: 43px;
        border-radius: 15px; background: #176b62; color: white;
        font: 800 20px 'Manrope', sans-serif;
        box-shadow: 0 8px 20px rgba(23,107,98,.18);
    }
    .brand-name { color: var(--ink); font: 800 20px 'Manrope', sans-serif; letter-spacing: -.7px; }
    .brand-sub { color: var(--muted); font-size: 11px; letter-spacing: .07em; text-transform: uppercase; }
    .hero {
        position: relative; overflow: hidden; padding: 2.4rem 2.6rem;
        border: 1px solid rgba(213, 229, 216, .9); border-radius: 28px;
        background: linear-gradient(118deg, #e8f3e9 0%, #f5f8f1 53%, #deeee4 100%);
        box-shadow: 0 18px 50px rgba(24, 62, 51, .055);
        margin: .3rem 0 1.7rem;
    }
    .hero:after {
        content: '§'; position: absolute; right: 4.2rem; top: -4.5rem;
        font: 400 250px Georgia, serif; color: rgba(23,107,98,.075);
        transform: rotate(-12deg); pointer-events: none;
    }
    .eyebrow {
        display: inline-flex; align-items: center; gap: 8px; padding: 7px 11px;
        border-radius: 999px; background: rgba(255,255,255,.7);
        color: #25665d; font-size: 11px; font-weight: 700; letter-spacing: .09em;
        text-transform: uppercase;
    }
    .eyebrow-dot { width: 7px; height: 7px; border-radius: 50%; background: #37a876; }
    .hero h1 {
        max-width: 720px; margin: 1.05rem 0 .55rem; color: #16312e;
        font: 800 clamp(2.05rem, 4vw, 3.35rem)/1.08 'Manrope', sans-serif;
        letter-spacing: -2px;
    }
    .hero p { max-width: 650px; margin: 0; color: #526b66; font-size: 1.02rem; line-height: 1.7; }
    .section-kicker {
        color: #638078; font-size: 11px; font-weight: 700; letter-spacing: .12em;
        text-transform: uppercase; margin: 1.6rem 0 .8rem;
    }
    .stTextArea textarea {
        min-height: 120px !important; padding: 1rem 1.1rem !important;
        border: 1px solid #dce7df !important; border-radius: 17px !important;
        background: rgba(255,255,255,.88) !important; color: var(--ink) !important;
        font-size: 16px !important; box-shadow: 0 5px 18px rgba(28,62,50,.035);
    }
    .stTextArea textarea:focus { border-color: #4d9d83 !important; box-shadow: 0 0 0 3px rgba(64,151,119,.12) !important; }
    .stButton > button, .stFormSubmitButton > button {
        min-height: 45px; border-radius: 13px; border: 1px solid #176b62;
        background: #176b62; color: #fff; font-weight: 700;
        box-shadow: 0 8px 19px rgba(23,107,98,.16); transition: .18s ease;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        border-color: #10584f; background: #10584f; color: #fff;
        transform: translateY(-1px); box-shadow: 0 11px 23px rgba(23,107,98,.2);
    }
    div[data-testid="stFormSubmitButton"] button { width: 100%; }
    .stButton button[kind="secondary"] {
        border: 1px solid #dce8df; background: rgba(255,255,255,.76); color: #325c53;
        box-shadow: none; font-size: 13px; min-height: 43px;
    }
    .stButton button[kind="secondary"]:hover { border-color: #93bdae; background: #fff; color: #174f46; }
    div[data-testid="stMetric"] {
        padding: 15px 17px; border: 1px solid #e0e9e2; border-radius: 16px;
        background: rgba(255,255,255,.78);
    }
    div[data-testid="stMetricLabel"] { color: #71837d; }
    div[data-testid="stMetricValue"] { color: #1b3d36; font-family: 'Manrope', sans-serif; }
    div[data-testid="stExpander"] {
        border: 1px solid #e0e9e2; border-radius: 15px; background: rgba(255,255,255,.7);
    }
    .answer-card {
        padding: 1.35rem 1.55rem; border: 1px solid #d9e8dc;
        border-left: 4px solid #31866c; border-radius: 17px;
        background: linear-gradient(110deg, #fff 0%, #f5faf5 100%);
        color: #24433c; font-size: 1.02rem; line-height: 1.8;
        box-shadow: 0 10px 28px rgba(36,75,57,.045);
    }
    .result-label {
        color: #638078; font-size: 11px; font-weight: 700;
        letter-spacing: .12em; text-transform: uppercase; margin-bottom: .65rem;
    }
    .source-card {
        padding: 1rem 1.15rem; margin: .45rem 0; border: 1px solid #e3ebe4;
        border-radius: 14px; background: rgba(255,255,255,.85);
    }
    .source-title { color: #26463e; font-weight: 700; }
    .source-meta { color: #73857f; font-size: 12px; }
    .source-snippet { color: #536b63; font-size: 14px; line-height: 1.65; margin-top: .55rem; }
    .footer-note { color: #83918a; font-size: 12px; text-align: center; margin-top: 3rem; }
    @media (max-width: 700px) {
        .hero { padding: 1.65rem 1.35rem; border-radius: 21px; }
        .hero:after { right: -1.2rem; font-size: 180px; }
        .hero h1 { letter-spacing: -1px; }
        .block-container { padding-top: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY} if API_KEY else {}


@st.cache_data(ttl=15, show_spinner=False)
def get_api_health() -> dict:
    response = httpx.get(
        f"{API_URL}/health",
        headers=api_headers(),
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def run_search(question: str, strategy: str, mode: str, top_k: int) -> dict:
    response = httpx.post(
        f"{API_URL}/ask",
        headers=api_headers(),
        json={
            "question": question,
            "strategy": strategy,
            "mode": mode,
            "top_k": top_k,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


with st.sidebar:
    st.markdown(
        """
        <div class="brand-row">
            <div class="brand-mark">N</div>
            <div><div class="brand-name">niyam</div>
            <div class="brand-sub">Regulatory intelligence</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### Tune your search")
    st.caption("Choose how the assistant finds relevant provisions.")
    strategy = st.selectbox(
        "Chunking strategy",
        ["recursive", "fixed"],
        format_func=lambda value: "Context-aware"
        if value == "recursive"
        else "Fixed-size",
        help="Context-aware chunks preserve nearby text together.",
    )
    mode = st.selectbox(
        "Search approach",
        ["hybrid_rerank", "hybrid", "vector", "keyword"],
        format_func=lambda value: {
            "hybrid_rerank": "Balanced + reranked",
            "hybrid": "Balanced",
            "vector": "Meaning-based",
            "keyword": "Exact terms",
        }[value],
        help="Balanced search combines semantic and keyword matching.",
    )
    top_k = st.slider(
        "Sources to inspect",
        min_value=1,
        max_value=10,
        value=5,
        help="More sources provide broader coverage.",
    )
    st.divider()
    st.markdown("#### Knowledge base")
    try:
        health = get_api_health()
        st.success("Connected to Niyam API", icon="🟢")
        st.metric("Indexed passages", health.get("documents_loaded", 0))
    except httpx.HTTPError:
        st.error("API unavailable. Check that the backend is running.", icon="🔌")
    except ValueError:
        st.error("API returned an invalid health response.", icon="⚠️")
    st.caption("Answers are grounded in the documents currently indexed.")

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow"><span class="eyebrow-dot"></span> Your regulatory research agent</div>
        <h1>Find the rule.<br>Understand what it means.</h1>
        <p>Ask a question in plain language. Niyam searches your regulatory library
        and brings back relevant passages with page-level citations.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-kicker">Start with a question</div>', unsafe_allow_html=True
)

if "question_draft" not in st.session_state:
    st.session_state.question_draft = ""
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_question" not in st.session_state:
    st.session_state.last_question = ""

st.markdown("**Not sure where to start?**")
example_cols = st.columns(len(EXAMPLE_QUESTIONS))
selected_example = None
for index, (col, example) in enumerate(zip(example_cols, EXAMPLE_QUESTIONS)):
    with col:
        if st.button(example, key=f"example_{index}", use_container_width=True):
            selected_example = example

if selected_example:
    st.session_state.question_draft = selected_example

with st.form("ask_form", clear_on_submit=False):
    question = st.text_area(
        "Your question",
        key="question_draft",
        label_visibility="collapsed",
        placeholder="e.g. What disclosures are required for material risk exposures?",
        max_chars=500,
        height=125,
    )
    ask_col, hint_col = st.columns([1, 3])
    with ask_col:
        submitted = st.form_submit_button("✦  Find an answer", type="primary")
    with hint_col:
        st.caption("Specific questions usually lead to more useful citations.")

if selected_example:
    submitted = True
    question = selected_example

if submitted:
    cleaned_question = question.strip()
    if len(cleaned_question) < 5:
        st.warning("Please enter a question with at least 5 characters.")
    else:
        try:
            with st.spinner("Searching your regulatory library..."):
                st.session_state.last_result = run_search(
                    cleaned_question,
                    strategy,
                    mode,
                    top_k,
                )
                st.session_state.last_question = cleaned_question
        except httpx.HTTPStatusError as exc:
            st.error(
                f"The API returned HTTP {exc.response.status_code}: {exc.response.text}"
            )
        except httpx.RequestError as exc:
            st.error(f"Could not reach the API at {API_URL}: {exc}")
        except ValueError:
            st.error("The API returned a response that could not be read.")

result = st.session_state.last_result
if result:
    st.markdown("---")
    result_col, question_col = st.columns([3, 2])
    with result_col:
        st.markdown(
            '<div class="result-label">Research result</div>', unsafe_allow_html=True
        )
        st.markdown("### Your answer")
    with question_col:
        st.caption(f"Question: “{st.session_state.last_question}”")

    answer = result.get("answer")
    if result.get("answered") and answer:
        st.markdown(
            f'<div class="answer-card">{html.escape(str(answer))}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info(answer or "No answer was returned.")

    sources = result.get("cited_sources") or []
    retrieved = result.get("retrieved_sources") or []
    score = result.get("top_score", 0)
    answer_col, sources_col, confidence_col = st.columns(3)
    with answer_col:
        st.metric("Answer status", "Grounded" if result.get("answered") else "No match")
    with sources_col:
        st.metric("Cited sources", len(sources))
    with confidence_col:
        st.metric(
            "Top match", f"{score:.0%}" if isinstance(score, (float, int)) else "—"
        )

    st.markdown("### Sources")
    if sources:
        for source in sources:
            title = html.escape(str(source.get("doc_title", "Regulatory document")))
            page = source.get("page_start", "—")
            snippet = html.escape(str(source.get("snippet", "")))
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-title">◈ &nbsp;{title}</div>
                    <div class="source-meta">Page {page}</div>
                    <div class="source-snippet">{snippet}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("No matching source citations were returned.")

    if retrieved:
        with st.expander(f"Explore {len(retrieved)} retrieved passages"):
            for number, chunk in enumerate(retrieved, start=1):
                score_value = chunk.get("vector_score", 0)
                st.markdown(
                    f"**Passage {number} · {chunk.get('doc_title', 'Document')} · "
                    f"Page {chunk.get('page_start', '—')}**"
                )
                st.progress(
                    max(0.0, min(float(score_value), 1.0)),
                    text=f"Match score: {score_value:.3f}",
                )
                st.write(chunk.get("content", ""))
                if number < len(retrieved):
                    st.divider()

st.markdown(
    '<div class="footer-note">Niyam · Regulatory research, grounded in your source documents</div>',
    unsafe_allow_html=True,
)
