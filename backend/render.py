from html import escape

from backend.schema import TIME_BUCKETS


BUCKET_META = {
    "morning": ("Morning", "sun", "blue"),
    "afternoon": ("Afternoon", "clock", "orange"),
    "evening": ("Evening", "sunset", "teal"),
    "night": ("Night", "moon", "green"),
}


def render_bucket(schedule, bucket):
    title, icon_class, color = BUCKET_META[bucket]
    medicines = [
        medicine
        for medicine in schedule.get("medicines", [])
        if bucket in medicine.get("schedule", [])
    ]

    if medicines:
        cards = "\n".join(render_medicine_card(medicine) for medicine in medicines)
    else:
        cards = '<div class="empty-state">No medicines listed for this time.</div>'

    return f"""
    <div class="tile schedule-tile {color}">
        <div class="tile-icon {icon_class}"></div>
        <div class="tile-title">{title}</div>
        <div class="medicine-list">{cards}</div>
    </div>
    """


def render_medicine_card(medicine):
    notes = medicine.get("notes", "")
    notes_html = f'<div class="medicine-note">{escape(notes)}</div>' if notes else ""
    instruction = medicine.get("instruction") or "Instruction translation pending."
    romanized = medicine.get("romanized") or "Romanized instruction pending."

    return f"""
    <div class="medicine-card">
        <div class="medicine-name">{escape(medicine.get("name", "Medicine"))}</div>
        <div class="medicine-dose">{escape(medicine.get("dose", "Dose not listed"))}</div>
        <div class="medicine-instruction">{escape(instruction)}</div>
        <div class="medicine-romanized">{escape(romanized)}</div>
        {notes_html}
    </div>
    """


def initial_bucket(bucket):
    return render_bucket({"medicines": []}, bucket)


def render_all_buckets(schedule):
    return [render_bucket(schedule, bucket) for bucket in TIME_BUCKETS]
