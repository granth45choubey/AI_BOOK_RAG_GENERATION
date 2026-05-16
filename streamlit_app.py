"""
Author Studio — Streamlit UI for AI_BOOK_RAG_GENERATION.
"""

import json
from datetime import datetime

import requests
import streamlit as st


st.set_page_config(
    page_title="Author Studio",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


BACKEND_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{BACKEND_URL}/upload-documents"
QUERY_ENDPOINT = f"{BACKEND_URL}/query"
BOOK_CONTEXT_ENDPOINT = f"{BACKEND_URL}/create-book-context"
COMPETITOR_ENDPOINT = f"{BACKEND_URL}/analyze-competitors"
AUTHOR_DOCS_ENDPOINT = f"{BACKEND_URL}/upload-author-documents"
OUTLINE_ENDPOINT = f"{BACKEND_URL}/set-chapter-outline"
OUTLINE_PREFILL_URL = f"{OUTLINE_ENDPOINT}/prefill"
TEMPLATES_ENDPOINT = f"{BACKEND_URL}/templates"
TEMPLATE_SELECT_URL = f"{BACKEND_URL}/templates/select"
TEMPLATE_SELECTED_URL = f"{BACKEND_URL}/templates/selected"
DRAFT_EXPORT_ENDPOINT = f"{BACKEND_URL}/drafts/export"
DRAFT_LIST_ENDPOINT = f"{BACKEND_URL}/drafts"
ORCHESTRATE_BLUEPRINT_URL = f"{BACKEND_URL}/orchestrate/auto-blueprint"
ORCHESTRATE_DRAFT_URL = f"{BACKEND_URL}/orchestrate/draft-chapter"
ORIGINALITY_ENDPOINT = f"{BACKEND_URL}/originality-check"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_TAGS_ENDPOINT = f"{OLLAMA_URL}/api/tags"


WIZARD_STEPS = [
    ("setup", "Setup", "Tell the studio about your book."),
    ("knowledge", "Knowledge", "Bring in the sources you want to write from."),
    ("blueprint", "Blueprint", "Approve the chapter framework."),
    ("draft", "Draft", "Generate and approve each chapter."),
    ("review", "Review & Export", "Validate originality and export."),
]


LIGHT_TOKENS = {
    "bg": "#f1e9d8",
    "bg_grad_a": "#f5eedf",
    "bg_grad_b": "#ebe1ce",
    "panel": "#fffaf0",
    "panel_alt": "#f6ebd6",
    "border": "#d4c3a3",
    "border_strong": "#b39d76",
    "text": "#1c1814",
    "muted": "#5e503f",
    "accent": "#1f5e57",
    "accent_strong": "#164842",
    "accent_soft": "#cfe3df",
    "on_accent": "#ffffff",
    "ok": "#2f7a4a",
    "warn": "#b86426",
    "error": "#a8362a",
    "shadow": "0 1px 2px rgba(28,24,20,0.06), 0 8px 24px rgba(28,24,20,0.06)",
}

DARK_TOKENS = {
    "bg": "#1c1815",
    "bg_grad_a": "#221d18",
    "bg_grad_b": "#16120f",
    "panel": "#2b2520",
    "panel_alt": "#36302a",
    "border": "#4b4036",
    "border_strong": "#6b5a48",
    "text": "#f1e6d4",
    "muted": "#c2b29c",
    "accent": "#6ec1b6",
    "accent_strong": "#9fdcd2",
    "accent_soft": "#2b3f3d",
    "on_accent": "#0b1816",
    "ok": "#8ac49a",
    "warn": "#d6a969",
    "error": "#d68f86",
    "shadow": "0 1px 2px rgba(0,0,0,0.4), 0 12px 28px rgba(0,0,0,0.35)",
}


def _theme_css(t: dict) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
:root {{
    --bg: {t['bg']};
    --bg-a: {t['bg_grad_a']};
    --bg-b: {t['bg_grad_b']};
    --panel: {t['panel']};
    --panel-alt: {t['panel_alt']};
    --border: {t['border']};
    --border-strong: {t['border_strong']};
    --text: {t['text']};
    --muted: {t['muted']};
    --accent: {t['accent']};
    --accent-strong: {t['accent_strong']};
    --accent-soft: {t['accent_soft']};
    --on-accent: {t['on_accent']};
    --ok: {t['ok']};
    --warn: {t['warn']};
    --error: {t['error']};
    --shadow: {t['shadow']};
}}
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: var(--text); }}
.stApp {{
    background:
        radial-gradient(1200px 600px at 10% -10%, var(--bg-a) 0%, transparent 60%),
        radial-gradient(900px 500px at 95% 105%, var(--bg-b) 0%, transparent 55%),
        var(--bg);
    color: var(--text);
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1280px; }}
h1, h2, h3, h4 {{ font-family: 'Fraunces', serif; letter-spacing: 0.005em; color: var(--text); }}
h1 {{ font-weight: 700; }}
p, label, span, div {{ color: var(--text); }}
.stMarkdown p {{ color: var(--text); }}
small, .stCaption, [data-testid="stCaptionContainer"] {{ color: var(--muted) !important; }}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox div[role="button"],
.stNumberInput input, .stDateInput input {{
    background: var(--panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}}
.stTextArea textarea {{ min-height: 90px; }}
[data-baseweb="select"] > div {{ background: var(--panel) !important; color: var(--text) !important; border-color: var(--border) !important; }}
[data-baseweb="popover"] {{ background: var(--panel) !important; }}

/* Buttons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    padding: 0.5rem 0.95rem;
    font-weight: 600;
    transition: all 0.15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
    background: var(--panel-alt);
    border-color: var(--accent);
    color: var(--accent-strong);
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
    background: var(--accent);
    color: var(--on-accent);
    border-color: var(--accent);
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
    background: var(--accent-strong);
    color: var(--on-accent);
    border-color: var(--accent-strong);
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{ color: var(--muted); padding: 8px 14px; }}
.stTabs [aria-selected="true"] {{ color: var(--accent) !important; }}

/* Expanders, alerts */
[data-testid="stExpander"] {{ border: 1px solid var(--border); border-radius: 12px; background: var(--panel); }}
[data-testid="stExpander"] summary {{ color: var(--text); font-weight: 600; }}
[data-testid="stAlert"] {{ background: var(--panel-alt); color: var(--text); border-radius: 10px; }}

/* Studio primitives */
.studio-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: var(--shadow);
}}
.studio-soft {{
    background: var(--panel-alt);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 16px;
}}
.section-label {{
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 700;
    margin: 4px 0 10px 0;
}}
.meta-chip {{
    display: inline-block;
    border: 1px solid var(--border-strong);
    border-radius: 999px;
    padding: 3px 11px;
    margin: 2px 6px 2px 0;
    font-size: 0.74rem;
    background: var(--panel);
    color: var(--text);
    font-weight: 500;
}}
.chip-accent {{ background: var(--accent-soft); border-color: var(--accent); color: var(--accent-strong); }}
.chip-ok {{ background: rgba(47,122,74,0.10); border-color: var(--ok); color: var(--ok); }}
.chip-warn {{ background: rgba(184,100,38,0.10); border-color: var(--warn); color: var(--warn); }}
.chip-error {{ background: rgba(168,54,42,0.10); border-color: var(--error); color: var(--error); }}

