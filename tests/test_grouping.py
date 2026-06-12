from backend.schema import group_by_timing, grouping_key


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


class TestGroupingKey:
    def test_uses_timing_label_first(self):
        assert grouping_key(med(timing_label="Morning and night", timing="1-0-1")) == "morning and night"

    def test_falls_back_to_timing(self):
        assert grouping_key(med(timing="before lunch")) == "before lunch"

    def test_falls_back_to_as_written(self):
        assert grouping_key(med()) == "as written"

    def test_whitespace_collapsed(self):
        assert grouping_key(med(timing_label="  Morning   AND  night ")) == "morning and night"


class TestGroupByTiming:
    def test_empty_list(self):
        assert group_by_timing([]) == []

    def test_first_seen_order_preserved(self):
        medicines = [
            med(name="A", timing_label="At bedtime"),
            med(name="B", timing_label="Before lunch"),
            med(name="C", timing_label="At bedtime"),
        ]
        groups = group_by_timing(medicines)
        assert [label for label, _ in groups] == ["At bedtime", "Before lunch"]
        assert [m["name"] for m in groups[0][1]] == ["A", "C"]

    def test_case_insensitive_merge(self):
        medicines = [
            med(name="A", timing_label="Morning and night"),
            med(name="B", timing_label="morning AND night "),
        ]
        groups = group_by_timing(medicines)
        assert len(groups) == 1
        assert len(groups[0][1]) == 2

    def test_display_label_keeps_first_seen_casing(self):
        medicines = [
            med(name="A", timing_label="MORNING"),
            med(name="B", timing_label="morning"),
        ]
        groups = group_by_timing(medicines)
        assert groups[0][0] == "MORNING"

    def test_fallback_group_label(self):
        groups = group_by_timing([med(name="A")])
        assert groups[0][0] == "As written"

    def test_timing_used_when_label_missing(self):
        groups = group_by_timing([med(name="A", timing="1-0-1 after food")])
        assert groups[0][0] == "1-0-1 after food"
