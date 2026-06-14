from backend.render import (
    GROUP_COLORS,
    empty_transcript,
    empty_view,
    render_card_body,
    render_freestyle,
    render_group_header,
    render_notice,
    render_pill_result,
    render_transcript,
    say_text,
    timing_icon,
)


def med(**overrides):
    base = {
        "name": "Medicine",
        "dose": "",
        "timing": "",
        "timing_label": "",
        "instruction": "",
        "romanized": "",
        "notes": "",
    }
    base.update(overrides)
    return base


class TestCardBody:
    def test_contains_name(self):
        assert "Amoxicillin" in render_card_body(med(name="Amoxicillin"))

    def test_name_escaped(self):
        html = render_card_body(med(name="<script>alert(1)</script>"))
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_timing_badge_present_when_timing_given(self):
        html = render_card_body(med(timing="1-0-1 after food"))
        assert "timing-badge" in html
        assert "1-0-1 after food" in html

    def test_timing_badge_absent_when_empty(self):
        assert "timing-badge" not in render_card_body(med())

    def test_timing_escaped(self):
        html = render_card_body(med(timing='<img src=x onerror="x">'))
        assert "<img" not in html

    def test_notes_escaped(self):
        html = render_card_body(med(notes="<b>bold</b>"))
        assert "<b>" not in html

    def test_no_buttons_or_legacy_js_hooks(self):
        # Cards are now visual-only; buttons/reminders are native components.
        html = render_card_body(med(name="Amoxicillin", romanized="sokale nin"))
        assert "<button" not in html
        assert "data-gc-" not in html
        assert 'type="time"' not in html


class TestSayText:
    def test_prefers_romanized(self):
        assert say_text(med(romanized="sokale nin", instruction="take am")) == "sokale nin"

    def test_falls_back_to_instruction(self):
        assert say_text(med(romanized="", instruction="Take in the morning")) == "Take in the morning"

    def test_falls_back_to_name(self):
        assert say_text(med(name="Breezy", romanized="", instruction="")) == "Breezy"


class TestGroupHeader:
    def test_label_and_color(self):
        html = render_group_header("At bedtime", "purple")
        assert "At bedtime" in html
        assert "purple" in html
        assert "moon" in html  # timing_icon for bedtime

    def test_label_escaped(self):
        assert "<svg" not in render_group_header("<svg onload=x>", "blue")


class TestTranscript:
    def test_escaped(self):
        html = render_transcript("Tab <script> 1-0-1")
        assert "<script>" not in html
        assert "transcript-box" in html

    def test_empty_shows_placeholder(self):
        assert "empty-state" in render_transcript("")
        assert "empty-state" in render_transcript(None)


class TestPillResult:
    def test_matched_class(self):
        html = render_pill_result(
            {"matched": True, "medicine_name": "Crocin", "answer": "Take it now", "romanized": "r"}
        )
        assert "matched" in html
        assert "Crocin" in html

    def test_not_found_class(self):
        html = render_pill_result({"matched": False, "medicine_name": "", "answer": "", "romanized": ""})
        assert "not-found" in html
        assert "pharmacist" in html

    def test_answer_escaped(self):
        html = render_pill_result(
            {"matched": True, "medicine_name": "X", "answer": "<script>", "romanized": ""}
        )
        assert "<script>" not in html


class TestFreestyle:
    def test_escaped(self):
        html = render_freestyle("MEDICINE: <script>alert(1)</script>")
        assert "<script>" not in html
        assert "freestyle" in html

    def test_empty_shows_empty_state(self):
        assert "empty-state" in render_freestyle("")
        assert "empty-state" in render_freestyle(None)


class TestHelpers:
    def test_timing_icons(self):
        assert timing_icon("Morning and night") == "sun"
        assert timing_icon("At bedtime") == "moon"
        assert timing_icon("After lunch") == "clock"
        assert timing_icon("When needed") == "pill"
        assert timing_icon("") == "pill"

    def test_group_colors_available(self):
        assert len(GROUP_COLORS) >= 1

    def test_empty_states(self):
        assert "empty-state" in empty_view()
        assert "empty-state" in empty_transcript()

    def test_notice_escaped(self):
        assert "<b>" not in render_notice("<b>hi</b>")
