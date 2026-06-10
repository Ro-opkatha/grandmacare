from html import escape

from backend.normalize import format_quantity
from backend.schema import TIME_BUCKETS


BUCKET_META = {
    "morning": ("Morning", "sun", "blue"),
    "afternoon": ("Afternoon", "clock", "orange"),
    "evening": ("Evening", "sunset", "teal"),
    "night": ("Night", "moon", "green"),
}

MEAL_LABELS = {
    "before_food": "Before food",
    "after_food": "After food",
    "with_food": "With food",
}


def render_bucket(schedule, bucket):
    title, icon_class, color = BUCKET_META[bucket]
    medicines = [
        medicine
        for medicine in schedule.get("medicines", [])
        if bucket in medicine.get("schedule", [])
    ]

    if medicines:
        cards = "\n".join(
            render_medicine_card(medicine, bucket) for medicine in medicines
        )
    else:
        cards = '<div class="empty-state">No medicines listed for this time.</div>'

    return f"""
    <div class="tile schedule-tile {color}">
        <div class="tile-icon {icon_class}"></div>
        <div class="tile-title">{title}</div>
        <div class="medicine-list">{cards}</div>
    </div>
    """


def render_medicine_card(medicine, bucket=None):
    quantities = medicine.get("quantities") or {}
    quantity_html = ""
    if bucket and bucket in quantities:
        amount = format_quantity(quantities[bucket])
        if amount:
            label = "tablet" if amount in ("½", "1") else "tablets"
            quantity_html = f'<div class="medicine-qty">{escape(amount)} {label}</div>'

    meta_parts = []
    meal_label = MEAL_LABELS.get(medicine.get("meal_relation", ""))
    if meal_label:
        meta_parts.append(meal_label)
    duration = medicine.get("duration", "")
    if duration:
        meta_parts.append(f"For {duration}")
    meta_html = (
        f'<div class="medicine-meta">{escape(" · ".join(meta_parts))}</div>'
        if meta_parts
        else ""
    )

    badge_html = ""
    if medicine.get("needs_review"):
        frequency_raw = medicine.get("frequency_raw", "")
        raw_html = (
            f'<span class="frequency-raw">{escape(frequency_raw)}</span>'
            if frequency_raw
            else ""
        )
        badge_html = (
            '<div class="review-badge">Timing unclear — ask your pharmacist '
            f"{raw_html}</div>"
        )

    notes = medicine.get("notes", "")
    notes_html = f'<div class="medicine-note">{escape(notes)}</div>' if notes else ""
    instruction = medicine.get("instruction") or "Instruction not available yet."
    romanized = medicine.get("romanized") or ""
    romanized_html = (
        f'<div class="medicine-romanized">{escape(romanized)}</div>' if romanized else ""
    )

    return f"""
    <div class="medicine-card">
        <div class="medicine-name">{escape(medicine.get("name", "Medicine"))}</div>
        <div class="medicine-dose">{escape(medicine.get("dose", "Dose not listed"))}</div>
        {quantity_html}
        {meta_html}
        {badge_html}
        <div class="medicine-instruction">{escape(instruction)}</div>
        {romanized_html}
        {notes_html}
    </div>
    """


def render_extras(schedule):
    """Medicines that do not live in a time bucket: as-needed (SOS) ones and
    ones whose timing we could not interpret (needs_review)."""
    medicines = schedule.get("medicines", [])
    sos = [m for m in medicines if m.get("as_needed")]
    review = [m for m in medicines if m.get("needs_review") and not m.get("as_needed")]

    sections = []
    if sos:
        cards = "\n".join(render_medicine_card(medicine) for medicine in sos)
        sections.append(
            f"""
    <div class="tile schedule-tile purple">
        <div class="tile-icon star"></div>
        <div class="tile-title">When needed (SOS)</div>
        <div class="tile-subtitle">Take only when required</div>
        <div class="medicine-list">{cards}</div>
    </div>
    """
        )
    if review:
        cards = "\n".join(render_medicine_card(medicine) for medicine in review)
        sections.append(
            f"""
    <div class="tile schedule-tile amber">
        <div class="tile-icon question"></div>
        <div class="tile-title">Please double-check</div>
        <div class="tile-subtitle">Confirm timing with your pharmacist</div>
        <div class="medicine-list">{cards}</div>
    </div>
    """
        )

    if not sections:
        return ""
    return f'<div class="extras-row">{"".join(sections)}</div>'


def initial_bucket(bucket):
    return render_bucket({"medicines": []}, bucket)


def initial_extras():
    return ""


def render_all_buckets(schedule):
    return [render_bucket(schedule, bucket) for bucket in TIME_BUCKETS]
