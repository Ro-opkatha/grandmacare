import json
import re


def extract_json(text):
    if isinstance(text, dict):
        return text

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
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("The model response was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("The model response was not a JSON object.")
    return payload


def normalize_medicines(payload):
    medicines = []
    if not isinstance(payload, dict):
        return {"medicines": []}

    items = payload.get("medicines", [])
    if not isinstance(items, list):
        return {"medicines": []}

    for item in items:
        if not isinstance(item, dict):
            continue

        medicine = {
            "name": str(item.get("name") or "").strip(),
            "dose": str(item.get("dose") or "").strip(),
            "timing": str(item.get("timing") or "").strip(),
            "timing_label": str(item.get("timing_label") or "").strip(),
            "instruction": str(item.get("instruction") or "").strip(),
            "romanized": str(item.get("romanized") or "").strip(),
            "notes": str(item.get("notes") or "").strip(),
        }

        if not medicine["name"] and not medicine["timing"]:
            continue
        if not medicine["name"]:
            medicine["name"] = "Medicine"

        medicines.append(medicine)

    return {"medicines": medicines}


def grouping_key(medicine):
    label = medicine.get("timing_label") or medicine.get("timing") or "As written"
    return " ".join(str(label).split()).lower()


def group_by_timing(medicines):
    groups = []
    index_by_key = {}

    for medicine in medicines:
        key = grouping_key(medicine)
        if key in index_by_key:
            groups[index_by_key[key]][1].append(medicine)
        else:
            display = (
                medicine.get("timing_label")
                or medicine.get("timing")
                or "As written"
            )
            display = " ".join(str(display).split())
            index_by_key[key] = len(groups)
            groups.append((display, [medicine]))

    return groups


def normalize_pill_match(payload):
    if not isinstance(payload, dict):
        payload = {}

    matched = payload.get("matched", False)
    if isinstance(matched, str):
        matched = matched.strip().lower() == "true"

    return {
        "matched": bool(matched),
        "medicine_name": str(payload.get("medicine_name") or "").strip(),
        "answer": str(payload.get("answer") or "").strip(),
        "romanized": str(payload.get("romanized") or "").strip(),
    }


def truncate_transcript(text, max_chars=2500):
    text = str(text or "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[transcript truncated]"
