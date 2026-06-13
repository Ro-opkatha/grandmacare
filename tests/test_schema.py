from backend.schema import parse_cards_text, parse_pill_text, truncate_transcript


class TestParseCardsText:
    def test_single_card(self):
        text = """MEDICINE: Paracetamol
DOSE: 500 mg
WHEN: 1-0-1 after food
TAKE: Take one tablet morning and night, after eating.
SAY: Take one tablet morning and night, after eating.
NOTE: for 5 days"""
        cards = parse_cards_text(text)
        assert len(cards) == 1
        assert cards[0]["name"] == "Paracetamol"
        assert cards[0]["dose"] == "500 mg"
        assert cards[0]["timing"] == "1-0-1 after food"
        assert cards[0]["instruction"].startswith("Take one tablet")
        assert cards[0]["notes"] == "for 5 days"

    def test_multiple_cards(self):
        text = """MEDICINE: A
WHEN: morning

MEDICINE: B
WHEN: night"""
        cards = parse_cards_text(text)
        assert [c["name"] for c in cards] == ["A", "B"]
        assert cards[1]["timing"] == "night"

    def test_missing_fields_default_empty(self):
        cards = parse_cards_text("MEDICINE: OnlyName")
        assert cards[0]["name"] == "OnlyName"
        assert cards[0]["dose"] == ""
        assert cards[0]["timing"] == ""

    def test_key_synonyms(self):
        text = """NAME: X
TIMING: before lunch
INSTRUCTION: take it
ROMANIZED: take it
NOTES: n"""
        cards = parse_cards_text(text)
        assert cards[0]["name"] == "X"
        assert cards[0]["timing"] == "before lunch"
        assert cards[0]["instruction"] == "take it"
        assert cards[0]["romanized"] == "take it"
        assert cards[0]["notes"] == "n"

    def test_markdown_noise_tolerated(self):
        text = """- **MEDICINE:** Crocin
* **WHEN:** at bedtime"""
        cards = parse_cards_text(text)
        assert cards[0]["name"] == "Crocin"
        assert cards[0]["timing"] == "at bedtime"

    def test_case_insensitive_keys(self):
        cards = parse_cards_text("medicine: x\nwhen: bd")
        assert cards[0]["name"] == "x"
        assert cards[0]["timing"] == "bd"

    def test_junk_before_first_card_ignored(self):
        text = """Here are the cards you asked for:

MEDICINE: A
WHEN: morning"""
        cards = parse_cards_text(text)
        assert len(cards) == 1

    def test_wrapped_instruction_continues(self):
        text = """MEDICINE: A
TAKE: Take one tablet
every morning after breakfast."""
        cards = parse_cards_text(text)
        assert cards[0]["instruction"] == "Take one tablet every morning after breakfast."

    def test_continuation_stops_at_blank_line(self):
        text = """MEDICINE: A
TAKE: Take one tablet

this trailing chatter is ignored"""
        cards = parse_cards_text(text)
        assert cards[0]["instruction"] == "Take one tablet"

    def test_nameless_card_dropped(self):
        cards = parse_cards_text("MEDICINE:\nWHEN: morning")
        assert cards == []

    def test_empty_input(self):
        assert parse_cards_text("") == []
        assert parse_cards_text(None) == []

    def test_no_labels_at_all(self):
        assert parse_cards_text("The patient should rest and drink water.") == []

    def test_dash_separator_accepted(self):
        cards = parse_cards_text("MEDICINE - Crocin\nWHEN - at night")
        assert cards[0]["name"] == "Crocin"
        assert cards[0]["timing"] == "at night"


class TestParsePillText:
    def test_matched(self):
        text = """MATCH: Paracetamol
ANSWER: This is your fever medicine.
SAY: This is your fever medicine."""
        result = parse_pill_text(text)
        assert result["matched"] is True
        assert result["medicine_name"] == "Paracetamol"
        assert result["answer"] == "This is your fever medicine."
        assert result["romanized"] == "This is your fever medicine."

    def test_none_means_no_match(self):
        result = parse_pill_text("MATCH: NONE\nANSWER: Not on your prescription.")
        assert result["matched"] is False
        assert result["medicine_name"] == ""
        assert result["answer"] == "Not on your prescription."

    def test_no_labels_falls_back_to_raw_answer(self):
        result = parse_pill_text("This looks like Crocin, take it at night.")
        assert result["matched"] is False
        assert result["answer"] == "This looks like Crocin, take it at night."

    def test_wrapped_answer_continues(self):
        text = """MATCH: A
ANSWER: First part
second part."""
        result = parse_pill_text(text)
        assert result["answer"] == "First part second part."

    def test_empty_input(self):
        result = parse_pill_text("")
        assert result["matched"] is False
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
