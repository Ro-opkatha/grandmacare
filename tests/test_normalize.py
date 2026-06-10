"""GPU-free tests for the deterministic prescription-notation interpreter.

Run with either:
    python -m unittest discover -s tests -v
    python -m pytest tests
"""

import unittest

from backend.normalize import (
    build_instruction,
    format_quantity,
    interpret_duration,
    interpret_frequency,
    interpret_meal_relation,
    normalize_medicine,
    normalize_transcription,
)
from backend.schema import (
    merge_translation,
    normalize_schedule,
    parse_raw_json,
    uses_expected_script,
)


class TestDosePatterns(unittest.TestCase):
    def test_1_0_1(self):
        result = interpret_frequency("1-0-1")
        self.assertTrue(result["understood"])
        self.assertEqual(result["buckets"], ["morning", "night"])
        self.assertEqual(result["quantities"], {"morning": 1.0, "night": 1.0})

    def test_1_1_1(self):
        result = interpret_frequency("1-1-1")
        self.assertTrue(result["understood"])
        self.assertEqual(result["buckets"], ["morning", "afternoon", "night"])

    def test_four_slots(self):
        result = interpret_frequency("1-0-0-1")
        self.assertTrue(result["understood"])
        self.assertEqual(result["buckets"], ["morning", "night"])

    def test_half_unicode(self):
        result = interpret_frequency("½-0-½")
        self.assertTrue(result["understood"])
        self.assertEqual(result["buckets"], ["morning", "night"])
        self.assertEqual(result["quantities"], {"morning": 0.5, "night": 0.5})

    def test_half_slash(self):
        result = interpret_frequency("1/2-0-1/2")
        self.assertTrue(result["understood"])
        self.assertEqual(result["quantities"], {"morning": 0.5, "night": 0.5})

    def test_en_dash_and_spaces(self):
        result = interpret_frequency("1 – 0 – 1")
        self.assertTrue(result["understood"])
        self.assertEqual(result["buckets"], ["morning", "night"])


class TestAbbreviations(unittest.TestCase):
    def test_od(self):
        self.assertEqual(interpret_frequency("OD")["buckets"], ["morning"])

    def test_bd(self):
        self.assertEqual(interpret_frequency("BD")["buckets"], ["morning", "night"])

    def test_tds(self):
        self.assertEqual(
            interpret_frequency("TDS")["buckets"], ["morning", "afternoon", "night"]
        )

    def test_qid(self):
        self.assertEqual(
            interpret_frequency("QID")["buckets"],
            ["morning", "afternoon", "evening", "night"],
        )

    def test_hs(self):
        self.assertEqual(interpret_frequency("HS")["buckets"], ["night"])

    def test_all_understood(self):
        for raw in ("OD", "BD", "TDS", "QID", "HS"):
            self.assertTrue(interpret_frequency(raw)["understood"], raw)


class TestAsNeededAndPlainEnglish(unittest.TestCase):
    def test_sos(self):
        result = interpret_frequency("SOS")
        self.assertTrue(result["understood"])
        self.assertTrue(result["as_needed"])
        self.assertEqual(result["buckets"], [])

    def test_morning_and_night(self):
        result = interpret_frequency("morning and night")
        self.assertTrue(result["understood"])
        self.assertEqual(result["buckets"], ["morning", "night"])

    def test_at_bedtime(self):
        result = interpret_frequency("at bedtime")
        self.assertTrue(result["understood"])
        self.assertEqual(result["buckets"], ["night"])

    def test_unknown_notation(self):
        result = interpret_frequency("q4h alt die")
        self.assertFalse(result["understood"])
        self.assertEqual(result["buckets"], [])

    def test_empty(self):
        self.assertFalse(interpret_frequency("")["understood"])


class TestMealRelation(unittest.TestCase):
    def test_ac(self):
        self.assertEqual(interpret_meal_relation("AC"), "before_food")

    def test_pc(self):
        self.assertEqual(interpret_meal_relation("PC"), "after_food")

    def test_after_food(self):
        self.assertEqual(interpret_meal_relation("after food"), "after_food")

    def test_empty_stomach(self):
        self.assertEqual(interpret_meal_relation("empty stomach"), "before_food")

    def test_none(self):
        self.assertEqual(interpret_meal_relation("no meal info"), "")


