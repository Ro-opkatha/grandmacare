"""
backend/normalize.py — deterministic prescription notation interpreter.

MiniCPM-V transcribes what is literally written; this module interprets it.
No GPU, no model, fully unit-testable. Unknown notation is flagged, never guessed.
"""

import re

TIME_BUCKETS = ("morning", "afternoon", "evening", "night")

# Latin / common abbreviations -> buckets
ABBREVIATIONS = {
    "od": ["morning"],
    "qd": ["morning"],
    "1od": ["morning"],
    "bd": ["morning", "night"],
    "bid": ["morning", "night"],
    "tds": ["morning", "afternoon", "night"],
    "tid": ["morning", "afternoon", "night"],
    "qid": ["morning", "afternoon", "evening", "night"],
    "hs": ["night"],          # hora somni — at bedtime
    "qhs": ["night"],
    "on": ["night"],          # omni nocte
    "om": ["morning"],        # omni mane
    "noct": ["night"],
}

AS_NEEDED = {"sos", "prn", "as needed", "when needed", "if needed", "if required"}

MEAL_BEFORE = {"ac", "a.c", "a/c", "before food", "before meal", "before meals",
               "empty stomach", "khali pet", "before breakfast"}
MEAL_AFTER = {"pc", "p.c", "p/c", "after food", "after meal", "after meals",
              "after breakfast", "after dinner", "after lunch"}
MEAL_WITH = {"with food", "with meal", "with meals", "cf", "c.f"}

BUCKET_PHRASES = {
    "morning": "in the morning",
    "afternoon": "in the afternoon",
    "evening": "in the evening",
    "night": "at night",
}

MEAL_PHRASES = {
    "before_food": "before food",
    "after_food": "after food",
    "with_food": "with food",
}

# e.g. 1-0-1, 1/2-0-1, 1-1-1-1, 1–0–1 (en dash), 1 - 0 - 1
_PATTERN_RE = re.compile(
    r"(?<![\w/])((?:\d+(?:/\d+)?|½)(?:\s*[-–—]\s*(?:\d+(?:/\d+)?|½)){2,3})(?![\w/])"
)
_DURATION_RE = re.compile(
    r"(?:x|for|×)\s*(\d+)\s*(day|days|din|week|weeks|month|months)", re.IGNORECASE
)


def format_quantity(quantity):
    """0.5 -> ½, 1.0 -> 1, 1.5 -> 1½, anything else -> trimmed decimal."""
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        return ""
    whole = int(quantity)
    fraction = quantity - whole
    if abs(fraction - 0.5) < 1e-9:
        return f"{whole}½" if whole else "½"
    if abs(fraction) < 1e-9:
        return str(whole)
    return f"{quantity:g}"


def _slot_value(token):
    token = token.strip().replace("½", "1/2")
    if "/" in token:
        num, den = token.split("/", 1)
        try:
            return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(token)
    except ValueError:
        return 0.0


def parse_dose_pattern(pattern):
    """'1-0-1' -> buckets + per-slot quantities.

    3 slots = morning-afternoon-night (standard Indian convention).
    4 slots = morning-afternoon-evening-night.
    """
    slots = [_slot_value(s) for s in re.split(r"\s*[-–—]\s*", pattern.strip())]
    if len(slots) == 3:
        names = ("morning", "afternoon", "night")
    elif len(slots) == 4:
        names = TIME_BUCKETS
    else:
        return None
    buckets, quantities = [], {}
    for name, qty in zip(names, slots):
        if qty > 0:
            buckets.append(name)
            quantities[name] = qty
    return {"buckets": buckets, "quantities": quantities}


def interpret_frequency(raw):
    """Interpret a raw frequency string. Returns dict with buckets / as_needed /
    understood flag. Never guesses: unknown notation -> understood=False."""
    text = (raw or "").strip().lower()
    result = {"buckets": [], "quantities": {}, "as_needed": False, "understood": False}
    if not text:
        return result

    if any(marker in text for marker in AS_NEEDED):
        result["as_needed"] = True
        result["understood"] = True
        return result

    match = _PATTERN_RE.search(text)
    if match:
        parsed = parse_dose_pattern(match.group(1))
        if parsed:
            result.update(parsed)
            result["understood"] = True
            return result

    # abbreviation tokens (strip punctuation, check each word)
    for token in re.split(r"[\s,;.]+", text):
        token = token.strip(".")
        if token in ABBREVIATIONS:
            result["buckets"] = list(ABBREVIATIONS[token])
            result["understood"] = True
            return result

    # plain-English buckets ("morning and night")
    found = [b for b in TIME_BUCKETS if b in text]
    if "bedtime" in text and "night" not in found:
        found.append("night")
    if found:
        result["buckets"] = found
        result["understood"] = True
    return result


