# AI Book RAG Generation

AI-powered book generation system using RAG, enabling users to transform
documents, research papers, and context into structured, editable books.

Core backend is a production-ready **Retrieval-Augmented Generation** (RAG)
service built with:

| Component | Technology |
|---|---|
| Web Framework | FastAPI |
| Orchestration | LangChain |
| Vector Store | ChromaDB (persistent) |
| LLM | Ollama `llama3.1:8b` |
| Embeddings | Ollama `nomic-embed-text` |
| PDF parsing | PyMuPDF (fitz) |
| DOCX parsing | python-docx |

---

## Project Structure

```
AI_BOOK_RAG_GENERATION/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── rag_pipeline/
│   │   ├── chunker.py           # Recursive & semantic chunking
│   │   ├── embedder.py          # Pluggable embedding (Ollama default)
│   │   ├── retriever.py         # ChromaDB store + top-k similarity search
│   │   └── generator.py        # Ollama LLM answer generation
│   ├── services/
│   │   ├── document_service.py  # Ingestion orchestrator
│   │   ├── query_service.py     # Query orchestrator
│   │   ├── author_service.py    # Author docs ingestion
│   │   ├── book_context_service.py # Book context storage
│   │   ├── competitor_service.py   # Competitor analysis jobs
│   │   └── outline_service.py      # Chapter outline persistence
│   ├── routes/
│   │   ├── upload.py            # POST /upload-documents
│   │   └── query.py             # POST /query
│   │   ├── book_context.py       # POST /create-book-context
│   │   ├── author_docs.py        # POST /upload-author-documents
│   │   ├── competitor.py         # POST /analyze-competitors
│   │   └── chapter_outline.py    # POST /set-chapter-outline
│   └── utils/
│       ├── config.py            # Pydantic settings (env-driven)
│       └── file_parser.py       # PDF / DOCX / TXT parsers
├── requirements.txt
├── .env.example
├── streamlit_app.py
└── README.md
```

---

## Prerequisites

### 1. Python 3.11+
```powershell
python --version   # must be >= 3.11
```

### 2. Ollama
Download and install from https://ollama.com/download

Pull the required models:
```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Verify Ollama is running:
```powershell
ollama list
```

---

## Setup & Run

### Step 1 — Clone / navigate to project
```powershell
cd "f:\D_backup\Work\GlobalBook\AI_BOOK_RAG_GENERATION"
```

### Step 2 — Create virtual environment
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 3 — Install dependencies
```powershell
pip install -r requirements.txt
```

### Step 4 — Configure (optional)
Copy `.env.example` to `.env` and edit values if needed:
```powershell
Copy-Item .env.example .env
```

### Step 5 — Start the server
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

---

## Dev Workflow

### Run backend + UI
```powershell
# Terminal 1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2
streamlit run streamlit_app.py
```

### Quick smoke test
```powershell
python test_api.py
```

### Environment variables
- Copy `.env.example` to `.env` for local overrides.
- Keep `OLLAMA_BASE_URL` and model names aligned with your Ollama install.

---

## API Reference

### `POST /upload-documents`

Upload one or more PDF, DOCX, or TXT files.

**Request** — `multipart/form-data`
| Field | Type | Description |
|---|---|---|
| `files` | `File[]` | One or more documents |

**cURL example:**
```bash
curl -X POST http://localhost:8000/upload-documents \
  -F "files=@my_document.pdf" \
  -F "files=@another.docx"
