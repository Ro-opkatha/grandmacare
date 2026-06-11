"""
backend/schema.py — deterministic validation for the card JSON contract.

The brain (Tiny Aya) is prompted to return a flat list of medicine cards.
This module is the trust boundary: whatever the model emits is parsed
leniently but sanitized strictly — strings coerced and trimmed, missing
fields defaulted, unknown shapes rejected. No model output reaches the UI
without passing through here. No fixed timing vocabulary: `when` is free
text, exactly as the prescription says it.
"""

import json
import re

CARD_TEXT_FIELDS = ("name", "dose", "when", "written", "explanation")


def empty_cards():
    return {"medicines": []}


def _extract_json(text):
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("The model returned an empty response.")

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("The model response was not valid JSON.") from exc


def sanitize_cards(payload):
    """Coerce a parsed payload into the card contract. Never raises."""
    if not isinstance(payload, dict):
        return empty_cards()

    medicines = []
    for item in payload.get("medicines", []):
        if not isinstance(item, dict):
            continue
        card = {field: str(item.get(field) or "").strip() for field in CARD_TEXT_FIELDS}
        card["unclear"] = bool(item.get("unclear"))
        if not any(card[field] for field in CARD_TEXT_FIELDS):
            continue
        if not card["name"]:
            card["name"] = "Medicine"
        medicines.append(card)

    return {"medicines": medicines}


def parse_cards_json(text):
    """Model output -> sanitized cards. Raises ValueError only when no JSON
    object can be extracted at all (so the caller can show a retry message)."""
    payload = text if isinstance(text, dict) else _extract_json(text)
    return sanitize_cards(payload)