def interpret_meal_relation(raw):
    text = (raw or "").strip().lower()
    tokens = {t.strip(".") for t in re.split(r"[\s,;]+", text)}
    joined = " ".join(sorted(tokens))
    if tokens & MEAL_BEFORE or any(p in text for p in MEAL_BEFORE):
        return "before_food"
    if tokens & MEAL_AFTER or any(p in text for p in MEAL_AFTER):
        return "after_food"
    if any(p in text or p in joined for p in MEAL_WITH):
        return "with_food"
    return ""


def interpret_duration(raw):
    match = _DURATION_RE.search(raw or "")
    if not match:
        return ""
    count, unit = int(match.group(1)), match.group(2).lower()
    if unit in ("din",):
        unit = "days"
    if count == 1 and unit.endswith("s"):
        unit = unit[:-1]
    if count > 1 and not unit.endswith("s"):
        unit += "s"
    return f"{count} {unit}"


def _rescue_dose_pattern(item):
    """Doctors squeeze 1-0-1 next to the name or dose, and the transcription
    then puts it in the wrong field. Accept ONLY an explicit slot pattern with
    believable tablet counts — never abbreviations, which false-positive on
    ordinary words ("on", "om") — from the other transcribed fields."""
    for field in ("dose", "meal_raw", "duration_raw", "notes", "name"):
        match = _PATTERN_RE.search(str(item.get(field) or ""))
        if not match:
            continue
        parsed = parse_dose_pattern(match.group(1))
        if not parsed or not parsed["buckets"]:
            continue
        if max(parsed["quantities"].values()) > 2:
            continue  # 12-05-25 is a date, not a dose
        parsed["pattern"] = match.group(1)
        return parsed
    return None


def _join_phrases(phrases):
    if len(phrases) == 1:
        return phrases[0]
    return ", ".join(phrases[:-1]) + " and " + phrases[-1]


def build_instruction(medicine):
    """Deterministic English instruction from the structured fields.

    The language model only ever translates this sentence — it must never
    compose dosing text itself, especially for needs_review medicines."""
    if medicine.get("needs_review"):
        return (
            "The timing for this medicine is not clear from the prescription. "
            "Please ask your pharmacist or doctor before taking it."
        )

    extras = []
    meal = MEAL_PHRASES.get(medicine.get("meal_relation", ""))
    if meal:
        extras.append(meal)
    duration = medicine.get("duration", "")
    if duration:
        extras.append(f"for {duration}")
    suffix = ", " + ", ".join(extras) if extras else ""

    if medicine.get("as_needed"):
        return (
            "Take this medicine only when you need it, "
            f"as your doctor advised{suffix}."
        )

    schedule = medicine.get("schedule", [])
    if not schedule:
        return "Please ask your pharmacist how to take this medicine."

    quantities = medicine.get("quantities") or {}
    phrases = []
    for bucket in schedule:
        when = BUCKET_PHRASES.get(bucket, bucket)
        if bucket in quantities:
            amount = format_quantity(quantities[bucket])
            unit = "tablet" if amount in ("½", "1") else "tablets"
            phrases.append(f"{amount} {unit} {when}")
        else:
            phrases.append(when)

    if quantities:
        return f"Take {_join_phrases(phrases)}{suffix}."
    return f"Take this medicine {_join_phrases(phrases)}{suffix}."


def normalize_medicine(item):
    """Takes one transcribed medicine dict from MiniCPM-V:
      {name, dose, frequency_raw, meal_raw, duration_raw, notes}
    Returns the GrandmaCare schedule entry, flagging anything not understood."""
    raw_freq = str(item.get("frequency_raw") or "")
    combined = " ".join(
        str(item.get(k) or "") for k in ("frequency_raw", "meal_raw", "duration_raw", "notes")
    )
    freq = interpret_frequency(raw_freq)

    if not freq["understood"] and not freq["as_needed"]:
        rescued = _rescue_dose_pattern(item)
        if rescued:
            freq["buckets"] = rescued["buckets"]
            freq["quantities"] = rescued["quantities"]
            freq["understood"] = True
            if not raw_freq.strip():
                raw_freq = rescued["pattern"]

    needs_review = not freq["understood"]
    notes = str(item.get("notes") or "").strip()
    if needs_review and raw_freq:
        notes = (notes + " " if notes else "") + (
            f'Timing written as "{raw_freq.strip()}" — please confirm with your pharmacist.'
        )

    return {
        "name": str(item.get("name") or "Medicine").strip(),
        "dose": str(item.get("dose") or "Dose not listed").strip(),
        "schedule": freq["buckets"],
        "quantities": freq["quantities"],          # e.g. {"morning": 0.5}
        "as_needed": freq["as_needed"],
        "meal_relation": interpret_meal_relation(combined),
        "duration": interpret_duration(combined),
        "frequency_raw": raw_freq.strip(),
        "needs_review": needs_review,
        "notes": notes,
        "instruction": "",
        "romanized": "",
    }


def normalize_transcription(payload):
    medicines = []
    if isinstance(payload, dict):
        for item in payload.get("medicines", []):
            if isinstance(item, dict):
                medicines.append(normalize_medicine(item))
    return {"medicines": medicines}
