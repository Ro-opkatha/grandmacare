import pytest

from backend.schema import (
    extract_json,
    normalize_medicines,
    normalize_pill_match,
    truncate_transcript,
)


class TestExtractJson:
    def test_bare_json(self):
        assert extract_json('{"medicines": []}') == {"medicines": []}

    def test_fenced_json(self):
        text = 'Here you go:\n```json\n{"medicines": []}\n```\nDone.'
        assert extract_json(text) == {"medicines": []}

    def test_fence_without_language_tag(self):
        text = '```\n{"a": 1}\n```'
        assert extract_json(text) == {"a": 1}

    def test_json_with_surrounding_prose(self):
        text = 'Sure! {"medicines": [{"name": "X"}]} Hope that helps.'
        assert extract_json(text) == {"medicines": [{"name": "X"}]}

    def test_nested_braces(self):
        text = 'prefix {"a": {"b": {"c": 1}}} suffix'
        assert extract_json(text) == {"a": {"b": {"c": 1}}}

    def test_dict_passthrough(self):
        assert extract_json({"a": 1}) == {"a": 1}

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            extract_json("")

    def test_none_raises(self):
        with pytest.raises(ValueError):
            extract_json(None)

    def test_garbage_raises(self):
        with pytest.raises(ValueError):
            extract_json("not json at all")

    def test_json_array_raises(self):
        with pytest.raises(ValueError):
            extract_json("[1, 2, 3]")


class TestNormalizeMedicines:
    def test_full_payload_passes_through(self):
        payload = {
            "medicines": [
                {
                    "name": "Amoxicillin",
                    "dose": "500 mg",
                    "timing": "1-0-1 after food",
                    "timing_label": "Morning and night",
                    "instruction": "খাবারের পরে খান",
                    "romanized": "khabarer pore khan",
                    "notes": "for 5 days",
                }
            ]
        }
        result = normalize_medicines(payload)
        assert result == payload

    def test_missing_fields_get_defaults(self):
        result = normalize_medicines({"medicines": [{"name": "Crocin"}]})
        medicine = result["medicines"][0]
        assert medicine["name"] == "Crocin"
        for field in ("dose", "timing", "timing_label", "instruction", "romanized", "notes"):
            assert medicine[field] == ""

    def test_non_dict_items_skipped(self):
        result = normalize_medicines({"medicines": ["junk", 42, None, {"name": "X"}]})
        assert len(result["medicines"]) == 1

    def test_numeric_values_coerced_to_strings(self):
        result = normalize_medicines({"medicines": [{"name": "X", "dose": 500}]})
        assert result["medicines"][0]["dose"] == "500"

    def test_nameless_and_timingless_entry_dropped(self):
        result = normalize_medicines({"medicines": [{"notes": "Dr. Sharma Clinic"}]})
        assert result["medicines"] == []

    def test_nameless_with_timing_kept_with_placeholder_name(self):
        result = normalize_medicines({"medicines": [{"timing": "before lunch"}]})
        assert result["medicines"][0]["name"] == "Medicine"

    def test_non_dict_payload(self):
        assert normalize_medicines("junk") == {"medicines": []}
        assert normalize_medicines(None) == {"medicines": []}

    def test_non_list_medicines(self):
        assert normalize_medicines({"medicines": "junk"}) == {"medicines": []}

    def test_whitespace_stripped(self):
        result = normalize_medicines({"medicines": [{"name": "  X  ", "timing": " bd "}]})
        assert result["medicines"][0]["name"] == "X"
        assert result["medicines"][0]["timing"] == "bd"


class TestNormalizePillMatch:
    def test_matched_result(self):
        result = normalize_pill_match(
            {"matched": True, "medicine_name": "Crocin", "answer": "A", "romanized": "B"}
        )
        assert result == {
            "matched": True,
            "medicine_name": "Crocin",
            "answer": "A",
            "romanized": "B",
        }

    def test_missing_matched_defaults_false(self):
        assert normalize_pill_match({})["matched"] is False

    def test_string_true_coerced(self):
        assert normalize_pill_match({"matched": "true"})["matched"] is True
        assert normalize_pill_match({"matched": "True"})["matched"] is True

    def test_string_false_coerced(self):
        assert normalize_pill_match({"matched": "false"})["matched"] is False

    def test_non_dict_payload(self):
        result = normalize_pill_match(None)
        assert result["matched"] is False
        assert result["answer"] == ""

    def test_none_fields_become_empty_strings(self):
        result = normalize_pill_match({"matched": True, "answer": None})
        assert result["answer"] == ""


class TestTruncateTranscript:
    def test_short_text_unchanged(self):
        assert truncate_transcript("hello") == "hello"

    def test_long_text_truncated_with_marker(self):
        text = "x" * 3000
        result = truncate_transcript(text, max_chars=2500)
        assert result.endswith("[transcript truncated]")
        assert len(result) == 2500 + len("\n[transcript truncated]")

    def test_exact_limit_unchanged(self):
        text = "x" * 2500
        assert truncate_transcript(text, max_chars=2500) == text

    def test_none_becomes_empty(self):
        assert truncate_transcript(None) == ""
