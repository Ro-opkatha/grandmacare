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


def render_card_actions(medicine):
    """Voice button + alarm controls. Pure markup + data-* attributes; the
    JS engine (frontend/alarm.js) drives them via event delegation, so this
    stays robust even if Gradio sanitizes the HTML blob (no inline JS here).

    The 🔊 button carries the text to speak in data-gc-say (romanized line for
    Hindi/Bengali, else the English instruction, else the name). Clicking it
    asks the server to synthesize that text on demand with VoxCPM."""
    name = escape(medicine.get("name", "Medicine"))
    say = (
        medicine.get("romanized")
        or medicine.get("instruction")
        or medicine.get("name", "Medicine")
    )
    return f"""
        <div class="card-actions" data-gc-card="{name}">
            <button type="button" class="sound-btn" data-gc-play data-gc-say="{escape(say)}">🔊 Listen</button>
            <div class="alarm-row">
                <input type="time" class="alarm-input" data-gc-alarm-input aria-label="Alarm time for {name}">
                <button type="button" class="alarm-set" data-gc-alarm-set data-gc-med="{name}">Set alarm</button>
                <button type="button" class="alarm-clear" data-gc-alarm-clear data-gc-med="{name}">Clear</button>
                <span class="alarm-status" data-gc-alarm-status></span>
            </div>
        </div>
    """


def render_medicine_card(medicine):
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
        {render_card_actions(medicine)}
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


def alarm_caveat():
    return (
        '<div class="alarm-caveat">🔔 Alarms ring only while this GrandmaCare '
        "page stays open in your browser. Keep the tab open to be reminded.</div>"
    )


def render_view(medicines, view):
    if not medicines:
        return empty_view()
    body = render_by_time(medicines) if view == "By time" else render_by_medicine(medicines)
    return body + alarm_caveat()


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