/* Step rail */
.step-rail {{
    display: flex;
    gap: 8px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 14px 16px;
    box-shadow: var(--shadow);
    margin-bottom: 16px;
}}
.step-cell {{
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--panel-alt);
    border: 1px solid transparent;
    min-width: 0;
}}
.step-cell .step-num {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px; height: 26px;
    border-radius: 50%;
    background: var(--panel);
    border: 1px solid var(--border-strong);
    color: var(--muted);
    font-weight: 700;
    font-size: 0.82rem;
}}
.step-cell .step-name {{ font-family: 'Fraunces', serif; font-weight: 600; color: var(--text); }}
.step-cell .step-hint {{ font-size: 0.74rem; color: var(--muted); }}
.step-cell.done {{ background: var(--accent-soft); border-color: var(--accent); }}
.step-cell.done .step-num {{ background: var(--accent); color: var(--on-accent); border-color: var(--accent); }}
.step-cell.current {{ background: var(--panel); border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }}
.step-cell.current .step-num {{ background: var(--accent); color: var(--on-accent); border-color: var(--accent); }}

/* Topbar */
.topbar {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 12px;
    box-shadow: var(--shadow);
}}
.topbar .project-name {{ font-family: 'Fraunces', serif; font-size: 1.25rem; font-weight: 600; }}

/* Landing hero */
.hero {{
    background:
        linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%);
    color: var(--on-accent);
    border-radius: 24px;
    padding: 44px 40px;
    margin-bottom: 18px;
    box-shadow: var(--shadow);
}}
.hero h1 {{ color: var(--on-accent); font-size: 2.4rem; margin: 0 0 10px 0; }}
.hero p {{ color: var(--on-accent); opacity: 0.92; font-size: 1.05rem; max-width: 640px; }}

/* Writer messages */
.writer-message-user, .writer-message-ai {{
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 10px;
}}
.writer-message-user {{ background: var(--accent-soft); border-color: var(--accent); margin-left: 10%; }}
.writer-message-ai {{ background: var(--panel); margin-right: 10%; }}

