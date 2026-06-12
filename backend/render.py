from html import escape

from backend.schema import group_by_timing


GROUP_COLORS = ("blue", "orange", "teal", "green", "purple", "red")


def timing_icon(label):
    label = str(label or "").lower()
    if "morning" in label or "breakfast" in label:
        return "sun"
    if "night" in label or "bedtime" in label or "bed" in label:
        return "moon"
    if any(word in label for word in ("food", "meal", "lunch", "dinner")):
        return "clock"
    return "pill"


def render_medicine_card(medicine):
    timing = medicine.get("timing", "")
    timing_html = (
        f'<div class="timing-badge">Doctor wrote: {escape(timing)}</div>'
        if timing
        else ""
    )
    notes = medicine.get("notes", "")
    notes_html = f'<div class="medicine-note">{escape(notes)}</div>' if notes else ""
    instruction = medicine.get("instruction") or "Instruction translation pending."
    romanized = medicine.get("romanized") or "Romanized instruction pending."
    dose = medicine.get("dose", "")
    dose_html = f'<div class="medicine-dose">{escape(dose)}</div>' if dose else ""

    return f"""
    <div class="medicine-card">
        <div class="medicine-name">{escape(medicine.get("name", "Medicine"))}</div>
        {dose_html}
        {timing_html}
        <div class="medicine-instruction">{escape(instruction)}</div>
        <div class="medicine-romanized">{escape(romanized)}</div>
        {notes_html}
    </div>
    """


def render_by_medicine(medicines):
    if not medicines:
        return empty_view()
    cards = "\n".join(render_medicine_card(medicine) for medicine in medicines)
    return f'<div class="medicine-grid">{cards}</div>'


def render_by_time(medicines):
    if not medicines:
        return empty_view()

    tiles = []
    for index, (label, group) in enumerate(group_by_timing(medicines)):
        color = GROUP_COLORS[index % len(GROUP_COLORS)]
        cards = "\n".join(render_medicine_card(medicine) for medicine in group)
        tiles.append(
            f"""
            <div class="tile schedule-tile {color}">
                <div class="tile-icon {timing_icon(label)}"></div>
                <div class="tile-title">{escape(label)}</div>
                <div class="medicine-list">{cards}</div>
            </div>
            """
        )

    return f'<div class="medicine-grid">{"".join(tiles)}</div>'


def render_view(medicines, view):
    if view == "By time":
        return render_by_time(medicines)
    return render_by_medicine(medicines)


def render_transcript(transcript):
    text = str(transcript or "").strip()
    if not text:
        return empty_transcript()
    return f'<div class="transcript-box">{escape(text)}</div>'


def render_pill_result(result):
    answer = result.get("answer") or ""
    romanized = result.get("romanized") or ""
    romanized_html = (
        f'<div class="medicine-romanized">{escape(romanized)}</div>'
        if romanized
        else ""
    )

    if result.get("matched"):
        name = result.get("medicine_name") or "Medicine"
        return f"""
        <div class="pill-result matched">
            <div class="medicine-name">{escape(name)}</div>
            <div class="medicine-instruction">{escape(answer)}</div>
            {romanized_html}
        </div>
        """

    message = answer or "This medicine is not on your prescription. Please ask your pharmacist."
    return f"""
    <div class="pill-result not-found">
        <div class="medicine-instruction">{escape(message)}</div>
        {romanized_html}
    </div>
    """


def render_notice(message):
    return f'<div class="pill-result not-found"><div class="medicine-instruction">{escape(message)}</div></div>'


def empty_view():
    return '<div class="empty-state dark">No medicines yet. Upload a prescription and press Analyze.</div>'


def empty_transcript():
    return '<div class="empty-state dark">The digital copy of your prescription will appear here.</div>'
