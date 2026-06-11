"""
backend/render.py — deterministic HTML for the adaptive cards.

One flat list of cards, one per medicine; each card carries its own timing
in plain words ("Before sleep", "After lunch", "Every 6 hours" — whatever
the prescription says). No fixed time buckets, no grouping. Every model
string is HTML-escaped here before it reaches the page.
"""

from html import escape


def render_medicine_card(card):
    name = escape(card.get("name") or "Medicine")
    dose = escape(card.get("dose") or "")
    when = escape(card.get("when") or "")
    written = escape(card.get("written") or "")
    explanation = escape(card.get("explanation") or "")

    dose_html = f'<div class="medicine-dose">{dose}</div>' if dose else ""
    when_html = f'<div class="when-line">{when}</div>' if when else ""
    written_html = (
        '<div class="written-line">Written on prescription: '
        f'<span class="frequency-raw">{written}</span></div>'
        if written
        else ""
    )
    explanation_html = (
        f'<div class="medicine-instruction">{explanation}</div>' if explanation else ""
    )
    badge_html = (
        '<div class="review-badge">Not fully readable — '
        "please confirm this one with your pharmacist.</div>"
        if card.get("unclear")
        else ""
    )

    return f"""
    <div class="medicine-card">
        <div class="medicine-name">{name}</div>
        {dose_html}
        {when_html}
        {written_html}
        {badge_html}
        {explanation_html}
    </div>
    """


def render_cards(cards):
    medicines = cards.get("medicines", []) if isinstance(cards, dict) else []
    if not medicines:
        return (
            '<div class="cards-area"><div class="empty-state dark">'
            "No medicines yet — take a photo of the prescription above."
            "</div></div>"
        )
    body = "\n".join(render_medicine_card(card) for card in medicines)
    return f'<div class="cards-area">{body}</div>'


def render_answer_card(text):
    """One BIG, readable card for the brain's reply — large font instead of
    spoken audio, in whatever language the user spoke."""
    if not text:
        return ""
    return f'<div class="answer-card">{escape(text)}</div>'


def initial_cards():
    return render_cards({"medicines": []})
