import pytest

from backend.schema import empty_cards, parse_cards_json, sanitize_cards


VALID = """
{
  "medicines": [
    {"name": "Opox-CV", "dose": "200mg",
     "when": "Morning and night, after food",
     "written": "1-0-1 a/f x 5 days",
     "explanation": "Take 1 tablet in the morning and 1 at night, after food, for 5 days.",
     "unclear": false}
  ]
}
"""


def test_valid_payload_passes_through():
    cards = parse_cards_json(VALID)
    assert len(cards["medicines"]) == 1
    card = cards["medicines"][0]
    assert card["name"] == "Opox-CV"
    assert card["when"] == "Morning and night, after food"
    assert card["written"] == "1-0-1 a/f x 5 days"
    assert card["unclear"] is False


def test_fenced_json_is_extracted():
    cards = parse_cards_json(f"Here you go:\n```json\n{VALID}\n```\nHope this helps!")
    assert cards["medicines"][0]["name"] == "Opox-CV"


def test_json_embedded_in_prose_is_extracted():
    cards = parse_cards_json(f"Sure! {VALID} Let me know if you need more.")
    assert cards["medicines"][0]["dose"] == "200mg"


def test_dict_input_accepted():
    cards = parse_cards_json({"medicines": [{"name": "Pantop", "when": "Before sleep"}]})
    assert cards["medicines"][0]["when"] == "Before sleep"


def test_no_json_raises():
    with pytest.raises(ValueError):
        parse_cards_json("I could not read the prescription, sorry.")


def test_empty_input_raises():
    with pytest.raises(ValueError):
        parse_cards_json("")


def test_missing_fields_default_to_empty_strings():
    cards = sanitize_cards({"medicines": [{"name": "Dolo 650"}]})
    card = cards["medicines"][0]
    assert card["dose"] == ""
    assert card["when"] == ""
    assert card["written"] == ""
    assert card["explanation"] == ""
    assert card["unclear"] is False


def test_nameless_card_gets_placeholder_name():
    cards = sanitize_cards({"medicines": [{"when": "Every 6 hours"}]})
    assert cards["medicines"][0]["name"] == "Medicine"


def test_entirely_blank_cards_are_dropped():
    cards = sanitize_cards({"medicines": [{}, {"name": "  "}, {"unclear": True}]})
    assert cards == empty_cards()


def test_non_dict_medicines_are_skipped():
    cards = sanitize_cards({"medicines": ["paracetamol", 42, None, {"name": "Real"}]})
    assert [card["name"] for card in cards["medicines"]] == ["Real"]


def test_non_dict_payload_yields_empty():
    assert sanitize_cards(["not", "a", "dict"]) == empty_cards()
    assert sanitize_cards(None) == empty_cards()


def test_non_string_field_values_are_coerced():
    cards = sanitize_cards({"medicines": [{"name": 123, "dose": None, "unclear": "yes"}]})
    card = cards["medicines"][0]
    assert card["name"] == "123"
    assert card["dose"] == ""
    assert card["unclear"] is True


def test_unclear_flag_survives():
    cards = sanitize_cards(
        {"medicines": [{"name": "Zr?th", "written": "<unclear> OD", "unclear": True}]}
    )
    assert cards["medicines"][0]["unclear"] is True
