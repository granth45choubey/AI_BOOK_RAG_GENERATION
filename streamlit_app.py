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
COMPETITOR_ENDPOINT     = f"{BACKEND_URL}/analyze-competitors"
MARKET_ENDPOINT         = f"{BACKEND_URL}/analyze-market"
AUTHOR_DOCS_ENDPOINT  = f"{BACKEND_URL}/upload-author-documents"
OUTLINE_ENDPOINT      = f"{BACKEND_URL}/set-chapter-outline"
FRAMEWORK_ENDPOINT      = f"{BACKEND_URL}/generate-frameworks"
SELECT_FW_ENDPOINT      = f"{BACKEND_URL}/select-framework"
SELECTED_FW_ENDPOINT    = f"{BACKEND_URL}/selected-framework"
FRAMEWORKS_ENDPOINT     = f"{BACKEND_URL}/frameworks"
OUTLINE_PREVIEW_ENDPOINT = f"{BACKEND_URL}/set-chapter-outline/preview"

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

/* ── Framework cards ── */
.fw-card {
    background: linear-gradient(135deg, #1e1b4b 0%, #1a1a3e 100%);
    border: 1px solid #4c1d95;
    border-radius: 16px;
    padding: 22px 22px 16px 22px;
    margin-bottom: 18px;
    position: relative;
    transition: box-shadow 0.2s;
}
.fw-card:hover {
    box-shadow: 0 8px 30px rgba(124,58,237,0.35);
}
.fw-card.selected-card {
    border: 2px solid #7c3aed;
    box-shadow: 0 0 20px rgba(124,58,237,0.5);
    background: linear-gradient(135deg, #2d1f6e 0%, #1e1b4b 100%);
}
.fw-badge {
    display: inline-block;
    background: linear-gradient(90deg, #7c3aed, #5b21b6);
    color: #fff;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 3px 12px;
    border-radius: 9999px;
    margin-bottom: 10px;
}
.fw-selected-badge {
    display: inline-block;
    background: linear-gradient(90deg, #16a34a, #15803d);
    color: #fff;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 3px 12px;
    border-radius: 9999px;
    margin-left: 8px;
    margin-bottom: 10px;
}
.fw-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #c4b5fd;
    margin: 6px 0 10px 0;
}
.fw-angle {
    font-size: 0.87rem;
    color: #94a3b8;
    font-style: italic;
    margin-bottom: 14px;
    line-height: 1.6;
}
.arc-row {
    display: flex;
    align-items: center;
    gap: 0;
    margin: 12px 0;
}
.arc-box {
    flex: 1;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 0.78rem;
    color: #94a3b8;
    text-align: center;
}
.arc-box b { color: #e2e8f0; display: block; margin-bottom: 4px; font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase; }
.arc-arrow {
    font-size: 1.2rem;
    color: #7c3aed;
    padding: 0 6px;
    flex-shrink: 0;
}
.ch-chip {
    display: inline-block;
    background: #1e3a5f;
    color: #93c5fd;
    border: 1px solid #2563eb;
    border-radius: 8px;
    padding: 3px 9px;
    font-size: 0.72rem;
    margin: 3px 3px 0 0;
}
.concept-tag {
    display: inline-block;
    background: #312e81;
    color: #a5b4fc;
    border-radius: 9999px;
    padding: 2px 9px;
    font-size: 0.68rem;
    margin: 2px 2px 0 0;
}
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

if "outline_preview" not in st.session_state:
    st.session_state.outline_preview = None   # stores last parsed preview dict

if "frameworks" not in st.session_state:
    st.session_state.frameworks = []         # last generated frameworks

if "selected_fw_id" not in st.session_state:
    st.session_state.selected_fw_id = None  # currently selected framework_id

if "fw_generating" not in st.session_state:
    st.session_state.fw_generating = False


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

    # ── Author Guidelines / Description ───────────────────────────────────────
    with st.expander("📝 Author Guidelines (optional)", expanded=False):
        st.caption(
            "Provide instructions the AI should follow when using your documents — "
            "e.g. tone, scope, topics to avoid, preferred terminology, writing style."
        )
        author_description = st.text_area(
            "Guidelines",
            height=140,
            placeholder=(
                "e.g.\n"
                "• Write in a conversational yet authoritative tone.\n"
                "• Avoid jargon unless defined in context.\n"
                "• Focus on practical, real-world applications.\n"
                "• Do not include competitor product names."
            ),
            label_visibility="collapsed",
            key="author_description_input",
        )

    author_btn = st.button("⬆️  Ingest Author Docs", disabled=not author_uploaded, key="author_ingest_btn")
    if author_btn and author_uploaded:
        file_objs = [("files", (f.name, f.getvalue(), f.type or "application/octet-stream")) for f in author_uploaded]
        # Pass description as a form field alongside files
        form_data = {}
        desc_text = st.session_state.get("author_description_input", "").strip()
        if desc_text:
            form_data["description"] = desc_text
        try:
            with st.spinner("⏳ Ingesting author documents…"):
                resp = requests.post(
                    AUTHOR_DOCS_ENDPOINT,
                    files=file_objs,
                    data=form_data,
                    timeout=600,
                )
                resp.raise_for_status()
                data = resp.json()
            for r in data.get("details", []):
                if r.get("status") == "success":
                    st.session_state.author_uploaded_files.append({
                        "name": r["filename"], "status": "ok",
                        "chunks": r.get("chunks_stored", "?"),
                        "description_attached": r.get("description_attached", False),
                    })
                else:
                    st.session_state.author_uploaded_files.append({"name": r["filename"], "status": "error", "reason": r.get("reason", "")})
            if data.get("description_saved"):
                st.success("✅ Author guidelines saved and attached to chunks.")
        except Exception as e:
            st.error(f"❌ Author upload error: {e}")
    if st.session_state.author_uploaded_files:
        for f in st.session_state.author_uploaded_files:
            if f["status"] == "ok":
                guide_icon = " 📝" if f.get("description_attached") else ""
                st.markdown(
                    f'<div class="file-pill file-pill-ok">✍️ {f["name"]}{guide_icon}'
                    f' &nbsp;<span style="opacity:.6">({f["chunks"]} chunks)</span></div>',
                    unsafe_allow_html=True,
                )
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
tab_rag, tab_competitor, tab_outline, tab_framework = st.tabs([
    "🧠 RAG Assistant", "🔬 Market & Research Analysis", "📋 Chapter Outline", "🏗️ Framework Generator"
])


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
# TAB 2 - MARKET & RESEARCH ANALYSIS
# ==============================================================================
with tab_competitor:
    st.markdown(
        '<h1 style="color:#a78bfa;font-size:1.8rem;margin-bottom:0">🔬 Market & Research Analysis</h1>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Upload books, research papers, industry reports, or whitepapers. "
        "The AI extracts insights, frameworks, trends, and evidence — "
        "which are then used to ground your book generation."
    )
    st.divider()

    # ── Document type options ────────────────────────────────────────────────
    _DOC_TYPE_OPTIONS = {
        "📚 Book":             "book",
        "🔬 Research Paper":  "research_paper",
        "📊 Industry Report": "industry_report",
        "📄 Whitepaper":      "whitepaper",
    }
    _DOC_TYPE_DESCRIPTIONS = {
        "book":            "Extracts chapter structures, writing frameworks, style patterns, and competitive positioning.",
        "research_paper":  "Extracts key findings, statistics, evidence, citations, and research trends.",
        "industry_report": "Extracts market trends, opportunities, challenges, and future outlook.",
        "whitepaper":      "Extracts models, methodologies, strategic frameworks, and recommendations.",
    }

    # ── Upload form ──────────────────────────────────────────────────────────
    with st.form(key="market_form", clear_on_submit=False):
        market_files = st.file_uploader(
            "Upload documents (PDF, DOCX, TXT — up to 10 files)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="market_uploader",
        )
        col_dtype, col_mode, col_btn2 = st.columns([3, 2, 1])
        with col_dtype:
            doc_type_label = st.selectbox(
                "Document Type",
                options=list(_DOC_TYPE_OPTIONS.keys()),
                index=0,
                help="Selects the analysis pipeline to apply to uploaded files.",
                key="market_doc_type",
            )
        with col_mode:
            market_mode = st.selectbox(
                "Analysis Mode",
                options=["replace", "merge"],
                index=0,
                help="'replace' clears previous data; 'merge' appends.",
                key="market_mode",
            )
        with col_btn2:
            market_submit = st.form_submit_button("▶ Analyze", use_container_width=True)

    selected_doc_type = _DOC_TYPE_OPTIONS[doc_type_label]
    st.caption(f"ℹ️ **{doc_type_label}** — {_DOC_TYPE_DESCRIPTIONS[selected_doc_type]}")

    if market_submit:
        if not market_files:
            st.error("Please upload at least one document.")
        elif len(market_files) > 10:
            st.error(f"Maximum 10 files allowed. You selected {len(market_files)}.")
        else:
            file_objs = [
                ("files", (f.name, f.getvalue(), f.type or "application/octet-stream"))
                for f in market_files
            ]
            try:
                resp = requests.post(
                    MARKET_ENDPOINT,
                    files=file_objs,
                    params={"mode": market_mode, "document_type": selected_doc_type},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                st.session_state.competitor_job_id = data["job_id"]
                st.session_state.competitor_result = None
                if "warning" in data:
                    st.warning(data["warning"])
                dtype_display = selected_doc_type.replace("_", " ").title()
                st.success(
                    f"✅ Job submitted! ID: `{data['job_id']}` · "
                    f"Document type: **{dtype_display}**"
                )
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend.")
            except Exception as e:
                st.error(f"Error: {e}")

    # ── Job polling ──────────────────────────────────────────────────────────
    job_id = st.session_state.competitor_job_id
    if job_id and st.session_state.competitor_result is None:
        try:
            status_resp = requests.get(f"{MARKET_ENDPOINT}/status/{job_id}", timeout=10)
            if status_resp.status_code == 200:
                job_data   = status_resp.json()
                job_status = job_data.get("status", "unknown")
                prog_map   = {"pending": 0.05, "processing": 0.5, "completed": 1.0, "failed": 1.0}
                dt_label   = job_data.get("document_type", "book").replace("_", " ").title()
                st.progress(
                    prog_map.get(job_status, 0.1),
                    text=f"Status: {job_status.upper()} · {dt_label}",
                )
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

    # ── Load cached result if no active job ──────────────────────────────────
    result_c = st.session_state.competitor_result
    if result_c is None and job_id is None:
        try:
            cr = requests.get(f"{MARKET_ENDPOINT}/latest", timeout=5)
            if cr.status_code == 200:
                result_c = cr.json()
        except Exception:
            pass

    # ── Display results ───────────────────────────────────────────────────────
    if result_c:
        st.divider()
        docs_list     = result_c.get("documents_analyzed") or result_c.get("books_analyzed", [])
        res_dtype     = result_c.get("document_type", "book").replace("_", " ").title()
        chunks_stored = result_c.get("chunks_stored", 0)
        st.markdown(
            f'<div class="metric-card" style="border-color:#7c3aed">'
            f'📊 <b>Documents:</b> {len(docs_list)} &nbsp;'
            f'<b>Type:</b> {res_dtype} &nbsp;'
            f'<b>Mode:</b> {result_c.get("mode", "replace")} &nbsp;'
            f'<b>Chunks:</b> {chunks_stored}</div>',
            unsafe_allow_html=True,
        )

        # ── Aggregated cross-document insights ────────────────────────────────
        st.markdown("#### 🔍 Aggregated Insights")
        col_p, col_s, col_d = st.columns(3)
        with col_p:
            with st.expander("📝 Patterns", expanded=True):
                for p in result_c.get("patterns", []):
                    st.markdown(f"- {p}")
                if not result_c.get("patterns"):
                    st.caption("None extracted.")
        with col_s:
            with st.expander("🏗️ Common Structures", expanded=True):
                for s in result_c.get("common_structures", []):
                    st.markdown(f"- {s}")
                if not result_c.get("common_structures"):
                    st.caption("None extracted.")
        with col_d:
            with st.expander("💡 Differentiators", expanded=True):
                for d in result_c.get("differentiators", []):
                    st.markdown(f"- {d}")
                if not result_c.get("differentiators"):
                    st.caption("None extracted.")

        key_trends   = result_c.get("key_trends", result_c.get("trends", []))
        key_insights = result_c.get("key_insights", [])
        if key_trends or key_insights:
            col_t, col_i = st.columns(2)
            with col_t:
                with st.expander("📈 Key Trends", expanded=True):
                    for t in key_trends:
                        st.markdown(f"- {t}")
                    if not key_trends:
                        st.caption("None extracted.")
            with col_i:
                with st.expander("🎯 Key Insights", expanded=True):
                    for ins in key_insights:
                        st.markdown(f"- {ins}")
                    if not key_insights:
                        st.caption("None extracted.")

        # ── Per-document details ──────────────────────────────────────────────
        st.markdown("#### 📄 Document Details")
        doc_details = result_c.get("document_details") or result_c.get("book_details", [])
        for bd in doc_details:
            bd_dtype = bd.get("document_type", "book")
            dtype_icon = {
                "book":            "📚",
                "research_paper":  "🔬",
                "industry_report": "📊",
                "whitepaper":      "📄",
            }.get(bd_dtype, "📄")
            dtype_badge = bd_dtype.replace("_", " ").title()
            with st.expander(
                f"{dtype_icon} {bd.get('source', '?')}  [{dtype_badge}]  "
                f"({bd.get('page_count', '?')} pages)"
            ):
                st.write(f"**Summary:** {bd.get('summary', '')}")

                if bd.get("insights"):
                    st.markdown("**Key Insights:**")
                    for ins in bd["insights"]:
                        st.markdown(f"  - {ins}")

                if bd.get("frameworks"):
                    st.markdown("**Frameworks / Models:**")
                    fw = bd["frameworks"]
                    items = fw if isinstance(fw, list) else [x for x in fw.splitlines() if x.strip()]
                    for f_item in items:
                        st.markdown(f"  - {str(f_item).strip('- •*').strip()}")

                if bd.get("trends"):
                    st.markdown("**Trends:**")
                    for t in bd["trends"]:
                        st.markdown(f"  - {t}")

                if bd.get("evidence"):
                    st.markdown("**Evidence / Data Points:**")
                    for ev in bd["evidence"]:
                        st.markdown(f"  - {ev}")

                if bd.get("statistics"):
                    st.markdown("**Statistics:**")
                    for stat in bd["statistics"]:
                        st.markdown(f"  - {stat}")

                if bd.get("chapter_structure"):
                    st.markdown("**Chapter Structure:**")
                    for h in bd["chapter_structure"]:
                        st.markdown(f"  - {h}")

                if bd.get("opportunities") or bd.get("challenges"):
                    col_opp, col_chl = st.columns(2)
                    with col_opp:
                        st.markdown("**Opportunities:**")
                        for o in bd.get("opportunities", []):
                            st.markdown(f"  - {o}")
                    with col_chl:
                        st.markdown("**Challenges:**")
                        for c in bd.get("challenges", []):
                            st.markdown(f"  - {c}")

                if bd.get("recommendations"):
                    st.markdown("**Recommendations:**")
                    for r in bd["recommendations"]:
                        st.markdown(f"  - {r}")

                if bd.get("methodologies"):
                    st.markdown("**Methodologies:**")
                    for m in bd["methodologies"]:
                        st.markdown(f"  - {m}")

        col_reset, _ = st.columns([1, 3])
        with col_reset:
            if st.button("🗑 Reset Analysis", key="reset_competitor"):
                st.session_state.competitor_job_id = None
                st.session_state.competitor_result = None
                st.rerun()
    elif job_id is None:
        st.info(
            "No analysis yet. Upload documents above, choose a document type, and click Analyze."
        )


# ==============================================================================
# TAB 3 - CHAPTER OUTLINE
# ==============================================================================
with tab_outline:
    st.markdown('<h1 style="color:#a78bfa;font-size:1.8rem;margin-bottom:0">📋 Chapter Outline</h1>', unsafe_allow_html=True)
    st.caption(
        "Paste your chapter outline as plain text. "
        "When set, the LLM strictly follows the chapter and section order in every generation."
    )
    st.divider()

    # ── Load current active outline ──────────────────────────────────────────
    try:
        cur_resp = requests.get(OUTLINE_ENDPOINT, timeout=5)
        cur_outline = cur_resp.json() if cur_resp.status_code == 200 else None
    except Exception:
        cur_outline = None

    if cur_outline:
        chapters_cur = cur_outline.get("chapters", [])
        meta_cur     = cur_outline.get("metadata", {})
        created_at   = meta_cur.get("created_at", "")
        created_str  = f" · saved {created_at[:10]}" if created_at else ""
        st.markdown(
            f'<div class="metric-card" style="border-color:#7c3aed">'
            f'📋 <b>Active outline:</b> <span style="color:#a78bfa">{len(chapters_cur)} chapter(s)</span>'
            f'<span style="opacity:.55;font-size:.8em">{created_str}</span></div>',
            unsafe_allow_html=True,
        )
        st.session_state.outline_active = True

        # Show original text if stored, else render structured
        original_text_cur = cur_outline.get("original_text") or ""
        with st.expander("📖 View Active Outline", expanded=False):
            if original_text_cur:
                st.text(original_text_cur)
            else:
                for i, ch in enumerate(chapters_cur, 1):
                    st.markdown(f"**Chapter {i}: {ch['title']}**")
                    for sec in ch.get("sections", []):
                        desc = f" — {sec['description']}" if sec.get("description") else ""
                        st.markdown(f"&nbsp;&nbsp;• {sec['title']}{desc}")
    else:
        st.session_state.outline_active = False
        st.info(
            "No chapter outline set. "
            "The LLM will generate chapter structure dynamically."
        )

    st.divider()

    # ── Plain-text outline input ─────────────────────────────────────────────
    st.markdown("**Chapter Outline**")
    _OUTLINE_PLACEHOLDER = (
        "Paste your chapter outline here...\n\n"
        "Chapter 1: Why You Can't Focus\n"
        "* The myth of laziness\n"
        "* Digital distractions\n"
        "* Attention vs time\n\n"
        "Chapter 2: Understanding Attention\n"
        "* Deep work\n"
        "* Focus systems\n"
        "* Attention recovery"
    )
    outline_text_input = st.text_area(
        "Outline text",
        height=300,
        placeholder=_OUTLINE_PLACEHOLDER,
        key="outline_text_input",
        label_visibility="collapsed",
        help="Supports: 'Chapter N: Title', '1. Title', or bare headings followed by bullet points.",
    )

    col_prev, col_sub, col_clr = st.columns([2, 2, 1])
    with col_prev:
        preview_btn = st.button("🔍 Parse Preview", use_container_width=True, key="preview_outline_btn",
                                help="Parse your text and show the hierarchy — nothing is saved.")
    with col_sub:
        submit_outline = st.button("💾 Save Outline", use_container_width=True, key="save_outline_btn")
    with col_clr:
        clear_outline = st.button(
            "🗑 Clear", use_container_width=True,
            disabled=not cur_outline, key="clear_outline_btn",
        )

    # ── Parse Preview ────────────────────────────────────────────────────────
    if preview_btn:
        txt = outline_text_input.strip()
        if not txt:
            st.error("Please paste some outline text first.")
        else:
            try:
                resp = requests.post(
                    OUTLINE_PREVIEW_ENDPOINT,
                    json={"outline_text": txt},
                    timeout=15,
                )
                if resp.status_code == 200:
                    st.session_state.outline_preview = resp.json()
                elif resp.status_code == 422:
                    errs = resp.json().get("detail", {}).get("errors", [])
                    st.error("Could not parse outline:\n" + "\n".join(f"• {e}" for e in errs))
                    st.session_state.outline_preview = None
                else:
                    st.error(f"Preview error ({resp.status_code}): {resp.text}")
                    st.session_state.outline_preview = None
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend.")
            except Exception as exc:
                st.error(f"Preview error: {exc}")

    # Render preview results
    if st.session_state.outline_preview:
        prev = st.session_state.outline_preview
        prev_chapters = prev.get("chapters", [])
        prev_warnings = prev.get("warnings", [])
        st.markdown(
            f'<div class="metric-card" style="border-color:#22c55e">'
            f'✅ <b>Parsed {len(prev_chapters)} chapter(s)</b> — review below, then click Save Outline.</div>',
            unsafe_allow_html=True,
        )
        if prev_warnings:
            for w in prev_warnings:
                st.warning(w)
        with st.expander("📋 Parsed Structure Preview", expanded=True):
            for i, ch in enumerate(prev_chapters, 1):
                secs = ch.get("sections", [])
                sec_count = f" ({len(secs)} section{'s' if len(secs) != 1 else ''})"
                st.markdown(
                    f'<span style="color:#a78bfa;font-weight:700">Chapter {i}: {ch["title"]}</span>'
                    f'<span style="color:#475569;font-size:.8em">{sec_count}</span>',
                    unsafe_allow_html=True,
                )
                for sec in secs:
                    desc = f" — {sec['description']}" if sec.get("description") else ""
                    st.markdown(
                        f'&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#60a5fa">•</span> {sec["title"]}{desc}',
                        unsafe_allow_html=True,
                    )
                st.markdown("")

    # ── Save ─────────────────────────────────────────────────────────────────
    if submit_outline:
        txt = outline_text_input.strip()
        if not txt:
            st.error("Please paste a chapter outline.")
        else:
            try:
                with st.spinner("⏳ Parsing and saving chapter outline…"):
                    resp = requests.post(
                        OUTLINE_ENDPOINT,
                        json={"outline_text": txt},
                        timeout=60,
                    )
                if resp.status_code == 201:
                    data = resp.json()
                    st.success(
                        f"✅ Outline saved! {data.get('chapters_count','?')} chapter(s) stored."
                    )
                    if data.get("warnings"):
                        for w in data["warnings"]:
                            st.warning(w)
                    st.session_state.outline_active = True
                    st.session_state.outline_preview = None
                    st.rerun()
                elif resp.status_code == 400:
                    st.error(f"Validation error: {resp.json().get('detail', resp.text)}")
                else:
                    st.error(f"Save failed ({resp.status_code}): {resp.text}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend.")
            except Exception as exc:
                st.error(f"Error: {exc}")

    # ── Clear ─────────────────────────────────────────────────────────────────
    if clear_outline:
        try:
            with st.spinner("Clearing chapter outline..."):
                resp = requests.delete(OUTLINE_ENDPOINT, timeout=10)
            if resp.status_code in (200, 204):
                st.success("Chapter outline cleared.")
                st.session_state.outline_active = False
                st.session_state.outline_preview = None
                st.rerun()
            else:
                st.error(f"Failed to clear outline: {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")
        except Exception as exc:
            st.error(f"Error: {exc}")


# ==============================================================================
# TAB 4 — FRAMEWORK GENERATOR AGENT
# ==============================================================================
with tab_framework:
    st.markdown(
        '<h1 style="color:#a78bfa;font-size:1.8rem;margin-bottom:0">🏗️ Framework Generator Agent</h1>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Generates 3 distinct book frameworks using your Book Context, "
        "Competitor Analysis & RAG knowledge base. Each framework includes "
        "a chapter breakdown, reader transformation arc, and unique angle."
    )
    st.divider()

    # ── Helper functions ──────────────────────────────────────────────────────

    def _call_generate_frameworks(override_ctx=None, override_comp=None, override_docs=None):
        payload = {}
        if override_ctx:
            payload["book_context"] = override_ctx
        if override_comp:
            payload["competitor_analysis"] = override_comp
        if override_docs:
            payload["retrieved_docs"] = override_docs
        try:
            resp = requests.post(
                FRAMEWORK_ENDPOINT,
                json={**payload, "force_regenerate": True},
                timeout=300,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            return {"error": "Cannot connect to backend. Is FastAPI running on port 8000?"}
        except requests.exceptions.Timeout:
            return {"error": "Request timed out (>5 min). The LLM may be slow — try again."}
        except requests.exceptions.HTTPError as e:
            return {"error": f"Backend error: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}

    def _call_select_framework(fw_id: str):
        try:
            resp = requests.post(SELECT_FW_ENDPOINT, json={"framework_id": fw_id}, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            return {"error": "Cannot connect to backend."}
        except requests.exceptions.HTTPError as e:
            return {"error": f"Backend error: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}

    def _load_selected_fw():
        try:
            resp = requests.get(SELECTED_FW_ENDPOINT, timeout=5)
            if resp.status_code == 200:
                return resp.json().get("framework")
        except Exception:
            pass
        return None

    def _load_active_frameworks():
        try:
            resp = requests.get(FRAMEWORKS_ENDPOINT, timeout=5)
            if resp.status_code == 200:
                return resp.json().get("frameworks", [])
        except Exception:
            pass
        return []

    def _render_framework_card(fw: dict, is_selected: bool, idx: int):
        """Render a single framework card with transformation arc & chapter list."""
        badge_html = f'<span class="fw-badge">Framework {chr(65+idx)}</span>'
        if is_selected:
            badge_html += '<span class="fw-selected-badge">✓ Selected</span>'

        card_class = "fw-card selected-card" if is_selected else "fw-card"
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        st.markdown(badge_html, unsafe_allow_html=True)
        st.markdown(f'<div class="fw-title">{fw.get("name", "Unnamed Framework")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="fw-angle">💡 {fw.get("unique_angle", "No angle provided.")}</div>',
            unsafe_allow_html=True,
        )

        # Transformation Arc
        fot = fw.get("flow_of_transformation", {})
        before  = fot.get("before", "—")
        journey = fot.get("journey", "—")
        after   = fot.get("after", "—")
        st.markdown(
            f"""
            <div class="arc-row">
                <div class="arc-box"><b>Before</b>{before}</div>
                <div class="arc-arrow">➜</div>
                <div class="arc-box" style="flex:2;font-size:0.75rem;"><b>Journey</b>{journey}</div>
                <div class="arc-arrow">➜</div>
                <div class="arc-box"><b>After</b>{after}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # Chapter Breakdown (collapsible)
        chapters = fw.get("chapter_breakdown", [])
        if chapters:
            with st.expander(f"📚 {len(chapters)} Chapters — expand to view", expanded=False):
                for ch in chapters:
                    num = ch.get("number", "?")
                    title = ch.get("title", "Untitled")
                    purpose = ch.get("purpose", "")
                    concepts = ch.get("key_concepts", [])
                    st.markdown(
                        f'<span class="ch-chip">Ch {num}</span> <b>{title}</b>',
                        unsafe_allow_html=True,
                    )
                    if purpose:
                        st.caption(purpose)
                    if concepts:
                        tags = "".join(
                            f'<span class="concept-tag">{c}</span>' for c in concepts
                        )
                        st.markdown(tags, unsafe_allow_html=True)
                    st.divider()

    # ── Load persisted selected framework on startup ───────────────────────────
    if st.session_state.selected_fw_id is None:
        persisted = _load_selected_fw()
        if persisted:
            st.session_state.selected_fw_id = persisted.get("framework_id")

    # Load active frameworks from backend if session state is empty
    if not st.session_state.frameworks:
        st.session_state.frameworks = _load_active_frameworks()

    # ── Status banner ─────────────────────────────────────────────────────────
    sel_id = st.session_state.selected_fw_id
    if sel_id:
        # Find the selected framework name from loaded frameworks
        sel_fw = next(
            (f for f in st.session_state.frameworks if f.get("framework_id") == sel_id),
            None,
        )
        name_display = sel_fw["name"] if sel_fw else sel_id
        st.markdown(
            f'<div class="metric-card" style="border-color:#16a34a">'
            f'🏗️ <b>Active framework:</b> <span style="color:#86efac">{name_display}</span>'
            f' <span style="color:#4ade80;font-size:0.75rem">— injected into generation pipeline</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card">🏗️ <b>No framework selected</b> — generate and select one below</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Controls — Generate ───────────────────────────────────────────────────
    st.markdown("### ⚡ Generate Frameworks")
    st.caption(
        "The agent automatically pulls your Book Context and Competitor Analysis from the backend. "
        "Optionally override them below, or leave blank to use stored data."
    )

    with st.expander("🔧 Optional: Override Inputs", expanded=False):
        st.markdown("**Book Context Override** *(leave blank to use stored context)*")
        col_ov1, col_ov2 = st.columns(2)
        with col_ov1:
            ov_title    = st.text_input("Title", placeholder="e.g. Mastering RAG", key="fw_ov_title")
            ov_audience = st.text_input("Target Audience", placeholder="e.g. ML engineers", key="fw_ov_audience")
            ov_objective= st.text_area("Author Objective", placeholder="What the author wants to achieve", height=70, key="fw_ov_obj")
        with col_ov2:
            ov_before   = st.text_input("Reader Before", placeholder="e.g. Knows Python basics", key="fw_ov_before")
            ov_after    = st.text_input("Reader After", placeholder="e.g. Can deploy ML pipelines", key="fw_ov_after")
            ov_tone     = st.text_input("Tone & Style", placeholder="e.g. Practical and direct", key="fw_ov_tone")

        st.markdown("**Competitor Analysis Override** *(leave blank to use cached analysis)*")
        ov_patterns = st.text_area(
            "Patterns (one per line)",
            placeholder="e.g. Most books start with theory then move to practice",
            height=70, key="fw_ov_patterns",
        )
        ov_structures = st.text_area(
            "Common Structures (one per line)",
            placeholder="e.g. 12-chapter format with exercises at end of each chapter",
            height=70, key="fw_ov_structures",
        )
        ov_differentiators = st.text_area(
            "Differentiators (one per line)",
            placeholder="e.g. Book X uses a project-first approach",
            height=70, key="fw_ov_diff",
        )

    col_gen, col_refresh = st.columns([3, 1])
    with col_gen:
        generate_btn = st.button(
            "🏗️ Generate 3 Frameworks",
            use_container_width=True,
            key="generate_fw_btn",
            type="primary",
        )
    with col_refresh:
        refresh_btn = st.button(
            "🔄 Reload",
            use_container_width=True,
            key="refresh_fw_btn",
            help="Reload frameworks from the backend session",
        )

    if refresh_btn:
        reloaded = _load_active_frameworks()
        if reloaded:
            st.session_state.frameworks = reloaded
            st.success(f"Reloaded {len(reloaded)} frameworks from backend.")
            st.rerun()
        else:
            st.info("No frameworks found in backend session. Click Generate first.")

    if generate_btn:
        # Build optional overrides
        override_ctx = None
        if ov_title.strip() and ov_audience.strip():
            override_ctx = {
                "title":            ov_title.strip(),
                "target_audience":  ov_audience.strip(),
                "author_objective": ov_objective.strip() or None,
                "initial_state":    ov_before.strip() or None,
                "final_state":      ov_after.strip() or None,
                "tone":             ov_tone.strip() or None,
            }

        override_comp = None
        if ov_patterns.strip() or ov_structures.strip() or ov_differentiators.strip():
            override_comp = {
                "patterns":          [l.strip() for l in ov_patterns.splitlines() if l.strip()],
                "common_structures": [l.strip() for l in ov_structures.splitlines() if l.strip()],
                "differentiators":   [l.strip() for l in ov_differentiators.splitlines() if l.strip()],
            }

        with st.spinner(
            "🤖 Agent is synthesising 3 book frameworks…  "
            "*(This uses the LLM — may take 1-3 minutes)*"
        ):
            result = _call_generate_frameworks(
                override_ctx=override_ctx,
                override_comp=override_comp,
            )

        if "error" in result:
            st.error(f"❌ {result['error']}")
        else:
            frameworks = result.get("frameworks", [])
            st.session_state.frameworks = frameworks
            st.success(f"✅ Generated {len(frameworks)} frameworks!")
            st.rerun()

    # ── Display Frameworks ────────────────────────────────────────────────────
    st.divider()

    frameworks = st.session_state.frameworks
    if not frameworks:
        st.markdown(
            '<div class="empty-state">'
            '<div class="icon">🏗️</div>'
            '<div style="color:#94a3b8;font-size:1rem;font-weight:600">No frameworks generated yet</div>'
            '<div class="hint">Click <b>Generate 3 Frameworks</b> above to get started.<br>'
            'Make sure you have a Book Context set in the sidebar.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"### 📐 {len(frameworks)} Generated Frameworks")
        st.caption("Review each framework below and select the one that best fits your vision.")

        for idx, fw in enumerate(frameworks):
            fw_id = fw.get("framework_id", f"framework_{chr(97+idx)}")
            is_selected = (fw_id == st.session_state.selected_fw_id)

            # Render the card
            _render_framework_card(fw, is_selected, idx)

            # Select button
            btn_label = "✓ Selected" if is_selected else f"Select Framework {chr(65+idx)}"
            btn_type  = "secondary" if is_selected else "primary"
            if st.button(
                btn_label,
                key=f"select_fw_{fw_id}",
                use_container_width=True,
                type=btn_type,
                disabled=is_selected,
            ):
                with st.spinner(f"Selecting '{fw.get('name', fw_id)}'…"):
                    sel_result = _call_select_framework(fw_id)
                if "error" in sel_result:
                    st.error(f"❌ {sel_result['error']}")
                else:
                    st.session_state.selected_fw_id = fw_id
                    st.success(
                        f"✅ Framework '{fw.get('name', fw_id)}' selected and saved! "
                        "It will be used in all future book generation."
                    )
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

        # ── Selected Framework Detail Panel ───────────────────────────────────
        if st.session_state.selected_fw_id:
            st.divider()
            sel_fw = next(
                (f for f in frameworks if f.get("framework_id") == st.session_state.selected_fw_id),
                None,
            )
            if sel_fw:
                st.markdown("### 📌 Selected Framework Detail")
                cols_meta = st.columns(3)
                fot = sel_fw.get("flow_of_transformation", {})
                with cols_meta[0]:
                    st.markdown("**📍 Before**")
                    st.info(fot.get("before", "—"))
                with cols_meta[1]:
                    st.markdown("**🔄 Journey**")
                    st.info(fot.get("journey", "—"))
                with cols_meta[2]:
                    st.markdown("**🏁 After**")
                    st.info(fot.get("after", "—"))

                st.markdown("**📚 Full Chapter Breakdown**")
                chapters = sel_fw.get("chapter_breakdown", [])
                if chapters:
                    for ch in chapters:
                        with st.expander(
                            f"Chapter {ch.get('number','?')}: {ch.get('title','Untitled')}",
                            expanded=False,
                        ):
                            if ch.get("purpose"):
                                st.markdown(f"**Purpose:** {ch['purpose']}")
                            if ch.get("key_concepts"):
                                st.markdown("**Key Concepts:**")
                                tags = "".join(
                                    f'<span class="concept-tag">{c}</span>'
                                    for c in ch["key_concepts"]
                                )
                                st.markdown(tags, unsafe_allow_html=True)
                else:
                    st.caption("No chapters defined.")
