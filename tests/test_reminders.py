from backend.reminders import schedule_reminder, split_due


class TestScheduleReminder:
    def test_deadline_is_now_plus_minutes(self):
        alarms, minutes = schedule_reminder([], 30, "Crocin", "kroh sin", now=1000.0)
        assert minutes == 30
        assert alarms == [{"deadline": 1000.0 + 30 * 60, "med": "Crocin", "say": "kroh sin"}]

    def test_appends_without_mutating_input(self):
        original = []
        alarms, _ = schedule_reminder(original, 5, "A", "", now=0.0)
        assert original == []
        assert len(alarms) == 1

    def test_minutes_clamped_to_at_least_one(self):
        _, minutes = schedule_reminder([], 0, "A", "", now=0.0)
        assert minutes == 1
        _, minutes = schedule_reminder([], -10, "A", "", now=0.0)
        assert minutes == 1

    def test_bad_minutes_falls_back_to_one(self):
        _, minutes = schedule_reminder([], None, "A", "", now=0.0)
        assert minutes == 1
        _, minutes = schedule_reminder([], "abc", "A", "", now=0.0)
        assert minutes == 1

    def test_say_defaults_to_empty_string(self):
        alarms, _ = schedule_reminder([], 1, "A", None, now=0.0)
        assert alarms[0]["say"] == ""


class TestSplitDue:
    def test_past_deadline_is_due_and_removed(self):
        alarms = [
            {"deadline": 100.0, "med": "Past", "say": "p"},
            {"deadline": 300.0, "med": "Future", "say": "f"},
        ]
        due, remaining = split_due(alarms, now=200.0)
        assert [a["med"] for a in due] == ["Past"]
        assert [a["med"] for a in remaining] == ["Future"]

    def test_deadline_exactly_now_is_due(self):
        due, remaining = split_due([{"deadline": 200.0, "med": "X", "say": ""}], now=200.0)
        assert len(due) == 1
        assert remaining == []

    def test_empty_and_none(self):
        assert split_due([], now=0.0) == ([], [])
        assert split_due(None, now=0.0) == ([], [])
