import json
import re


TIME_BUCKETS = ("morning", "afternoon", "evening", "night")

SCRIPT_RANGES = {
    "Devanagari": (0x0900, 0x097F),
    "Bengali": (0x0980, 0x09FF),
}


def uses_expected_script(text, script_name):
    """True if the text contains at least one character of the expected
    script. Guards against the translator answering in the wrong language;
    scripts without a mapped range only require non-empty text."""
    text = str(text or "")
    bounds = SCRIPT_RANGES.get(script_name)
    if bounds is None:
        return bool(text.strip())
    low, high = bounds
    return any(low <= ord(char) <= high for char in text)


def empty_schedule():
    return {"medicines": []}


def _clean_quantities(value):
    quantities = {}
    if not isinstance(value, dict):
        return quantities
    for bucket, qty in value.items():
        bucket_name = str(bucket).strip().lower()
        if bucket_name not in TIME_BUCKETS:
            continue
        try:
            quantities[bucket_name] = float(qty)
        except (TypeError, ValueError):
            continue
    return quantities


def normalize_schedule(payload):
    medicines = []
    if not isinstance(payload, dict):
        return empty_schedule()

    for item in payload.get("medicines", []):
        if not isinstance(item, dict):
            continue

        schedule = item.get("schedule", [])
        if isinstance(schedule, str):
            schedule = [schedule]

        normalized_buckets = []
        for bucket in schedule:
            bucket_name = str(bucket).strip().lower()
            if bucket_name in TIME_BUCKETS and bucket_name not in normalized_buckets:
                normalized_buckets.append(bucket_name)

        medicines.append(
            {
                "name": str(item.get("name") or "Medicine").strip(),
                "dose": str(item.get("dose") or "Dose not listed").strip(),
                "schedule": normalized_buckets,
                "quantities": _clean_quantities(item.get("quantities")),
                "as_needed": bool(item.get("as_needed")),
                "meal_relation": str(item.get("meal_relation") or "").strip(),
                "duration": str(item.get("duration") or "").strip(),
                "quantity_to_buy": str(item.get("quantity_to_buy") or "").strip(),
                "frequency_raw": str(item.get("frequency_raw") or "").strip(),
                "needs_review": bool(item.get("needs_review")),
                "notes": str(item.get("notes") or "").strip(),
                "instruction": str(item.get("instruction") or "").strip(),
                "romanized": str(item.get("romanized") or "").strip(),
            }
        )

    return {"medicines": medicines}


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


def parse_raw_json(text):
    """Lenient JSON extraction with NO schedule normalization.

    Used for the transcription step, where the payload carries raw notation
    fields (frequency_raw, meal_raw, ...) that normalize_schedule would drop.
    """
    if isinstance(text, dict):
        return text
    return _extract_json(text)


def parse_model_json(text):
    if isinstance(text, dict):
        return normalize_schedule(text)
    return normalize_schedule(_extract_json(text))


def merge_translation(schedule, translated):
    base = normalize_schedule(schedule)
    translated = normalize_schedule(translated)
    translated_items = translated.get("medicines", [])

    for index, medicine in enumerate(base["medicines"]):
        if index >= len(translated_items):
            continue
        medicine["instruction"] = translated_items[index].get("instruction", "")
        medicine["romanized"] = translated_items[index].get("romanized", "")

    return base