class TestDuration(unittest.TestCase):
    def test_x_5_days(self):
        self.assertEqual(interpret_duration("x 5 days"), "5 days")

    def test_for_2_weeks(self):
        self.assertEqual(interpret_duration("for 2 weeks"), "2 weeks")

    def test_singular(self):
        self.assertEqual(interpret_duration("x 1 days"), "1 day")

    def test_din(self):
        self.assertEqual(interpret_duration("x 5 din"), "5 days")

    def test_none(self):
        self.assertEqual(interpret_duration("take with water"), "")


class TestNormalizeMedicine(unittest.TestCase):
    def test_full_entry(self):
        entry = normalize_medicine(
            {
                "name": "Pantoprazole",
                "dose": "40 mg",
                "frequency_raw": "1-0-1",
                "meal_raw": "AC",
                "duration_raw": "x 5 days",
                "notes": "",
            }
        )
        self.assertEqual(entry["schedule"], ["morning", "night"])
        self.assertEqual(entry["quantities"], {"morning": 1.0, "night": 1.0})
        self.assertEqual(entry["meal_relation"], "before_food")
        self.assertEqual(entry["duration"], "5 days")
        self.assertEqual(entry["frequency_raw"], "1-0-1")
        self.assertFalse(entry["needs_review"])
        self.assertFalse(entry["as_needed"])

    def test_unknown_flags_for_review(self):
        entry = normalize_medicine(
            {"name": "Mystery", "dose": "10 mg", "frequency_raw": "q4h alt die"}
        )
        self.assertTrue(entry["needs_review"])
        self.assertEqual(entry["schedule"], [])
        self.assertIn("q4h alt die", entry["notes"])
        self.assertIn("pharmacist", entry["notes"])

    def test_sos_entry(self):
        entry = normalize_medicine(
            {"name": "Paracetamol", "dose": "650 mg", "frequency_raw": "SOS"}
        )
        self.assertTrue(entry["as_needed"])
        self.assertFalse(entry["needs_review"])
        self.assertEqual(entry["schedule"], [])

    def test_transcription_payload(self):
        result = normalize_transcription(
            {
                "medicines": [
                    {"name": "A", "frequency_raw": "BD"},
                    "not-a-dict",
                    {"name": "B", "frequency_raw": "??"},
                ]
            }
        )
        self.assertEqual(len(result["medicines"]), 2)
        self.assertFalse(result["medicines"][0]["needs_review"])
        self.assertTrue(result["medicines"][1]["needs_review"])

    def test_non_dict_payload(self):
        self.assertEqual(normalize_transcription(None), {"medicines": []})


class TestRescuedPatterns(unittest.TestCase):
    """MiniCPM sometimes transcribes the slot pattern into the wrong field
    (seen live: '1-1-1 10f.' in the dose). Only explicit patterns with
    believable tablet counts are rescued — never abbreviations."""

    def test_pattern_in_dose_field(self):
        entry = normalize_medicine(
            {"name": "T. Alltrose SP", "dose": "1-1-1 10f.", "frequency_raw": ""}
        )
        self.assertEqual(entry["schedule"], ["morning", "afternoon", "night"])
        self.assertFalse(entry["needs_review"])
        self.assertEqual(entry["frequency_raw"], "1-1-1")

    def test_pattern_in_name_field(self):
        entry = normalize_medicine({"name": "T. Breezy 0-0-1", "frequency_raw": ""})
        self.assertEqual(entry["schedule"], ["night"])
        self.assertFalse(entry["needs_review"])

    def test_date_is_not_a_dose(self):
        entry = normalize_medicine(
            {"name": "X", "notes": "review on 12-05-25", "frequency_raw": ""}
        )
        self.assertTrue(entry["needs_review"])
        self.assertEqual(entry["schedule"], [])

    def test_explicit_frequency_raw_wins(self):
        entry = normalize_medicine(
            {"name": "X", "dose": "1-1-1", "frequency_raw": "BD"}
        )
        self.assertEqual(entry["schedule"], ["morning", "night"])

    def test_abbreviation_in_dose_is_not_rescued(self):
        entry = normalize_medicine({"name": "X", "dose": "10 mg OD", "frequency_raw": ""})
        self.assertTrue(entry["needs_review"])


