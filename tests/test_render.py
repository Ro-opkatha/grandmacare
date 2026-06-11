from backend.render import initial_cards, render_answer_card, render_cards


def card(**overrides):
    base = {
        "name": "Opox-CV",
        "dose": "200mg",
        "when": "Morning and night, after food",
        "written": "1-0-1 a/f x 5 days",
        "explanation": "Take 1 tablet in the morning and 1 at night, after food.",
        "unclear": False,
    }
    base.update(overrides)
    return base


def test_card_shows_all_fields():
    html = render_cards({"medicines": [card()]})
    assert "Opox-CV" in html
    assert "200mg" in html
    assert "Morning and night, after food" in html
    assert "1-0-1 a/f x 5 days" in html
    assert "Take 1 tablet in the morning" in html
    assert "review-badge" not in html


def test_one_card_per_medicine():
    html = render_cards({"medicines": [card(), card(name="Pantop", when="Before sleep")]})
    assert html.count("medicine-card") == 2
    assert "Before sleep" in html


def test_unclear_card_gets_pharmacist_badge():
    html = render_cards({"medicines": [card(unclear=True)]})
    assert "review-badge" in html
    assert "pharmacist" in html


def test_model_text_is_html_escaped():
    html = render_cards(
        {"medicines": [card(name='<script>alert("x")</script>', when="<b>now</b>")]}
    )
    assert "<script>" not in html
    assert "<b>" not in html
    assert "&lt;script&gt;" in html


def test_empty_and_malformed_input_render_empty_state():
    assert "empty-state" in render_cards({"medicines": []})
    assert "empty-state" in render_cards(None)
    assert "empty-state" in initial_cards()


def test_missing_optional_fields_render_without_artifacts():
    html = render_cards({"medicines": [card(dose="", when="", written="", explanation="")]})
    assert "medicine-dose" not in html
    assert "when-line" not in html
    assert "written-line" not in html
    assert "Opox-CV" in html


def test_answer_card_escapes_and_wraps():
    html = render_answer_card("Take <one> tablet now.")
    assert "answer-card" in html
    assert "&lt;one&gt;" in html
    assert render_answer_card("") == ""
