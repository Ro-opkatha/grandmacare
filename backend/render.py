from html import escape


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


def say_text(medicine):
    """The text a card's 🔊 button asks VoxCPM to speak: the romanized line
    (it spells out Hindi/Bengali sounds for the English-only model), else the
    English instruction, else the medicine name."""
    return (
        medicine.get("romanized")
        or medicine.get("instruction")
        or medicine.get("name", "Medicine")
    )


def render_card_body(medicine):
    """Visual-only card markup: name, dose, timing, instruction, romanized,
    notes. The 🔊 Listen and reminder controls are native Gradio components
    emitted alongside this by the @gr.render loop in app.py — no buttons or
    inline JS live here."""
    timing = medicine.get("timing", "")
    timing_html = (
        f'<div class="timing-badge">Doctor wrote: {escape(timing)}</div>'
        if timing
        else ""
    )
    notes = medicine.get("notes", "")
    notes_html = f'<div class="medicine-note">{escape(notes)}</div>' if notes else ""
    instruction = medicine.get("instruction") or "Instruction pending."
    instruction_html = f'<div class="medicine-instruction">{escape(instruction)}</div>'
    romanized = medicine.get("romanized", "")
    romanized_html = (
        f'<div class="medicine-romanized">{escape(romanized)}</div>' if romanized else ""
    )
    dose = medicine.get("dose", "")
    dose_html = f'<div class="medicine-dose">{escape(dose)}</div>' if dose else ""

    return f"""
    <div class="medicine-card">
        <div class="medicine-name">{escape(medicine.get("name", "Medicine"))}</div>
        {dose_html}
        {timing_html}
        {instruction_html}
        {romanized_html}
        {notes_html}
    </div>
    """


def render_group_header(label, color):
    """Colored timing-group header for the 'By time' view. The cards (with
    their native controls) are rendered as components beneath it."""
    return (
        f'<div class="tile schedule-tile {color} group-header">'
        f'<div class="tile-icon {timing_icon(label)}"></div>'
        f'<div class="tile-title">{escape(label)}</div>'
        "</div>"
    )


def alarm_caveat():
    return (
        '<div class="alarm-caveat">🔔 Reminders ring only while this GrandmaCare '
        "page stays open and connected. Keep the tab open to be reminded.</div>"
    )


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


def render_freestyle(text):
    body = str(text or "").strip()
    if not body:
        return empty_view()
    return f'<div class="medicine-card freestyle">{escape(body)}</div>'


def render_notice(message):
    return f'<div class="pill-result not-found"><div class="medicine-instruction">{escape(message)}</div></div>'


def empty_view():
    return '<div class="empty-state dark">No medicines yet. Upload a prescription and press Analyze.</div>'


def empty_transcript():
    return '<div class="empty-state dark">The digital copy of your prescription will appear here.</div>'
