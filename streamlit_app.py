"""
RAG Frontend — Streamlit UI
Connects to FastAPI backend at http://localhost:8000
"""

import streamlit as st
import requests
import time
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RAG Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────
BACKEND_URL           = "http://localhost:8000"
UPLOAD_ENDPOINT       = f"{BACKEND_URL}/upload-documents"
QUERY_ENDPOINT        = f"{BACKEND_URL}/query"
BOOK_CONTEXT_ENDPOINT = f"{BACKEND_URL}/create-book-context"

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── App background ── */
.stApp {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    color: #e2e8f0;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b27 100%);
    border-right: 1px solid #2d3748;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #7c3aed;
}

/* ── Chat bubbles ── */
.user-bubble {
    background: linear-gradient(135deg, #7c3aed, #5b21b6);
    color: #fff;
    padding: 12px 18px;
    border-radius: 18px 18px 4px 18px;
    margin: 8px 0 8px 15%;
    word-wrap: break-word;
    box-shadow: 0 4px 15px rgba(124,58,237,0.35);
    font-size: 0.95rem;
    line-height: 1.6;
}

.assistant-bubble {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    color: #e2e8f0;
    padding: 14px 18px;
    border-radius: 18px 18px 18px 4px;
    margin: 8px 15% 8px 0;
    word-wrap: break-word;
    border: 1px solid #334155;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    font-size: 0.95rem;
    line-height: 1.7;
}

.bubble-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 4px;
    opacity: 0.65;
}