class TestBuildInstruction(unittest.TestCase):
    def test_full_entry(self):
        entry = normalize_medicine(
            {
                "name": "Pantoprazole",
                "dose": "40 mg",
                "frequency_raw": "1-0-1",
                "meal_raw": "PC",
                "duration_raw": "x 5 days",
            }
        )
        self.assertEqual(
            build_instruction(entry),
            "Take 1 tablet in the morning and 1 tablet at night, after food, for 5 days.",
        )

    def test_half_tablet(self):
        entry = normalize_medicine({"name": "Metformin", "frequency_raw": "½-0-½"})
        self.assertEqual(
            build_instruction(entry),
            "Take ½ tablet in the morning and ½ tablet at night.",
        )

    def test_abbreviation_without_quantities(self):
        entry = normalize_medicine({"name": "X", "frequency_raw": "BD"})
        self.assertEqual(
            build_instruction(entry),
            "Take this medicine in the morning and at night.",
        )

    def test_needs_review_never_composes_a_dose(self):
        entry = normalize_medicine({"name": "X", "frequency_raw": "q4h alt die"})
        instruction = build_instruction(entry)
        self.assertIn("pharmacist", instruction)
        self.assertFalse(instruction.startswith("Take"))

    def test_as_needed(self):
        entry = normalize_medicine(
            {"name": "Paracetamol", "frequency_raw": "SOS", "meal_raw": "after food"}
        )
        instruction = build_instruction(entry)
        self.assertIn("only when you need it", instruction)
        self.assertIn("after food", instruction)

    def test_format_quantity(self):
        self.assertEqual(format_quantity(0.5), "½")
        self.assertEqual(format_quantity(1.0), "1")
        self.assertEqual(format_quantity(1.5), "1½")


class TestScriptValidation(unittest.TestCase):
    def test_devanagari(self):
        self.assertTrue(uses_expected_script("खाने के बाद", "Devanagari"))
        self.assertFalse(uses_expected_script("Téng yi tiě bǎo", "Devanagari"))

    def test_bengali(self):
        self.assertTrue(uses_expected_script("খাবার পরে", "Bengali"))
        self.assertFalse(uses_expected_script("khabar pore", "Bengali"))

    def test_unmapped_script_requires_text(self):
        self.assertTrue(uses_expected_script("Take 1 tablet", "English"))
        self.assertFalse(uses_expected_script("   ", "English"))


class TestSchemaPreservesNewFields(unittest.TestCase):
    def _entry(self):
        return normalize_medicine(
            {
                "name": "Metformin",
                "dose": "500 mg",
                "frequency_raw": "½-0-½",
                "meal_raw": "PC",
                "duration_raw": "for 2 weeks",
            }
        )

    def test_normalize_schedule_keeps_fields(self):
        cleaned = normalize_schedule({"medicines": [self._entry()]})
        medicine = cleaned["medicines"][0]
        self.assertEqual(medicine["quantities"], {"morning": 0.5, "night": 0.5})
        self.assertEqual(medicine["meal_relation"], "after_food")
        self.assertEqual(medicine["duration"], "2 weeks")
        self.assertEqual(medicine["frequency_raw"], "½-0-½")
        self.assertFalse(medicine["needs_review"])
        self.assertFalse(medicine["as_needed"])

    def test_merge_translation_keeps_fields(self):
        base = {"medicines": [self._entry()]}
        translated = {
            "medicines": [{"instruction": "खाने के बाद", "romanized": "khane ke baad"}]
        }
        merged = merge_translation(base, translated)
        medicine = merged["medicines"][0]
        self.assertEqual(medicine["instruction"], "खाने के बाद")
        self.assertEqual(medicine["romanized"], "khane ke baad")
        self.assertEqual(medicine["quantities"], {"morning": 0.5, "night": 0.5})
        self.assertEqual(medicine["meal_relation"], "after_food")

    def test_parse_raw_json_keeps_raw_fields(self):
        text = '```json\n{"medicines": [{"name": "X", "frequency_raw": "1-0-1"}]}\n```'
        raw = parse_raw_json(text)
        self.assertEqual(raw["medicines"][0]["frequency_raw"], "1-0-1")

    def test_parse_raw_json_brace_slicing(self):
        text = 'Here you go: {"medicines": []} hope that helps'
        self.assertEqual(parse_raw_json(text), {"medicines": []})


if __name__ == "__main__":
    unittest.main()
