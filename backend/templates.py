"""
backend/templates.py — deterministic slot-filling instruction templates.

Card instructions are NEVER composed by a model. They are filled from the
normalized schedule fields (quantities, buckets, meal relation, duration,
as_needed, needs_review) using the per-language strings below, so they
cannot hallucinate a dose. A model may only translate the free-text notes
field elsewhere — never these sentences.
"""

from backend.normalize import format_quantity
from backend.schema import normalize_schedule


ENGLISH = {
    "buckets": {
        "morning": "in the morning",
        "afternoon": "in the afternoon",
        "evening": "in the evening",
        "night": "at night",
    },
    "meals": {
        "before_food": "before food",
        "after_food": "after food",
        "with_food": "with food",
    },
    "duration": "for {duration}",
    "and": " and ",
    "list_sep": ", ",
    "tablet_singular": "tablet",
    "tablet_plural": "tablets",
    "slot_with_qty": "{qty} {unit} {when}",
    "take_quantified": "Take {slots}{suffix}.",
    "take_plain": "Take this medicine {slots}{suffix}.",
    "as_needed": "Take this medicine only when you need it, as your doctor advised{suffix}.",
    "needs_review": (
        "The timing for this medicine is not clear from the prescription. "
        "Please ask your pharmacist or doctor before taking it."
    ),
    "no_schedule": "Please ask your pharmacist how to take this medicine.",
}

# TODO(Roopkatha): native review needed. These are English placeholder strings
# so Hindi renders safely until the native-speaker translation lands. Replace
# every value with natural Hindi (Devanagari); keep the {placeholders} intact.
HINDI = dict(ENGLISH)

# TODO(Roopkatha): native review needed. Same as above, for Bengali script.
BENGALI = dict(ENGLISH)

TEMPLATES = {
    "English": ENGLISH,
    "Hindi": HINDI,
    "Bengali": BENGALI,
}


def _join(phrases, strings):
    if len(phrases) == 1:
        return phrases[0]
    return strings["list_sep"].join(phrases[:-1]) + strings["and"] + phrases[-1]


def _suffix(medicine, strings):
    extras = []
    meal = strings["meals"].get(medicine.get("meal_relation", ""))
    if meal:
        extras.append(meal)
    duration = medicine.get("duration", "")
    if duration:
        extras.append(strings["duration"].format(duration=duration))
    return ", " + ", ".join(extras) if extras else ""


def build_instruction(medicine, language="English"):
    """Deterministic instruction sentence for one normalized medicine."""
    strings = TEMPLATES.get(language, ENGLISH)

    if medicine.get("needs_review"):
        return strings["needs_review"]

    suffix = _suffix(medicine, strings)

    if medicine.get("as_needed"):
        return strings["as_needed"].format(suffix=suffix)

    schedule = medicine.get("schedule", [])
    if not schedule:
        return strings["no_schedule"]

    quantities = medicine.get("quantities") or {}
    phrases = []
    for bucket in schedule:
        when = strings["buckets"].get(bucket, bucket)
        if bucket in quantities:
            amount = format_quantity(quantities[bucket])
            unit = (
                strings["tablet_singular"]
                if amount in ("½", "1")
                else strings["tablet_plural"]
            )
            phrases.append(strings["slot_with_qty"].format(qty=amount, unit=unit, when=when))
        else:
            phrases.append(when)

    template = strings["take_quantified"] if quantities else strings["take_plain"]
    return template.format(slots=_join(phrases, strings), suffix=suffix)


def localize_schedule(schedule, language):
    """Fill every medicine's instruction from templates. Romanization is
    intentionally skipped: English needs none, and Hindi/Bengali strings are
    English placeholders until Roopkatha's native review."""
    schedule = normalize_schedule(schedule)
    for medicine in schedule["medicines"]:
        medicine["instruction"] = build_instruction(medicine, language)
        medicine["romanized"] = ""
    return schedule