/* Chapter card */
.chapter-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 12px;
    box-shadow: var(--shadow);
}}
.chapter-card.approved {{ border-left-color: var(--ok); }}
.chapter-card.pending {{ border-left-color: var(--warn); }}
.chapter-title {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.05rem; }}
</style>
"""


LIGHT_THEME = _theme_css(LIGHT_TOKENS)
DARK_THEME = _theme_css(DARK_TOKENS)


def _init_session():
    defaults = {
        # Wizard
        "wizard_step": 0,                # 0 = landing, 1..5 = wizard steps
        "intent_payload": {},            # last intent submitted
        "template_choice_mode": "auto",  # "auto" or "choose"
        "blueprint_chapters": [],        # cached outline chapters
        "blueprint_approved": False,
        "chapter_state": {},             # idx -> {draft, sources, originality, approved, history}
        "active_chapter_idx": 0,
        # Legacy / shared
        "uploaded_files": [],
        "author_uploaded_files": [],
        "book_context_title": "",
        "book_context_active": False,
        "selected_template_id": "",
        "top_k": 5,
        "source_filter": "",
        "ui_theme": "Light",
        "competitor_job_id": None,
        "competitor_result": None,
        # Review/export
        "review_originality": {},        # idx -> originality dict
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _go_to_step(idx: int):
    st.session_state.wizard_step = max(0, min(idx, len(WIZARD_STEPS)))


def _ensure_chapter_state(idx: int) -> dict:
    state = st.session_state.chapter_state
    if idx not in state:
        state[idx] = {
            "draft": "",
            "sources": [],
            "originality": None,
            "approved": False,
            "history": [],
        }
    return state[idx]


def _backend_status() -> dict:
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=3)
        response.raise_for_status()
        return {"online": True, "payload": response.json()}
    except requests.exceptions.RequestException as exc:
        return {"online": False, "error": str(exc)}


def _ollama_status() -> dict:
    try:
        response = requests.get(OLLAMA_TAGS_ENDPOINT, timeout=3)
        response.raise_for_status()
        models = [m.get("name") for m in response.json().get("models", []) if m.get("name")]
        return {"online": True, "models": models}
    except requests.exceptions.RequestException as exc:
        return {"online": False, "error": str(exc)}


def create_book_context(payload: dict) -> dict:
    try:
        response = requests.post(BOOK_CONTEXT_ENDPOINT, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend."}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"Backend error: {exc.response.text}"}
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def fetch_book_context() -> dict:
    try:
        response = requests.get(BOOK_CONTEXT_ENDPOINT, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {"active": False}


def fetch_templates() -> list[dict]:
    try:
        response = requests.get(TEMPLATES_ENDPOINT, timeout=10)
        response.raise_for_status()
        return response.json().get("templates", [])
    except requests.exceptions.RequestException:
        return []


def fetch_selected_template() -> dict:
    try:
        response = requests.get(TEMPLATE_SELECTED_URL, timeout=5)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def select_template(template_id: str, parameters: dict | None = None) -> dict:
    payload = {"template_id": template_id, "parameters": parameters or {}}
    try:
        response = requests.post(TEMPLATE_SELECT_URL, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def prefill_outline() -> dict:
    try:
        response = requests.get(OUTLINE_PREFILL_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def upload_files(files, endpoint: str) -> list[dict]:
    payload = [("files", (f.name, f.getvalue(), f.type or "application/octet-stream")) for f in files]
    try:
        response = requests.post(endpoint, files=payload, timeout=600)
        response.raise_for_status()
        return response.json().get("details", [])
    except requests.exceptions.Timeout:
        return [{"filename": f.name, "status": "error", "reason": "Request timed out for this file."} for f in files]
    except requests.exceptions.ConnectionError:
        return [{"filename": f.name, "status": "error", "reason": "Cannot connect to backend."} for f in files]
    except requests.exceptions.HTTPError as exc:
        return [{"filename": f.name, "status": "error", "reason": str(exc)} for f in files]
    except requests.exceptions.RequestException as exc:
        return [{"filename": f.name, "status": "error", "reason": str(exc)} for f in files]


def query_backend(question: str, top_k: int, source_filter: str) -> dict:
    payload = {"question": question, "top_k": top_k}
    if source_filter.strip():
        payload["source_filter"] = source_filter.strip()
    try:
        response = requests.post(QUERY_ENDPOINT, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. Start FastAPI on port 8000."}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"Backend error: {exc.response.text}"}
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def export_draft(title: str, chapters: list[dict]) -> dict:
    try:
        response = requests.post(DRAFT_EXPORT_ENDPOINT, json={"title": title, "chapters": chapters}, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def fetch_drafts() -> list[dict]:
    try:
        response = requests.get(DRAFT_LIST_ENDPOINT, timeout=10)
        response.raise_for_status()
        return response.json().get("drafts", [])
    except requests.exceptions.RequestException:
        return []


def fetch_draft(draft_id: str) -> dict:
    try:
        response = requests.get(f"{DRAFT_LIST_ENDPOINT}/{draft_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def delete_draft(draft_id: str) -> dict:
    try:
        response = requests.delete(f"{DRAFT_LIST_ENDPOINT}/{draft_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


# ── Orchestration / outline / originality helpers ────────────────────────────

def fetch_outline() -> dict:
    try:
        response = requests.get(OUTLINE_ENDPOINT, timeout=6)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def save_outline_chapters(chapters: list[dict]) -> dict:
    try:
        response = requests.post(OUTLINE_ENDPOINT, json={"chapters": chapters}, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def orchestrate_auto_blueprint(template_id: str | None, parameters: dict | None = None) -> dict:
    payload = {"template_id": template_id, "parameters": parameters or {}}
    try:
        response = requests.post(ORCHESTRATE_BLUEPRINT_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as exc:
        return {"error": f"Backend error: {exc.response.text}"}
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def orchestrate_draft_chapter(chapter_index: int, instructions: str = "") -> dict:
    payload = {"chapter_index": chapter_index}
    if instructions.strip():
        payload["instructions"] = instructions.strip()
    try:
        response = requests.post(ORCHESTRATE_DRAFT_URL, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as exc:
        return {"error": f"Backend error: {exc.response.text}"}
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def originality_check_text(text: str) -> dict:
    try:
        response = requests.post(ORIGINALITY_ENDPOINT, json={"text": text}, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


# ── Render helpers ───────────────────────────────────────────────────────────

def render_step_rail(current_step: int):
    if current_step <= 0:
        return
    cells = []
    for idx, (_key, name, hint) in enumerate(WIZARD_STEPS, 1):
        if idx < current_step:
            klass = "step-cell done"
        elif idx == current_step:
            klass = "step-cell current"
        else:
            klass = "step-cell"
        cells.append(
            f'<div class="{klass}">'
            f'<div><span class="step-num">{idx}</span></div>'
            f'<div class="step-name">{name}</div>'
            f'<div class="step-hint">{hint}</div>'
            f"</div>"
        )
    st.markdown(f'<div class="step-rail">{"".join(cells)}</div>', unsafe_allow_html=True)


def render_topbar(project_name: str, backend: dict, ollama: dict):
    left, right = st.columns([5, 2])
    with left:
        backend_chip = "chip-ok" if backend.get("online") else "chip-error"
        ollama_chip = "chip-ok" if ollama.get("online") else "chip-warn"
        st.markdown(
            f'<div class="topbar">'
            f'<div class="project-name">📖 {project_name}</div>'
            f'<div style="margin-top:6px;">'
            f'<span class="meta-chip chip-accent">GlobalBook Author Studio</span>'
            f'<span class="meta-chip {backend_chip}">Backend {"online" if backend.get("online") else "offline"}</span>'
            f'<span class="meta-chip {ollama_chip}">Ollama {"online" if ollama.get("online") else "offline"}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="topbar">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.ui_theme = st.selectbox(
                "Theme", ["Light", "Dark"],
                index=0 if st.session_state.ui_theme == "Light" else 1,
                label_visibility="collapsed",
            )
        with c2:
            if st.button("↺ Reset", use_container_width=True, help="Start a new project (clears local state)"):
                preserved_theme = st.session_state.ui_theme
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.session_state.ui_theme = preserved_theme
                st.rerun()
        st.caption(f"Saved · {datetime.now().strftime('%H:%M')}")
        st.markdown("</div>", unsafe_allow_html=True)


def render_landing(has_existing: bool, project_name: str):
    st.markdown(
        '<div class="hero">'
        '<h1>Welcome to GlobalBook Author Studio</h1>'
        '<p>A guided studio for turning your sources, voice, and intent into a polished '
        'manuscript. The AI does the heavy lifting; you stay in the editor\'s chair.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="studio-card">', unsafe_allow_html=True)
        st.markdown("### Start a new project")
        st.write(
            "Tell the studio about your book, drop in your sources, approve a blueprint, "
            "and draft chapter by chapter with full source traceability."
        )
        if st.button("Start project →", type="primary", use_container_width=True, key="landing_start"):
            _go_to_step(1)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="studio-card">', unsafe_allow_html=True)
        st.markdown("### Resume current project")
        if has_existing:
            st.write(f"You have an active project: **{project_name}**.")
            if st.button("Resume →", use_container_width=True, key="landing_resume"):
                # Jump to the furthest sensible step based on what's already done
                outline = fetch_outline()
                if outline.get("active") or outline.get("chapters"):
                    st.session_state.blueprint_chapters = outline.get("chapters", [])
                    _go_to_step(4)
                else:
                    _go_to_step(3)
                st.rerun()
        else:
            st.write("No active project yet — start a new one on the left.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="studio-soft" style="margin-top:8px;">', unsafe_allow_html=True)
    st.markdown(
        '**Five guided steps:** Setup → Knowledge → Blueprint → Draft → Review & Export. '
        "Each major output (blueprint, chapter draft) waits for your approval."
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_setup(templates: list[dict]):
    st.markdown("## 1 · Setup — editorial intent")
    st.caption("These answers shape the voice, audience, and structure of your book.")

    with st.form("intent_form"):
        title = st.text_input("Book title", placeholder="Your working manuscript title",
                              value=st.session_state.intent_payload.get("title", ""))
        c1, c2 = st.columns(2)
        with c1:
            book_kind = st.selectbox(
                "Book type",
                ["self-help", "business", "spiritual", "academic", "memoir", "fiction",
                 "educational", "children's", "other"],
            )
            book_kind_other = st.text_input("Other book type") if book_kind == "other" else ""
            audience = st.selectbox(
                "Audience",
                ["general readers", "students", "professionals", "executives",
                 "young adults", "researchers", "other"],
            )
            audience_other = st.text_input("Other audience") if audience == "other" else ""
        with c2:
            tone = st.selectbox(
                "Tone",
                ["warm", "reflective", "authoritative", "conversational",
                 "inspiring", "practical", "spiritual", "other"],
            )
            tone_other = st.text_input("Other tone") if tone == "other" else ""
            goal = st.selectbox(
                "Goal",
                ["inform", "persuade", "guide", "inspire", "entertain", "teach", "other"],
            )
            goal_other = st.text_input("Other goal") if goal == "other" else ""

        length = st.selectbox("Target length",
                              ["short draft", "medium draft", "full manuscript", "custom"])
        custom_length = st.text_input("Custom length target") if length == "custom" else ""

        st.markdown('<div class="section-label">Template preference</div>', unsafe_allow_html=True)
        template_choice = st.radio(
            "How should we pick the chapter framework?",
            ["Auto-choose a template for me", "Let me choose from options"],
            index=0 if st.session_state.template_choice_mode == "auto" else 1,
            horizontal=False,
        )

        submitted = st.form_submit_button("Save intent & continue →", type="primary",
                                          use_container_width=True)

    if not submitted:
        return

    if not title.strip():
        st.error("Book title is required.")
        return

    aud_v = audience_other.strip() if audience == "other" else audience
    tone_v = tone_other.strip() if tone == "other" else tone
    kind_v = book_kind_other.strip() if book_kind == "other" else book_kind
    goal_v = goal_other.strip() if goal == "other" else goal
    len_v = custom_length.strip() if length == "custom" else length

    payload = {
        "title": title.strip(),
        "target_audience": aud_v,
        "author_objective": goal_v,
        "reader_transformation": f"Deliver a {kind_v} manuscript in a {tone_v} voice.",
        "initial_state": f"Audience profile: {aud_v}",
        "final_state": f"Audience outcome: {goal_v}",
        "tone": f"{tone_v}; length target: {len_v}",
    }
    with st.spinner("Saving editorial intent..."):
        result = create_book_context(payload)
    if "error" in result:
        st.error(result["error"])
        return

    st.session_state.intent_payload = payload
    st.session_state.book_context_active = True
    st.session_state.book_context_title = payload["title"]
    st.session_state.template_choice_mode = (
        "auto" if template_choice.startswith("Auto") else "choose"
    )

    if st.session_state.template_choice_mode == "auto":
        st.success("Intent saved. We'll auto-build a blueprint in step 3.")
    else:
        st.success("Intent saved. Choose a template below, then continue.")

    st.rerun()


def render_setup_template_picker(templates: list[dict], selected_template: dict):
    """When intent is saved with 'choose' mode, present template options inline."""
    if st.session_state.template_choice_mode != "choose":
        return
    st.markdown('<div class="studio-soft" style="margin-top:12px;">', unsafe_allow_html=True)
    st.markdown("#### Choose a chapter framework")
    if not templates:
        st.warning("No templates available from the backend.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    options = {t["name"]: t for t in templates}
    active_id = selected_template.get("template_id", "")
    names = list(options.keys())
    default_idx = next(
        (i for i, n in enumerate(names) if options[n]["id"] == active_id), 0
    )
    selected_name = st.selectbox("Template", names, index=default_idx, key="setup_template_select")
    st.caption(options[selected_name].get("description", ""))
    audience = st.session_state.intent_payload.get("target_audience", "")
    tone = st.session_state.intent_payload.get("tone", "")
    params = {}
    if audience:
        params["audience"] = audience
    if tone:
        # tone field stores combined string; keep only first token for validator
        params["tone"] = tone.split(";")[0].strip() or tone
    if st.button("Apply template & continue →", type="primary", use_container_width=True,
                 key="setup_apply_template"):
        res = select_template(options[selected_name]["id"], params)
        if "error" in res:
            st.error(res["error"])
        else:
            st.session_state.selected_template_id = options[selected_name]["id"]
            _go_to_step(2)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_knowledge():
    st.markdown("## 2 · Knowledge — your source library")
    st.caption(
        "Add reference material and your author notes. Author notes get the highest "
        "retrieval priority. Sources are optional but strongly recommended for grounded drafts."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="studio-card">', unsafe_allow_html=True)
        st.markdown("#### Reference material")
        st.caption("Books, articles, PDFs that should inform the writing.")
        general_files = st.file_uploader(
            "Upload PDFs / DOCX / TXT", type=["pdf", "docx", "txt"],
            accept_multiple_files=True, key="knowledge_general_uploader",
        )
        if st.button("Add reference material", disabled=not general_files,
                     use_container_width=True, key="knowledge_add_general"):
            with st.spinner("Ingesting reference material..."):
                for item in upload_files(general_files, UPLOAD_ENDPOINT):
                    ok = item.get("status") == "success"
                    st.session_state.uploaded_files.append({
                        "name": item.get("filename", "?"),
                        "status": "ok" if ok else "error",
                        "reason": item.get("reason", ""),
                    })
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="studio-card">', unsafe_allow_html=True)
        st.markdown("#### Author notes")
        st.caption("Your voice samples, transcripts, questionnaires. Highest priority.")
        author_files = st.file_uploader(
            "Upload PDFs / DOCX / TXT", type=["pdf", "docx", "txt"],
            accept_multiple_files=True, key="knowledge_author_uploader",
        )
        if st.button("Add author materials", disabled=not author_files,
                     use_container_width=True, key="knowledge_add_author"):
            with st.spinner("Ingesting author materials..."):
                for item in upload_files(author_files, AUTHOR_DOCS_ENDPOINT):
                    ok = item.get("status") == "success"
                    st.session_state.author_uploaded_files.append({
                        "name": item.get("filename", "?"),
                        "status": "ok" if ok else "error",
                        "reason": item.get("reason", ""),
                    })
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="studio-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Source shelf</div>', unsafe_allow_html=True)
    total = len(st.session_state.uploaded_files) + len(st.session_state.author_uploaded_files)
    if total == 0:
        st.info("No sources added yet. You can continue without sources, "
                "but the AI will have less to ground the writing in.")
    else:
        chips = []
        for item in st.session_state.author_uploaded_files:
            klass = "chip-accent" if item.get("status") == "ok" else "chip-error"
            chips.append(f'<span class="meta-chip {klass}">★ {item.get("name", "?")}</span>')
        for item in st.session_state.uploaded_files:
            klass = "chip-ok" if item.get("status") == "ok" else "chip-error"
            chips.append(f'<span class="meta-chip {klass}">{item.get("name", "?")}</span>')
        st.markdown("".join(chips), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    nav_l, nav_r = st.columns([1, 1])
    with nav_l:
        if st.button("← Back to Setup", use_container_width=True, key="knowledge_back"):
            _go_to_step(1)
            st.rerun()
    with nav_r:
        if st.button("Continue to Blueprint →", type="primary",
                     use_container_width=True, key="knowledge_next"):
            _go_to_step(3)
            st.rerun()


def render_blueprint(templates: list[dict], selected_template: dict):
    st.markdown("## 3 · Blueprint — chapter framework")
    st.caption("Approve the chapter structure before drafting. Edit any title or section in place.")

    active_template_id = selected_template.get("template_id", "")
    if active_template_id:
        st.markdown(
            f'<span class="meta-chip chip-accent">Template active: {active_template_id}</span>',
            unsafe_allow_html=True,
        )

    has_blueprint = bool(st.session_state.blueprint_chapters)

    action_col, _ = st.columns([1, 1])
    with action_col:
        cta_label = "↻ Rebuild blueprint" if has_blueprint else "✦ Auto-build Blueprint"
        if st.button(cta_label, type="primary", use_container_width=True, key="bp_build"):
            params = {}
            audience = st.session_state.intent_payload.get("target_audience", "")
            if audience:
                params["audience"] = audience
            template_id = active_template_id or "classic_nonfiction"
            with st.spinner("Composing your blueprint..."):
                result = orchestrate_auto_blueprint(template_id, params)
            if "error" in result:
                st.error(result["error"])
            else:
                st.session_state.blueprint_chapters = result.get("chapters", [])
                st.session_state.blueprint_approved = False
                st.session_state.chapter_state = {}
                st.success(f"Blueprint ready ({result.get('chapters_count', 0)} chapters).")
                st.rerun()

    if not has_blueprint:
        st.info("Click **Auto-build Blueprint** to generate a starting structure. "
                "You'll be able to edit every chapter before approving.")
        nav_l, _ = st.columns([1, 1])
        with nav_l:
            if st.button("← Back to Knowledge", use_container_width=True, key="bp_back_empty"):
                _go_to_step(2)
                st.rerun()
        return

    st.markdown('<div class="section-label">Chapters</div>', unsafe_allow_html=True)
    edited: list[dict] = []
    for idx, chapter in enumerate(st.session_state.blueprint_chapters):
        with st.expander(f"Chapter {idx + 1}: {chapter.get('title', 'Untitled')}",
                         expanded=False):
            new_title = st.text_input("Title", value=chapter.get("title", ""),
                                      key=f"bp_title_{idx}")
            sections = chapter.get("sections", []) or []
            section_titles = "\n".join(
                f"- {s.get('title', '')}" + (f" | {s['description']}" if s.get("description") else "")
                for s in sections
            )
            new_sections_text = st.text_area(
                "Sections (one per line, use ' | ' for description)",
                value=section_titles, height=120, key=f"bp_sections_{idx}",
            )
            parsed_sections = []
            for line in new_sections_text.splitlines():
                line = line.strip().lstrip("-").strip()
                if not line:
                    continue
                if "|" in line:
                    t, d = line.split("|", 1)
                    parsed_sections.append({"title": t.strip(), "description": d.strip()})
                else:
                    parsed_sections.append({"title": line, "description": None})
            edited.append({"title": new_title.strip() or chapter.get("title", ""),
                           "sections": parsed_sections})

    save_col, approve_col = st.columns(2)
    with save_col:
        if st.button("💾 Save edits", use_container_width=True, key="bp_save"):
            res = save_outline_chapters(edited)
            if "error" in res:
                st.error(res["error"])
            else:
                st.session_state.blueprint_chapters = res.get("chapters", edited)
                st.success("Blueprint saved.")
                st.rerun()
    with approve_col:
        if st.button("✓ Approve & start drafting →", type="primary",
                     use_container_width=True, key="bp_approve"):
            # Always save latest edits before advancing
            res = save_outline_chapters(edited)
            if "error" in res:
                st.error(res["error"])
            else:
                st.session_state.blueprint_chapters = res.get("chapters", edited)
                st.session_state.blueprint_approved = True
                _go_to_step(4)
                st.rerun()

    nav_l, _ = st.columns([1, 1])
    with nav_l:
        if st.button("← Back to Knowledge", use_container_width=True, key="bp_back"):
            _go_to_step(2)
            st.rerun()


def _render_originality_chip(orig: dict | None):
    if not orig:
        st.markdown('<span class="meta-chip">Originality: pending</span>',
                    unsafe_allow_html=True)
        return
    flagged = orig.get("flagged")
    score = orig.get("max_score", 0)
    klass = "chip-warn" if flagged else "chip-ok"
    label = "Needs revision" if flagged else "Clear"
    st.markdown(
        f'<span class="meta-chip {klass}">Originality: {label} · score {score:.2f}</span>',
        unsafe_allow_html=True,
    )


def render_draft():
    st.markdown("## 4 · Draft — chapter by chapter")
    st.caption(
        "Pick a chapter, generate a draft from your sources, edit freely, then approve. "
        "Use **Redraft with instructions** to steer the AI in a specific direction."
    )

    chapters = st.session_state.blueprint_chapters or []
    if not chapters:
        st.warning("No blueprint yet. Go back to step 3 to build one.")
        if st.button("← Back to Blueprint", use_container_width=True, key="draft_back_nobp"):
            _go_to_step(3)
            st.rerun()
        return

    titles = [f"{i + 1}. {ch.get('title', 'Untitled')}" for i, ch in enumerate(chapters)]
    active_idx = st.session_state.active_chapter_idx
    if active_idx >= len(chapters):
        active_idx = 0
        st.session_state.active_chapter_idx = 0
    selected_label = st.selectbox("Active chapter", titles, index=active_idx, key="draft_picker")
    st.session_state.active_chapter_idx = titles.index(selected_label)
    idx = st.session_state.active_chapter_idx
    chapter = chapters[idx]
    cstate = _ensure_chapter_state(idx)

    # Chapter card with status
    status_class = "approved" if cstate["approved"] else ("pending" if cstate["draft"] else "")
    sections = chapter.get("sections", []) or []
    section_chips = "".join(
        f'<span class="meta-chip">{s.get("title", "?")}</span>' for s in sections
    )
    st.markdown(
        f'<div class="chapter-card {status_class}">'
        f'<div class="chapter-title">Chapter {idx + 1}: {chapter.get("title", "Untitled")}</div>'
        f'<div style="margin-top:6px;">{section_chips or "<em>No sections</em>"}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    instructions = st.text_area(
        "Optional drafting instructions (tone, focus, what to emphasize)",
        placeholder="Lean on the productivity sources. Open with a story. Keep it under 1500 words.",
        height=90, key=f"draft_instr_{idx}",
    )

    bcol1, bcol2, bcol3 = st.columns(3)
    with bcol1:
        draft_label = "✦ Draft this chapter" if not cstate["draft"] else "↻ Redraft chapter"
        if st.button(draft_label, type="primary", use_container_width=True, key=f"draft_go_{idx}"):
            with st.spinner("Drafting from your sources..."):
                result = orchestrate_draft_chapter(idx, instructions)
            if "error" in result:
                st.error(result["error"])
            else:
                if cstate["draft"]:
                    cstate["history"].append({
                        "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "text": cstate["draft"],
                    })
                cstate["draft"] = result.get("answer", "")
                cstate["sources"] = result.get("sources", [])
                cstate["originality"] = result.get("originality_report")
                cstate["approved"] = False
                st.rerun()
    with bcol2:
        if st.button("⟲ Revert to previous", disabled=not cstate["history"],
                     use_container_width=True, key=f"draft_revert_{idx}"):
            prev = cstate["history"].pop()
            cstate["draft"] = prev["text"]
            cstate["approved"] = False
            st.rerun()
    with bcol3:
        approve_disabled = not cstate["draft"].strip()
        if st.button("✓ Approve chapter", disabled=approve_disabled,
                     use_container_width=True, key=f"draft_approve_{idx}"):
            cstate["approved"] = True
            st.success(f"Chapter {idx + 1} approved.")
            if idx + 1 < len(chapters):
                st.session_state.active_chapter_idx = idx + 1
            st.rerun()

    if cstate["draft"]:
        edited_text = st.text_area(
            "Chapter draft (editable)", value=cstate["draft"],
            height=380, key=f"draft_body_{idx}",
        )
        if edited_text != cstate["draft"]:
            cstate["draft"] = edited_text
            cstate["approved"] = False

        chips_html = "".join(
            f'<span class="meta-chip">{s.get("source", "?")} · p{s.get("page", "?")}</span>'
            for s in cstate["sources"]
        )
        st.markdown(
            f'<div class="section-label">Sources used</div>{chips_html or "<em>No source citations.</em>"}',
            unsafe_allow_html=True,
        )
        _render_originality_chip(cstate["originality"])
    else:
        st.info("No draft yet. Click **Draft this chapter** to generate one.")

    # Per-chapter progress overview
    st.markdown('<div class="section-label" style="margin-top:18px;">Chapter progress</div>',
                unsafe_allow_html=True)
    chips = []
    for i, ch in enumerate(chapters):
        s = st.session_state.chapter_state.get(i, {})
        if s.get("approved"):
            klass, label = "chip-ok", "✓"
        elif s.get("draft"):
            klass, label = "chip-warn", "✎"
        else:
            klass, label = "", "·"
        chips.append(
            f'<span class="meta-chip {klass}">{label} {i + 1}. '
            f'{ch.get("title", "Untitled")[:32]}</span>'
        )
    st.markdown("".join(chips), unsafe_allow_html=True)

    nav_l, nav_r = st.columns([1, 1])
    with nav_l:
        if st.button("← Back to Blueprint", use_container_width=True, key="draft_back"):
            _go_to_step(3)
            st.rerun()
    with nav_r:
        approved_count = sum(1 for s in st.session_state.chapter_state.values()
                             if s.get("approved"))
        if st.button(
            f"Continue to Review ({approved_count}/{len(chapters)} approved) →",
            type="primary", use_container_width=True, key="draft_next",
        ):
            _go_to_step(5)
            st.rerun()


def render_review_export(project_name: str):
    st.markdown("## 5 · Review & Export")
    st.caption("Validate originality across all chapters and export your manuscript.")

    chapters = st.session_state.blueprint_chapters or []
    approved_chapters: list[dict] = []
    rows_html: list[str] = []
    for i, ch in enumerate(chapters):
        s = st.session_state.chapter_state.get(i, {})
        draft_ok = bool(s.get("draft", "").strip())
        approved = bool(s.get("approved"))
        orig = s.get("originality") or {}
        if draft_ok and approved:
            approved_chapters.append({"title": ch.get("title", f"Chapter {i + 1}"),
                                      "content": s["draft"]})
        klass = "chip-ok" if approved else ("chip-warn" if draft_ok else "chip-error")
        status = "Approved" if approved else ("Draft (not approved)" if draft_ok else "No draft")
        orig_label = ""
        if orig:
            o_klass = "chip-warn" if orig.get("flagged") else "chip-ok"
            orig_label = (
                f'<span class="meta-chip {o_klass}">orig {orig.get("max_score", 0):.2f}</span>'
            )
        rows_html.append(
            f'<div class="studio-soft" style="margin-bottom:8px;">'
            f'<strong>Chapter {i + 1}: {ch.get("title", "Untitled")}</strong><br>'
            f'<span class="meta-chip {klass}">{status}</span>{orig_label}'
            f"</div>"
        )

    st.markdown('<div class="studio-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Chapter readiness</div>', unsafe_allow_html=True)
    if rows_html:
        st.markdown("".join(rows_html), unsafe_allow_html=True)
    else:
        st.info("No chapters drafted yet.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="studio-card">', unsafe_allow_html=True)
    st.markdown("### Re-run originality across approved chapters")
    if st.button("Run originality check", use_container_width=True, key="review_orig_run",
                 disabled=not approved_chapters):
        for i, ch in enumerate(chapters):
            s = st.session_state.chapter_state.get(i, {})
            if not s.get("approved") or not s.get("draft"):
                continue
            with st.spinner(f"Checking chapter {i + 1}..."):
                res = originality_check_text(s["draft"])
            if "error" not in res:
                s["originality"] = res
        st.success("Originality refreshed.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="studio-card">', unsafe_allow_html=True)
    st.markdown("### Export manuscript")
    export_title = st.text_input("Manuscript title", value=project_name, key="review_export_title")
    disabled = not approved_chapters
    if disabled:
        st.caption("Approve at least one chapter to enable export.")
    if st.button("⬇ Export manuscript", type="primary", use_container_width=True,
                 disabled=disabled, key="review_export_btn"):
        with st.spinner("Assembling manuscript..."):
            result = export_draft(export_title.strip() or "Untitled", approved_chapters)
        if "error" in result:
            st.error(result["error"])
        else:
            st.success("Export ready.")
            st.download_button(
                "Download .md", data=result.get("content", ""),
                file_name=f"{result.get('title', 'manuscript')}.md",
                use_container_width=True, key="review_export_download",
            )
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Stored exports", expanded=False):
        drafts = fetch_drafts()
        if not drafts:
            st.caption("No stored manuscript exports yet.")
        for draft in drafts[:10]:
            col_load, col_delete = st.columns([3, 1])
            with col_load:
                if st.button(f"Open: {draft.get('title', 'Untitled')}",
                             key=f"open_{draft.get('id', '')}", use_container_width=True):
                    detail = fetch_draft(draft.get("id", ""))
                    if "error" in detail:
                        st.error(detail["error"])
                    else:
                        st.text_area("Export content", detail.get("content", ""),
                                     height=220, key=f"export_view_{draft.get('id', '')}")
            with col_delete:
                if st.button("Delete", key=f"delete_{draft.get('id', '')}",
                             use_container_width=True):
                    result = delete_draft(draft.get("id", ""))
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success("Stored draft deleted.")
                        st.rerun()

    nav_l, _ = st.columns([1, 1])
    with nav_l:
        if st.button("← Back to Draft", use_container_width=True, key="review_back"):
            _go_to_step(4)
            st.rerun()


_init_session()
ctx_data = fetch_book_context()
templates = fetch_templates()
selected_template = fetch_selected_template()

if ctx_data.get("active"):
    st.session_state.book_context_active = True
    st.session_state.book_context_title = ctx_data.get("title", "Untitled")
else:
    st.session_state.book_context_active = False

theme = st.session_state.ui_theme
st.markdown(LIGHT_THEME if theme == "Light" else DARK_THEME, unsafe_allow_html=True)

backend = _backend_status()
ollama = _ollama_status()
project_name = st.session_state.book_context_title or "Untitled Manuscript"

render_topbar(project_name, backend, ollama)
render_step_rail(st.session_state.wizard_step)

step = st.session_state.wizard_step
if step == 0:
    render_landing(st.session_state.book_context_active, project_name)
elif step == 1:
    render_setup(templates)
    render_setup_template_picker(templates, selected_template)
    # If auto-mode and intent already saved, offer to skip ahead
    if (st.session_state.book_context_active
            and st.session_state.template_choice_mode == "auto"
            and st.session_state.intent_payload):
        if st.button("Continue to Knowledge →", type="primary",
                     use_container_width=True, key="setup_auto_next"):
            _go_to_step(2)
            st.rerun()
elif step == 2:
    render_knowledge()
elif step == 3:
    render_blueprint(templates, selected_template)
elif step == 4:
    render_draft()
elif step == 5:
    render_review_export(project_name)
else:
    _go_to_step(0)
    st.rerun()



