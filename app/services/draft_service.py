"""
Draft export service.

Assembles drafts and persists them to disk.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from app.utils.config import get_settings

settings = get_settings()


def _draft_dir() -> Path:
    p = Path(settings.draft_store_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def export_draft(
    title: str,
    chapters: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Assemble a plain-text draft from chapter content.

    chapters: list of {"title": str, "content": str}
    """
    parts = [f"# {title}", ""]
    for ch in chapters:
        parts.append(f"## {ch.get('title','Untitled')}\n")
        parts.append(ch.get("content", ""))
        parts.append("")

    return {
        "title": title,
        "content": "\n".join(parts).strip(),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def save_draft(draft: Dict[str, Any]) -> Dict[str, Any]:
    draft_id = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    payload = {
        "id": draft_id,
        "title": draft.get("title", "Untitled"),
        "content": draft.get("content", ""),
        "generated_at": draft.get("generated_at"),
    }
    path = _draft_dir() / f"{draft_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def list_drafts() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for fp in sorted(_draft_dir().glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            items.append({
                "id": data.get("id", fp.stem),
                "title": data.get("title", "Untitled"),
                "generated_at": data.get("generated_at"),
            })
        except Exception:
            continue
    return items


def get_draft(draft_id: str) -> Optional[Dict[str, Any]]:
    path = _draft_dir() / f"{draft_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete_draft(draft_id: str) -> bool:
    path = _draft_dir() / f"{draft_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True