```

**Response `201`:**
```json
{
  "total_files": 2,
  "total_chunks_stored": 143,
  "details": [
    {
      "filename": "my_document.pdf",
      "status": "success",
      "pages": 12,
      "chunks_stored": 87
    },
    {
      "filename": "another.docx",
      "status": "success",
      "pages": 1,
      "chunks_stored": 56
    }
  ]
}
```

---

### `POST /query`

Ask a question against the ingested knowledge base.

**Request body (JSON):**
```json
{
  "question": "What are the key findings in chapter 3?",
  "top_k": 5,
  "source_filter": "my_document.pdf"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | `string` | ✅ | The question to answer |
| `top_k` | `integer` | ❌ | Chunks to retrieve (1–20, default from config) |
| `source_filter` | `string` | ❌ | Restrict to a specific filename |

**Response `200`:**
```json
{
  "question": "What are the key findings in chapter 3?",
  "answer": "According to my_document.pdf (page 3), the key findings include...",
  "sources": [
    { "source": "my_document.pdf", "page": 3 },
    { "source": "my_document.pdf", "page": 5 }
  ],
  "retrieved_chunks": [
    {
      "text": "Chapter 3 reveals that...",
      "source": "my_document.pdf",
      "page": 3,
      "chunk_index": 12,
      "score": 0.9231
    }
  ]
}
```

---

### `POST /create-book-context`

Create or update the active book context (title, audience, tone, etc.).

### `POST /upload-author-documents`

Upload author-specific content that should have highest retrieval priority.

### `POST /analyze-competitors`

Upload competitor PDFs for background analysis. Poll the job status endpoint.

### `POST /set-chapter-outline`

Save a chapter outline that the generator should follow strictly.

### `POST /originality-check`

Check a draft for similarity against stored corpora (general + competitor).

### `POST /drafts/export`

Export a full draft from chapter content (placeholder scaffold).

### `GET /drafts`

List exported drafts (metadata only).

### `GET /drafts/{draft_id}`

Fetch a stored draft by id.

### `DELETE /drafts/{draft_id}`

Delete a stored draft by id.

### `GET /templates`

List available templates/frameworks.

### `POST /templates/select`

Select a template for the current project.

---

## Configuration

All settings can be overridden via environment variables or a `.env` file.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | LLM model name |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama` (extendable to `openai`, `huggingface`) |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB storage directory |
| `CHROMA_COLLECTION_NAME` | `rag_documents` | ChromaDB collection name |
| `CHUNK_STRATEGY` | `recursive` | `recursive` or `semantic` |
| `CHUNK_SIZE` | `512` | Max characters per chunk |
| `CHUNK_OVERLAP` | `64` | Overlap characters between chunks |
| `RETRIEVAL_TOP_K` | `5` | Default number of chunks to retrieve |
| `LLM_PROVIDER` | `ollama` | `ollama`, `openai`, or `anthropic` |
| `LLM_REASONING_MODEL` | `llama3.1:8b` | High-reasoning model name |
| `LLM_LIGHT_MODEL` | `llama3.1:8b` | Light model for critiques |
| `LLM_API_BASE_URL` | `` | Optional provider base URL |
| `ORIGINALITY_TOP_K` | `5` | Similarity matches to return |
| `ORIGINALITY_THRESHOLD` | `0.85` | Flag threshold for similarity |
| `UPLOAD_DIR` | `./uploaded_docs` | Directory to save uploaded files |
| `DRAFT_STORE_DIR` | `./drafts` | Directory to persist exported drafts |

---

## Chunk Strategies

| Strategy | Description | Best For |
|---|---|---|
| `recursive` | LangChain `RecursiveCharacterTextSplitter` | General purpose, fast |
| `semantic` | Sentence-boundary + rolling window | Better coherence for QA |

---

## Extending the System

### Add a new embedding provider
Edit `app/rag_pipeline/embedder.py` and add an `elif` branch:
```python
elif provider == "openai":
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model="text-embedding-3-small")
```
Then set `EMBEDDING_PROVIDER=openai` in your `.env`.

### Add a new file type
Edit `app/utils/file_parser.py` and add a parser function + register it in `parsers` dict.

---

## Quick Test

With the server running, use the included test script:

```powershell
python test_api.py
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Connection refused` on Ollama | Run `ollama serve` in a separate terminal |
| `model not found` | Run `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text` |
| ChromaDB errors | Delete `./chroma_db` folder and restart |
| `pymupdf` import error | Run `pip install pymupdf` |
