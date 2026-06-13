import re


_CARD_FIELDS = {
    "medicine": "name",
    "name": "name",
    "dose": "dose",
    "when": "timing",
    "timing": "timing",
    "schedule": "timing",
    "label": "timing_label",
    "take": "instruction",
    "instruction": "instruction",
    "say": "romanized",
    "romanized": "romanized",
    "note": "notes",
    "notes": "notes",
}

_PILL_FIELDS = {
    "match": "medicine_name",
    "medicine": "medicine_name",
    "answer": "answer",
    "take": "answer",
    "say": "romanized",
    "romanized": "romanized",
}

# Allows bullets/markdown noise before the key and ":" or "-" after it.
_LABELED_LINE = re.compile(r"^[\s*#>•-]*([A-Za-z]+)\s*[:\-]\s*(.*)$")

# Fields where a wrapped line should be appended rather than ignored.
_CONTINUABLE = {"instruction", "romanized", "notes", "timing"}


def _empty_card():
    return {
        "name": "",
        "dose": "",
        "timing": "",
        "timing_label": "",
        "instruction": "",
        "romanized": "",
        "notes": "",
    }


def _clean_value(value):
    return value.strip().strip("*").strip()


def parse_cards_text(text):
    medicines = []
    current = None
    last_field = None

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            last_field = None
            continue

        match = _LABELED_LINE.match(line)
        field = _CARD_FIELDS.get(match.group(1).lower()) if match else None

        if field == "name":
            current = _empty_card()
            current["name"] = _clean_value(match.group(2))
            medicines.append(current)
            last_field = "name"
        elif field and current is not None:
            current[field] = _clean_value(match.group(2))
            last_field = field
        elif current is not None and last_field in _CONTINUABLE:
            current[last_field] = (current[last_field] + " " + line).strip()
        else:
            last_field = None

    return [medicine for medicine in medicines if medicine["name"]]


def parse_pill_text(text):
    result = {"matched": False, "medicine_name": "", "answer": "", "romanized": ""}
    last_field = None

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            last_field = None
            continue

        match = _LABELED_LINE.match(line)
        field = _PILL_FIELDS.get(match.group(1).lower()) if match else None

        if field:
            result[field] = _clean_value(match.group(2))
            last_field = field
        elif last_field in ("answer", "romanized"):
            result[last_field] = (result[last_field] + " " + line).strip()

    name = result["medicine_name"]
    if name and name.strip().lower() not in ("none", "no", "no match", "not found"):
        result["matched"] = True
    else:
        result["medicine_name"] = ""

    if not result["answer"]:
        result["answer"] = str(text or "").strip()

    return result


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


def truncate_transcript(text, max_chars=2500):
    text = str(text or "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[transcript truncated]"
