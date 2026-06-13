from backend.render import (
    GROUP_COLORS,
    empty_transcript,
    empty_view,
    render_by_medicine,
    render_by_time,
    render_freestyle,
    render_medicine_card,
    render_notice,
    render_pill_result,
    render_transcript,
    render_view,
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


class TestMedicineCard:
    def test_contains_name(self):
        assert "Amoxicillin" in render_medicine_card(med(name="Amoxicillin"))

    def test_name_escaped(self):
        html = render_medicine_card(med(name="<script>alert(1)</script>"))
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_timing_badge_present_when_timing_given(self):
        html = render_medicine_card(med(timing="1-0-1 after food"))
        assert "timing-badge" in html
        assert "1-0-1 after food" in html

    def test_timing_badge_absent_when_empty(self):
        assert "timing-badge" not in render_medicine_card(med())

    def test_timing_escaped(self):
        html = render_medicine_card(med(timing='<img src=x onerror="x">'))
        assert "<img" not in html

    def test_notes_escaped(self):
        html = render_medicine_card(med(notes="<b>bold</b>"))
        assert "<b>" not in html


class TestByMedicine:
    def test_empty_shows_empty_state(self):
        assert "empty-state" in render_by_medicine([])

    def test_one_card_per_medicine(self):
        html = render_by_medicine([med(name="A"), med(name="B"), med(name="C")])
        assert html.count("medicine-card") == 3
        assert "medicine-grid" in html


class TestByTime:
    def test_empty_shows_empty_state(self):
        assert "empty-state" in render_by_time([])

    def test_group_titles_appear(self):
        html = render_by_time(
            [
                med(name="A", timing_label="At bedtime"),
                med(name="B", timing_label="Before lunch"),
            ]
        )
        assert "At bedtime" in html
        assert "Before lunch" in html

    def test_colors_cycle(self):
        medicines = [
            med(name=f"M{i}", timing_label=f"slot {i}")
            for i in range(len(GROUP_COLORS) + 1)
        ]
        html = render_by_time(medicines)
        assert html.count(GROUP_COLORS[0]) == 2

    def test_cards_under_correct_group(self):
        html = render_by_time(
            [
                med(name="Alpha", timing_label="Morning"),
                med(name="Beta", timing_label="Night"),
            ]
        )
        assert html.index("Morning") < html.index("Alpha") < html.index("Night") < html.index("Beta")

    def test_group_label_escaped(self):
        html = render_by_time([med(name="A", timing_label="<svg onload=x>")])
        assert "<svg" not in html


class TestRenderView:
    def test_by_time_dispatch(self):
        medicines = [med(name="A", timing_label="Morning")]
        assert "schedule-tile" in render_view(medicines, "By time")

    def test_by_medicine_dispatch(self):
        medicines = [med(name="A")]
        assert "schedule-tile" not in render_view(medicines, "By medicine")


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

    def test_empty_states(self):
        assert "empty-state" in empty_view()
        assert "empty-state" in empty_transcript()

    def test_notice_escaped(self):
        assert "<b>" not in render_notice("<b>hi</b>")
