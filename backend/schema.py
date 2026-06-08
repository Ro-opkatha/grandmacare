import json
import re


TIME_BUCKETS = ("morning", "afternoon", "evening", "night")


def empty_schedule():
    return {"medicines": []}


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
                "notes": str(item.get("notes") or "").strip(),
                "instruction": str(item.get("instruction") or "").strip(),
                "romanized": str(item.get("romanized") or "").strip(),
            }
        )

    return {"medicines": medicines}


def parse_model_json(text):
    if isinstance(text, dict):
        return normalize_schedule(text)

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
        return normalize_schedule(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise ValueError("The model response was not valid JSON.") from exc


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