.user-label   { color: #c4b5fd; text-align: right; margin-right: 4px; }
.assist-label { color: #60a5fa; }

.source-tag {
    display: inline-block;
    background: #1e3a5f;
    color: #93c5fd;
    border: 1px solid #2563eb;
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 0.72rem;
    margin: 3px 3px 0 0;
}

/* ── Uploaded file pill ── */
.file-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #1a2744;
    border: 1px solid #2d4a7a;
    color: #93c5fd;
    border-radius: 9999px;
    padding: 4px 12px;
    font-size: 0.78rem;
    margin: 4px 4px 4px 0;
    word-break: break-all;
}
.file-pill-ok  { border-color: #16a34a; color: #86efac; background: #052e16; }
.file-pill-err { border-color: #dc2626; color: #fca5a5; background: #2d0a0a; }

/* ── Section divider ── */
.section-title {
    color: #a78bfa;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 20px 0 8px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #2d3748;
}

/* ── Metric card ── */
.metric-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 12px 16px;
    margin: 6px 0;
    font-size: 0.82rem;
    color: #94a3b8;
}
.metric-card b { color: #e2e8f0; }

/* ── Input box override ── */
.stTextInput > div > div > input,
.stChatInputContainer textarea {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border: 1px solid #4c1d95 !important;
    border-radius: 12px !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #5b21b6);
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 8px 20px;
    font-weight: 600;
    transition: all 0.2s;
    width: 100%;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #6d28d9, #4c1d95);
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(124,58,237,0.4);
}

/* ── Upload widget ── */
[data-testid="stFileUploader"] {
    border: 2px dashed #4c1d95;
    border-radius: 12px;
    padding: 10px;
}

/* ── Scrollable chat area ── */
.chat-container {
    max-height: 62vh;
    overflow-y: auto;
    padding-right: 4px;
    scrollbar-width: thin;
    scrollbar-color: #4c1d95 #0f172a;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #475569;
}
.empty-state .icon { font-size: 3.5rem; margin-bottom: 16px; }
.empty-state .hint { font-size: 0.88rem; }
</style>
""", unsafe_allow_html=True)


# ── Session state initialisation ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []          # list of {role, content, sources, chunks, ts}

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []    # list of {name, status, chunks}

if "top_k" not in st.session_state:
    st.session_state.top_k = 5

if "source_filter" not in st.session_state:
    st.session_state.source_filter = ""

if "book_context_active" not in st.session_state:
    st.session_state.book_context_active = False

if "book_context_title" not in st.session_state:
    st.session_state.book_context_title = ""


# ── Helper — check backend health ─────────────────────────────────────────────
def _backend_online() -> bool:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# ── Helper — create book context ──────────────────────────────────────────────
def create_book_context(payload: dict) -> dict:
    try:
        response = requests.post(BOOK_CONTEXT_ENDPOINT, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend."}
    except requests.exceptions.HTTPError as e:
        return {"error": f"Backend error: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_book_context() -> dict:
    try:
        response = requests.get(BOOK_CONTEXT_ENDPOINT, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"active": False}


# ── Helper — upload files ─────────────────────────────────────────────────────
def upload_files(files) -> list[dict]:
    file_objs = []
    for f in files:
        file_objs.append(("files", (f.name, f.getvalue(), f.type or "application/octet-stream")))

    try:
        # Large PDFs can have hundreds of chunks; Ollama embedding each one takes
        # time — use a generous timeout so we never cut off a legitimate request.
        response = requests.post(UPLOAD_ENDPOINT, files=file_objs, timeout=600)
        response.raise_for_status()
        return response.json().get("details", [])
    except requests.exceptions.Timeout:
        return [{"filename": f.name, "status": "error",
                 "reason": "Timed out (>10 min). The file may be very large. "
                           "Try splitting it into smaller files."} for f in files]
    except requests.exceptions.ConnectionError:
        return [{"filename": f.name, "status": "error", "reason": "Cannot connect to backend."} for f in files]
    except requests.exceptions.HTTPError as e:
        return [{"filename": f.name, "status": "error", "reason": str(e)} for f in files]
    except Exception as e:
        return [{"filename": f.name, "status": "error", "reason": str(e)} for f in files]


# ── Helper — query backend ────────────────────────────────────────────────────
def query_backend(question: str, top_k: int, source_filter: str) -> dict:
    payload = {"question": question, "top_k": top_k}
    if source_filter.strip():
        payload["source_filter"] = source_filter.strip()

    try:
        response = requests.post(QUERY_ENDPOINT, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. Is the FastAPI server running on port 8000?"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"Backend error: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


# ── Helper — render a chat message ────────────────────────────────────────────
def render_message(msg: dict):
    if msg["role"] == "user":
        st.markdown(f'<div class="bubble-label user-label">You</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bubble-label assist-label">🧠 RAG Assistant</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="assistant-bubble">{msg["content"]}</div>', unsafe_allow_html=True)

        # Source pills
        if msg.get("sources"):
            pills_html = "".join(
                f'<span class="source-tag">📄 {s["source"]} · p{s["page"]}</span>'
                for s in msg["sources"]
            )
            st.markdown(f'<div style="margin: 0 15% 10px 0">{pills_html}</div>', unsafe_allow_html=True)

        # Show retrieved chunks in expander
        if msg.get("chunks"):
            with st.expander(f"📎 {len(msg['chunks'])} retrieved context chunks", expanded=False):
                for i, chunk in enumerate(msg["chunks"], 1):
                    st.markdown(
                        f"**[{i}]** `{chunk['source']}` · page {chunk['page']} "
                        f"· chunk #{chunk['chunk_index']} · score **{chunk['score']}**"
                    )
                    st.caption(chunk["text"][:500] + ("…" if len(chunk["text"]) > 500 else ""))
                    st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # ── Logo / title ─────────────────────────────────────────────────────────
    st.markdown("## 🧠 RAG Assistant")
    st.caption("Powered by Ollama · LangChain · ChromaDB")

    st.divider()

    # ── Backend status ────────────────────────────────────────────────────────
    online = _backend_online()
    status_color = "#22c55e" if online else "#ef4444"
    status_text  = "Backend online" if online else "Backend offline"
    st.markdown(
        f'<div class="metric-card">🔌 <b>Status:</b> '
        f'<span style="color:{status_color}">● {status_text}</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">📂 Upload Documents</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drop files here",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Supported: PDF, DOCX, TXT",
    )

    upload_btn = st.button("⬆️  Ingest Documents", disabled=not uploaded)

    if upload_btn and uploaded:
        with st.spinner("⏳ Uploading & indexing… Large files may take a few minutes while Ollama embeds the chunks. Please wait."):
            results = upload_files(uploaded)

        for r in results:
            status = r.get("status", "error")
            name   = r.get("filename", "?")
            if status == "success":
                chunks = r.get("chunks_stored", "?")
                st.session_state.uploaded_files.append({"name": name, "status": "ok", "chunks": chunks})
            else:
                reason = r.get("reason", "Unknown error")
                st.session_state.uploaded_files.append({"name": name, "status": "error", "reason": reason})

    # ── Show ingested files ───────────────────────────────────────────────────
    if st.session_state.uploaded_files:
        st.markdown('<div class="section-title">✅ Ingested Files</div>', unsafe_allow_html=True)
        for f in st.session_state.uploaded_files:
            if f["status"] == "ok":
                st.markdown(
                    f'<div class="file-pill file-pill-ok">✔ {f["name"]} &nbsp;<span style="opacity:.6">({f["chunks"]} chunks)</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="file-pill file-pill-err">✖ {f["name"]}<br><span style="font-size:.68rem">{f.get("reason","")}</span></div>',
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── 📖 Book Context Builder ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">📖 Book Context Builder</div>', unsafe_allow_html=True)

    # Show active context badge
    ctx_data = fetch_book_context()
    if ctx_data.get("active"):
        st.session_state.book_context_active = True
        st.session_state.book_context_title  = ctx_data.get("title", "Untitled")
        st.markdown(
            f'<div class="metric-card" style="border-color:#7c3aed">'
            f'📗 <b>Active context:</b> '
            f'<span style="color:#a78bfa">{st.session_state.book_context_title}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.session_state.book_context_active = False
        st.markdown(
            '<div class="metric-card">📘 <b>No book context set</b> — generic RAG mode</div>',
            unsafe_allow_html=True,
        )

    with st.expander("⚙️ Configure Book Context", expanded=not ctx_data.get("active", False)):
        bc_title       = st.text_input("Book Title *",
                            value=ctx_data.get("title", "") if ctx_data.get("active") else "",
                            placeholder="e.g. Mastering Deep Learning")
        bc_subtitle    = st.text_input("Subtitle",
                            value=ctx_data.get("subtitle", "") if ctx_data.get("active") else "",
                            placeholder="e.g. From Zero to Production")
        bc_audience    = st.text_area("Target Audience *",
                            value=ctx_data.get("target_audience", "") if ctx_data.get("active") else "",
                            placeholder="e.g. ML engineers with 1-3 years of experience",
                            height=70)
        bc_objective   = st.text_area("Author's Objective *",
                            value=ctx_data.get("author_objective", "") if ctx_data.get("active") else "",
                            placeholder="e.g. Teach practitioners to build scalable ML pipelines",
                            height=70)
        bc_transform   = st.text_area("Reader Transformation *",
                            value=ctx_data.get("reader_transformation", "") if ctx_data.get("active") else "",
                            placeholder="e.g. From theory-only to production-ready practitioner",
                            height=70)
        bc_initial     = st.text_area("Initial State (before reading) *",
                            value=ctx_data.get("initial_state", "") if ctx_data.get("active") else "",
                            placeholder="e.g. Knows Python basics, unfamiliar with MLOps",
                            height=70)
        bc_final       = st.text_area("Final State (after reading) *",
                            value=ctx_data.get("final_state", "") if ctx_data.get("active") else "",
                            placeholder="e.g. Can deploy and monitor ML models in production",
                            height=70)
        bc_tone        = st.text_input("Tone & Style *",
                            value=ctx_data.get("tone", "") if ctx_data.get("active") else "",
                            placeholder="e.g. Authoritative yet approachable, code-first")

        save_ctx_btn = st.button("📘 Save Book Context", use_container_width=True)

        if save_ctx_btn:
            required = [bc_title, bc_audience, bc_objective, bc_transform,
                        bc_initial, bc_final, bc_tone]
            if not all(f.strip() for f in required):
                st.error("⚠️ Please fill in all required fields (marked with *).")
            else:
                with st.spinner("📘 Saving book context…"):
                    result = create_book_context({
                        "title":                bc_title.strip(),
                        "subtitle":             bc_subtitle.strip(),
                        "target_audience":      bc_audience.strip(),
                        "author_objective":     bc_objective.strip(),
                        "reader_transformation": bc_transform.strip(),
                        "initial_state":        bc_initial.strip(),
                        "final_state":          bc_final.strip(),
                        "tone":                 bc_tone.strip(),
                    })
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    st.success("✅ Book context saved! All future queries will use this context.")
                    st.session_state.book_context_active = True
                    st.session_state.book_context_title  = bc_title.strip()
                    st.rerun()

    st.divider()

    # ── Query settings ────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">⚙️ Query Settings</div>', unsafe_allow_html=True)

    st.session_state.top_k = st.slider(
        "Top-K chunks to retrieve",
        min_value=1, max_value=20,
        value=st.session_state.top_k,
        help="How many context passages to pass to the LLM",
    )

    st.session_state.source_filter = st.text_input(
        "Filter by filename (optional)",
        value=st.session_state.source_filter,
        placeholder="e.g. report.pdf",
        help="Restrict retrieval to a specific document",
    )

    st.divider()

    # ── Clear chat ────────────────────────────────────────────────────────────
    if st.button("🗑️  Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.caption("RAG Backend · FastAPI · llama3.1:8b")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Chat Interface
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<h1 style="color:#a78bfa;font-size:1.8rem;margin-bottom:0">🧠 RAG Book Assistant</h1>',
    unsafe_allow_html=True,
)
if st.session_state.book_context_active:
    st.markdown(
        f'<span style="background:#3b1d8a;color:#c4b5fd;border-radius:9999px;'
        f'padding:3px 14px;font-size:0.78rem;font-weight:600;">'
        f'📖 Book Mode · {st.session_state.book_context_title}</span>',
        unsafe_allow_html=True,
    )
    st.caption("Context-aware generation is active. Every answer is shaped by your book goals.")
else:
    st.caption("Ask questions about your uploaded documents. Set a Book Context to enable author-mode generation.")

st.divider()

# ── Render chat history ───────────────────────────────────────────────────────
chat_area = st.container()
with chat_area:
    if not st.session_state.messages:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">💬</div>
            <b>No messages yet</b><br>
            <span class="hint">Upload documents in the sidebar, then ask a question below.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            render_message(msg)

st.divider()

# ── Chat input ────────────────────────────────────────────────────────────────
with st.form(key="chat_form", clear_on_submit=True):
    col_input, col_btn = st.columns([9, 1])
    with col_input:
        user_input = st.text_input(
            "Your question",
            placeholder="Ask anything about your documents…",
            label_visibility="collapsed",
        )
    with col_btn:
        send = st.form_submit_button("Send", use_container_width=True)

# ── Handle submission ─────────────────────────────────────────────────────────
if send and user_input.strip():
    question = user_input.strip()

    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": question,
        "ts": datetime.now().strftime("%H:%M"),
    })

    # Query backend with spinner
    with st.spinner("🔍 Retrieving context & generating answer…"):
        result = query_backend(
            question=question,
            top_k=st.session_state.top_k,
            source_filter=st.session_state.source_filter,
        )

    if "error" in result:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"⚠️ **Error:** {result['error']}",
            "sources": [],
            "chunks": [],
            "ts": datetime.now().strftime("%H:%M"),
        })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": result.get("answer", "No answer returned."),
            "sources": result.get("sources", []),
            "chunks": result.get("retrieved_chunks", []),
            "ts": datetime.now().strftime("%H:%M"),
        })

    st.rerun()
