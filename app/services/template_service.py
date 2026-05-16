"""
Template and framework service.

Provides a static template catalog and persists the selected template.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.utils.config import get_settings

settings = get_settings()


class Template(BaseModel):
    id: str
    name: str
    description: str
    sections: List[str]


class TemplateSelection(BaseModel):
    template_id: str
    parameters: Dict[str, Any] = {}


class TemplateValidationError(ValueError):
    pass


def _template_path() -> Path:
    p = Path(settings.template_store_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def list_templates() -> List[Template]:
    return [
        Template(
            id="classic_nonfiction",
            name="Classic Nonfiction",
            description="Intro, problem framing, core concepts, case studies, conclusion.",
            sections=["Introduction", "Problem Framing", "Core Concepts", "Case Studies", "Conclusion"],
        ),
        Template(
            id="how_to_playbook",
            name="How-To Playbook",
            description="Step-by-step method with examples and checklists.",
            sections=["Overview", "Step 1", "Step 2", "Step 3", "Common Pitfalls", "Checklist"],
        ),
        Template(
            id="research_synthesis",
            name="Research Synthesis",
            description="Evidence-driven structure for academic or research-heavy books.",
            sections=["Background", "Methodology", "Findings", "Implications", "Future Work"],
        ),
    ]


def validate_template_parameters(template_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate template parameters with a minimal schema.
    This can be extended per template as requirements evolve.
    """
    if not isinstance(parameters, dict):
        raise TemplateValidationError("parameters must be a JSON object")

    cleaned: Dict[str, Any] = {}

    if "audience" in parameters:
        audience = parameters.get("audience")
        if not isinstance(audience, str) or not audience.strip():
            raise TemplateValidationError("audience must be a non-empty string")
        cleaned["audience"] = audience.strip()

    if "pages" in parameters:
        pages = parameters.get("pages")
        if not isinstance(pages, int) or pages <= 0:
            raise TemplateValidationError("pages must be a positive integer")
        cleaned["pages"] = pages

    if "tone" in parameters:
        tone = parameters.get("tone")
        if not isinstance(tone, str) or not tone.strip():
            raise TemplateValidationError("tone must be a non-empty string")
        cleaned["tone"] = tone.strip()

    return cleaned


def save_selected_template(selection: TemplateSelection) -> Dict[str, Any]:
    cleaned = validate_template_parameters(selection.template_id, selection.parameters or {})
    path = _template_path()
    data = selection.model_dump()
    data["parameters"] = cleaned
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def get_selected_template() -> Optional[Dict[str, Any]]:
    path = _template_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_selected_template() -> bool:
    path = _template_path()
    if not path.exists():
        return False
    path.unlink()
    return True
