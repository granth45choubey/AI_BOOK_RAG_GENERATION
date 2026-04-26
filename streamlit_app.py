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
COMPETITOR_ENDPOINT   = f"{BACKEND_URL}/analyze-competitors"
AUTHOR_DOCS_ENDPOINT  = f"{BACKEND_URL}/upload-author-documents"
OUTLINE_ENDPOINT      = f"{BACKEND_URL}/set-chapter-outline"

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

if "competitor_job_id" not in st.session_state:
    st.session_state.competitor_job_id = None

if "competitor_result" not in st.session_state:
    st.session_state.competitor_result = None

if "competitor_page" not in st.session_state:
    st.session_state.competitor_page = False

if "author_uploaded_files" not in st.session_state:
    st.session_state.author_uploaded_files = []

if "outline_active" not in st.session_state:
    st.session_state.outline_active = False


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
        st.markdown('<div class="bubble-label user-label">You</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bubble-label assist-label">🧠 RAG Assistant</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="assistant-bubble">{msg["content"]}</div>', unsafe_allow_html=True)

        if msg.get("sources"):
            pills_html = "".join(
                f'<span class="source-tag">📄 {s["source"]} · p{s["page"]}</span>'
                for s in msg["sources"]
            )
            st.markdown(f'<div style="margin: 0 15% 10px 0">{pills_html}</div>', unsafe_allow_html=True)

        if msg.get("chunks"):
            with st.expander(f"📎 {len(msg['chunks'])} retrieved context chunks", expanded=False):
                for i, chunk in enumerate(msg["chunks"], 1):
                    src_type = chunk.get("source_type", "general")
                    badge = {"author": "✍️ author", "context": "📖 context",
                             "outline": "📋 outline", "competitor": "🔍 competitor"}.get(src_type, "📄 general")
                    st.markdown(
                        f"**[{i}]** `{chunk.get('source','?')}` · page {chunk.get('page','?')} "
                        f"· score **{chunk.get('score','?')}** · {badge}"
                    )
                    st.caption(chunk["text"][:500] + ("…" if len(chunk["text"]) > 500 else ""))
                    st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
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

    # ── 📂 General Documents ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">📂 Upload Documents</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Drop files here", type=["pdf", "docx", "txt"],
        accept_multiple_files=True, label_visibility="collapsed",
        key="general_uploader",
        help="Supported: PDF, DOCX, TXT",
    )
    upload_btn = st.button("⬆️  Ingest Documents", disabled=not uploaded)
    if upload_btn and uploaded:
        with st.spinner("⏳ Uploading & indexing…"):
            results = upload_files(uploaded)
        for r in results:
            s, nm = r.get("status", "error"), r.get("filename", "?")
            if s == "success":
                st.session_state.uploaded_files.append({"name": nm, "status": "ok", "chunks": r.get("chunks_stored", "?")})
            else:
                st.session_state.uploaded_files.append({"name": nm, "status": "error", "reason": r.get("reason", "")})
    if st.session_state.uploaded_files:
        st.markdown('<div class="section-title">✅ Ingested Files</div>', unsafe_allow_html=True)
        for f in st.session_state.uploaded_files:
            if f["status"] == "ok":
                st.markdown(f'<div class="file-pill file-pill-ok">✔ {f["name"]} &nbsp;<span style="opacity:.6">({f["chunks"]} chunks)</span></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="file-pill file-pill-err">✖ {f["name"]}<br><span style="font-size:.68rem">{f.get("reason","")}</span></div>', unsafe_allow_html=True)

    st.divider()

    # ── ✍️ Author Documents (HIGH PRIORITY) ───────────────────────────────────
    st.markdown('<div class="section-title">✍️ Author Documents (High Priority)</div>', unsafe_allow_html=True)
    st.caption("Questionnaires, transcripts, notes — retrieved first in every query.")
    author_uploaded = st.file_uploader(
        "Drop author files here", type=["pdf", "docx", "txt"],
        accept_multiple_files=True, label_visibility="collapsed",
        key="author_uploader",
        help="These files override general documents in the retrieval pipeline.",
    )
    author_btn = st.button("⬆️  Ingest Author Docs", disabled=not author_uploaded, key="author_ingest_btn")
    if author_btn and author_uploaded:
        file_objs = [("files", (f.name, f.getvalue(), f.type or "application/octet-stream")) for f in author_uploaded]
        try:
            with st.spinner("⏳ Ingesting author documents…"):
                resp = requests.post(AUTHOR_DOCS_ENDPOINT, files=file_objs, timeout=600)
                resp.raise_for_status()
                data = resp.json()
            for r in data.get("details", []):
                if r.get("status") == "success":
                    st.session_state.author_uploaded_files.append({"name": r["filename"], "status": "ok", "chunks": r.get("chunks_stored", "?")})
                else:
                    st.session_state.author_uploaded_files.append({"name": r["filename"], "status": "error", "reason": r.get("reason", "")})
        except Exception as e:
            st.error(f"❌ Author upload error: {e}")
    if st.session_state.author_uploaded_files:
        for f in st.session_state.author_uploaded_files:
            if f["status"] == "ok":
                st.markdown(f'<div class="file-pill file-pill-ok">✍️ {f["name"]} &nbsp;<span style="opacity:.6">({f["chunks"]} chunks)</span></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="file-pill file-pill-err">✖ {f["name"]}<br><span style="font-size:.68rem">{f.get("reason","")}</span></div>', unsafe_allow_html=True)

    st.divider()

    # ── 📖 Book Context Builder ───────────────────────────────────────────────
    st.markdown('<div class="section-title">📖 Book Context Builder</div>', unsafe_allow_html=True)
    ctx_data = fetch_book_context()
    if ctx_data.get("active"):
        st.session_state.book_context_active = True
        st.session_state.book_context_title  = ctx_data.get("title", "Untitled")
        st.markdown(
            f'<div class="metric-card" style="border-color:#7c3aed">'
            f'📗 <b>Active context:</b> <span style="color:#a78bfa">{st.session_state.book_context_title}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.session_state.book_context_active = False
        st.markdown('<div class="metric-card">📘 <b>No book context set</b> — generic RAG mode</div>', unsafe_allow_html=True)

    with st.expander("⚙️ Configure Book Context", expanded=not ctx_data.get("active", False)):
        bc_title    = st.text_input("Book Title *", value=ctx_data.get("title", "") if ctx_data.get("active") else "", placeholder="e.g. Mastering Deep Learning")
        bc_subtitle = st.text_input("Subtitle",     value=ctx_data.get("subtitle", "") if ctx_data.get("active") else "", placeholder="e.g. From Zero to Production")
        bc_audience = st.text_area("Target Audience *", value=ctx_data.get("target_audience", "") if ctx_data.get("active") else "", placeholder="e.g. ML engineers with 1-3 years experience", height=70)
        st.caption("💡 Fields below are optional — leave blank to auto-infer from title & audience.")
        bc_objective = st.text_area("Author's Objective",  value=ctx_data.get("author_objective", "") if ctx_data.get("active") else "", placeholder="e.g. Teach practitioners to build scalable ML pipelines (auto-inferred if blank)", height=70)
        bc_transform = st.text_area("Reader Transformation", value=ctx_data.get("reader_transformation", "") if ctx_data.get("active") else "", placeholder="e.g. From theory-only to production-ready (auto-inferred if blank)", height=70)
        bc_initial   = st.text_area("Initial State (before reading)", value=ctx_data.get("initial_state", "") if ctx_data.get("active") else "", placeholder="e.g. Knows Python basics, unfamiliar with MLOps (auto-inferred if blank)", height=70)
        bc_final     = st.text_area("Final State (after reading)", value=ctx_data.get("final_state", "") if ctx_data.get("active") else "", placeholder="e.g. Can deploy ML models in production (auto-inferred if blank)", height=70)
        bc_tone      = st.text_input("Tone & Style", value=ctx_data.get("tone", "") if ctx_data.get("active") else "", placeholder="e.g. Authoritative yet approachable (auto-inferred if blank)")
        save_ctx_btn = st.button("📘 Save Book Context", use_container_width=True)
        if save_ctx_btn:
            if not bc_title.strip() or not bc_audience.strip():
                st.error("⚠️ Title and Target Audience are required.")
            else:
                with st.spinner("📘 Saving book context… (LLM may infer missing fields)"):
                    result = create_book_context({
                        "title":                 bc_title.strip(),
                        "subtitle":              bc_subtitle.strip() or None,
                        "target_audience":       bc_audience.strip(),
                        "author_objective":      bc_objective.strip() or None,
                        "reader_transformation": bc_transform.strip() or None,
                        "initial_state":         bc_initial.strip() or None,
                        "final_state":           bc_final.strip() or None,
                        "tone":                  bc_tone.strip() or None,
                    })
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    st.success("✅ Book context saved!")
                    st.session_state.book_context_active = True
                    st.session_state.book_context_title  = bc_title.strip()
                    st.rerun()

    st.divider()

    # ── ⚙️ Query Settings ─────────────────────────────────────────────────────
    st.markdown('<div class="section-title">⚙️ Query Settings</div>', unsafe_allow_html=True)
    st.session_state.top_k = st.slider("Top-K chunks to retrieve", min_value=1, max_value=20, value=st.session_state.top_k)
    st.session_state.source_filter = st.text_input(
        "Source filter (optional)",
        value=st.session_state.source_filter,
        placeholder="Exact filename to restrict retrieval",
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE SELECTOR (top of main area)
# ══════════════════════════════════════════════════════════════════════════════
tab_rag, tab_competitor, tab_outline = st.tabs(["🧠 RAG Assistant", "🔍 Competitor Analysis", "📋 Chapter Outline"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RAG ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
with tab_rag:
    st.markdown('<h1 style="color:#a78bfa;font-size:1.8rem;margin-bottom:0">🧠 RAG Book Assistant</h1>', unsafe_allow_html=True)
    if st.session_state.book_context_active:
        st.markdown(
            f'<span style="background:#3b1d8a;color:#c4b5fd;border-radius:9999px;padding:3px 14px;font-size:0.78rem;font-weight:600;">'
            f'📖 Book Mode · {st.session_state.book_context_title}</span>',
            unsafe_allow_html=True,
        )
        st.caption("Context-aware generation is active. Every answer is shaped by your book goals.")
    else:
        st.caption("Ask questions about your uploaded documents. Set a Book Context to enable author-mode generation.")

    st.divider()

    chat_area = st.container()
    with chat_area:
        if not st.session_state.messages:
            st.info("No messages yet. Upload documents in the sidebar, then ask a question below.")
        else:
            for msg in st.session_state.messages:
                render_message(msg)

    st.divider()

    with st.form(key="chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([9, 1])
        with col_input:
            user_input = st.text_input("Your question", placeholder="Ask anything about your documents…", label_visibility="collapsed")
        with col_btn:
            send = st.form_submit_button("Send", use_container_width=True)

    if send and user_input.strip():
        question = user_input.strip()
        st.session_state.messages.append({"role": "user", "content": question, "ts": datetime.now().strftime("%H:%M")})
        with st.spinner("Retrieving context & generating answer…"):
            result = query_backend(question=question, top_k=st.session_state.top_k, source_filter=st.session_state.source_filter)
        if "error" in result:
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {result['error']}", "sources": [], "chunks": [], "ts": datetime.now().strftime("%H:%M")})
        else:
            st.session_state.messages.append({"role": "assistant", "content": result.get("answer", "No answer returned."), "sources": result.get("sources", []), "chunks": result.get("retrieved_chunks", []), "ts": datetime.now().strftime("%H:%M")})
        st.rerun()


# ==============================================================================
# TAB 2 - COMPETITOR ANALYSIS
# ==============================================================================
with tab_competitor:
    st.markdown('<h1 style="color:#a78bfa;font-size:1.8rem;margin-bottom:0">Competitor Analysis</h1>', unsafe_allow_html=True)
    st.caption("Upload 5-10 competitor PDFs. Analysis runs in the background.")
    st.divider()

    with st.form(key="competitor_form", clear_on_submit=False):
        comp_files = st.file_uploader("Upload competitor PDFs (up to 10)", type=["pdf"],
                                      accept_multiple_files=True, key="competitor_uploader")
        col_mode, col_btn2 = st.columns([3, 1])
        with col_mode:
            comp_mode = st.selectbox("Analysis mode", options=["replace", "merge"], index=0)
        with col_btn2:
            comp_submit = st.form_submit_button("Start Analysis", use_container_width=True)

    if comp_submit:
        if not comp_files:
            st.error("Please upload at least one PDF.")
        elif len(comp_files) > 10:
            st.error(f"Maximum 10 books allowed. You selected {len(comp_files)}.")
        else:
            file_objs = [("files", (f.name, f.getvalue(), "application/pdf")) for f in comp_files]
            try:
                resp = requests.post(COMPETITOR_ENDPOINT, files=file_objs, params={"mode": comp_mode}, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                st.session_state.competitor_job_id = data["job_id"]
                st.session_state.competitor_result = None
                if "warning" in data:
                    st.warning(data["warning"])
                st.success(f"Job submitted! ID: {data['job_id']}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend.")
            except Exception as e:
                st.error(f"Error: {e}")

    job_id = st.session_state.competitor_job_id
    if job_id and st.session_state.competitor_result is None:
        try:
            status_resp = requests.get(f"{COMPETITOR_ENDPOINT}/status/{job_id}", timeout=10)
            if status_resp.status_code == 200:
                job_data   = status_resp.json()
                job_status = job_data.get("status", "unknown")
                prog_map   = {"pending": 0.05, "processing": 0.5, "completed": 1.0, "failed": 1.0}
                st.progress(prog_map.get(job_status, 0.1), text=f"Status: {job_status.upper()}")
                st.caption(f"Progress: {job_data.get('progress', '')}")
                if job_status == "completed":
                    st.session_state.competitor_result = job_data.get("result", {})
                    st.rerun()
                elif job_status == "failed":
                    st.error(f"Failed: {job_data.get('error', 'Unknown error')}")
                    st.session_state.competitor_job_id = None
                else:
                    time.sleep(5)
                    st.rerun()
        except Exception as e:
            st.warning(f"Poll error: {e}")

    result_c = st.session_state.competitor_result
    if result_c is None and job_id is None:
        try:
            cr = requests.get(f"{COMPETITOR_ENDPOINT}/latest", timeout=5)
            if cr.status_code == 200:
                result_c = cr.json()
        except Exception:
            pass

    if result_c:
        st.divider()
        books_c = result_c.get("books_analyzed", [])
        st.markdown(f'<div class="metric-card">Books: <b>{len(books_c)}</b> | Mode: <b>{result_c.get("mode","replace")}</b> | Chunks: <b>{result_c.get("chunks_stored",0)}</b></div>', unsafe_allow_html=True)
        col_p, col_s, col_d = st.columns(3)
        with col_p:
            with st.expander("Writing Patterns", expanded=True):
                for p in result_c.get("patterns", []): st.markdown(f"- {p}")
                if not result_c.get("patterns"): st.caption("None extracted.")
        with col_s:
            with st.expander("Common Structures", expanded=True):
                for s in result_c.get("common_structures", []): st.markdown(f"- {s}")
                if not result_c.get("common_structures"): st.caption("None extracted.")
        with col_d:
            with st.expander("Differentiators", expanded=True):
                for d in result_c.get("differentiators", []): st.markdown(f"- {d}")
                if not result_c.get("differentiators"): st.caption("None extracted.")
        for bd in result_c.get("book_details", []):
            with st.expander(f"{bd['source']} ({bd['page_count']} pages)"):
                if bd.get("chapter_structure"):
                    st.markdown("**Chapter Headings:**")
                    for h in bd["chapter_structure"]: st.markdown(f"  - {h}")
                st.markdown("**Summary:**"); st.write(bd.get("summary", ""))
                st.markdown("**Writing Patterns:**"); st.write(bd.get("writing_patterns", ""))
                st.markdown("**Frameworks:**"); st.write(bd.get("frameworks", ""))
        if st.button("Reset Competitor Analysis", key="reset_competitor"):
            st.session_state.competitor_job_id = None
            st.session_state.competitor_result = None
            st.rerun()
    elif job_id is None:
        st.info("No competitor analysis yet. Upload 5-10 PDFs above and click Start Analysis.")


# ==============================================================================
# TAB 3 - CHAPTER OUTLINE
# ==============================================================================
with tab_outline:
    st.markdown('<h1 style="color:#a78bfa;font-size:1.8rem;margin-bottom:0">Chapter Outline</h1>', unsafe_allow_html=True)
    st.caption("Provide a chapter structure. When set, the LLM strictly follows it in every generation.")
    st.divider()

    try:
        cur_resp = requests.get(OUTLINE_ENDPOINT, timeout=5)
        cur_outline = cur_resp.json() if cur_resp.status_code == 200 else None
    except Exception:
        cur_outline = None

    if cur_outline:
        chapters_cur = cur_outline.get("chapters", [])
        st.markdown(f'<div class="metric-card">Active outline: <b>{len(chapters_cur)} chapter(s)</b></div>', unsafe_allow_html=True)
        st.session_state.outline_active = True
        with st.expander("View Current Outline", expanded=False):
            for i, ch in enumerate(chapters_cur, 1):
                st.markdown(f"**Chapter {i}: {ch['title']}**")
                for sec in ch.get("sections", []):
                    desc = f" - {sec['description']}" if sec.get("description") else ""
                    st.markdown(f"&nbsp;&nbsp;- {sec['title']}{desc}")
    else:
        st.session_state.outline_active = False
        st.info("No chapter outline set. The LLM will generate the outline dynamically.")

    st.divider()
    st.markdown("**Set Chapter Outline (JSON)**")
    st.caption("Paste valid JSON with a top-level `chapters` key.")

    example = '{"chapters": [{"title": "Introduction", "sections": [{"title": "What Is It?", "description": "Brief overview"}]}, {"title": "Core Concepts", "sections": [{"title": "Concept A"}, {"title": "Concept B"}]}]}'

    outline_input = st.text_area("Chapter Outline JSON", height=260, placeholder=example, key="outline_json_input")

    col_sub, col_clr = st.columns([3, 1])
    with col_sub:
        submit_outline = st.button("Save Outline", use_container_width=True, key="save_outline_btn")
    with col_clr:
        clear_outline = st.button("Clear", use_container_width=True, disabled=not cur_outline, key="clear_outline_btn")

    if submit_outline:
        if not outline_input.strip():
            st.error("Please paste a JSON chapter outline.")
        else:
            try:
                import json as _json
                parsed = _json.loads(outline_input)
                if "chapters" not in parsed:
                    st.error("JSON must have a top-level 'chapters' key.")
                else:
                    with st.spinner("Saving chapter outline..."):
                        resp = requests.post(OUTLINE_ENDPOINT, json=parsed, timeout=60)
                        resp.raise_for_status()
                        data = resp.json()
                    st.success(f"Outline saved! {data.get('chapters_count','?')} chapter(s).")
                    st.session_state.outline_active = True
                    st.rerun()
            except _json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend.")
            except Exception as e:
                st.error(f"Error: {e}")
    if clear_outline:
        try:
            with st.spinner("Clearing chapter outline..."):
                resp = requests.delete(OUTLINE_ENDPOINT, timeout=10)
            if resp.status_code in (200, 204):
                st.success("Chapter outline cleared.")
                st.session_state.outline_active = False
                st.rerun()
            else:
                st.error(f"Failed to clear outline: {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")
        except Exception as e:
            st.error(f"Error: {e}")
