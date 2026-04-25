"""
Smoke-test script for the RAG API.

Run with:
    python test_api.py

Requires the server to be running:
    uvicorn app.main:app --reload
"""
import json
import os
import sys
import tempfile

import httpx

BASE_URL = "http://localhost:8000"


def _print(label: str, data) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print("="*60)
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)


def test_health():
    print("\n[1/3] Health check …")
    r = httpx.get(f"{BASE_URL}/health")
    r.raise_for_status()
    _print("Health", r.json())


def test_upload():
    print("\n[2/3] Uploading a sample text document …")

    # Create a temporary .txt file with sample content
    sample_text = """\
Introduction to Retrieval-Augmented Generation

RAG is a technique that enhances large language model outputs by retrieving
relevant information from a knowledge base before generating a response.

Chapter 1: Core Components
- Embedding model converts text to dense vectors.
- Vector database stores and retrieves these vectors by similarity.
- LLM generates the final answer grounded in the retrieved context.

Chapter 2: Benefits
- Reduces hallucination by grounding answers in source documents.
- Allows models to reference up-to-date or proprietary information.
- Improves factual accuracy and source traceability.

Chapter 3: Chunking Strategies
Recursive splitting divides text by character separators.
Semantic splitting respects sentence boundaries for better coherence.
Smaller chunk sizes improve precision; larger sizes improve context.
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(sample_text)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            r = httpx.post(
                f"{BASE_URL}/upload-documents",
                files={"files": ("rag_intro.txt", f, "text/plain")},
                timeout=60,
            )
        r.raise_for_status()
        _print("Upload Response", r.json())
    finally:
        os.unlink(tmp_path)


def test_query():
    print("\n[3/3] Querying the knowledge base …")
    payload = {
        "question": "What are the benefits of using RAG?",
        "top_k": 3,
    }
    r = httpx.post(f"{BASE_URL}/query", json=payload, timeout=120)
    r.raise_for_status()
    result = r.json()

    _print("Answer", result["answer"])
    _print("Sources", result["sources"])
    print(f"\nRetrieved {len(result['retrieved_chunks'])} chunks.")


if __name__ == "__main__":
    try:
        test_health()
        test_upload()
        test_query()
        print("\n✅  All tests passed!")
    except httpx.ConnectError:
        print("\n❌  Cannot connect to server. Make sure the server is running:")
        print("    uvicorn app.main:app --reload")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"\n❌  HTTP error: {e.response.status_code}")
        print(e.response.text)
        sys.exit(1)
