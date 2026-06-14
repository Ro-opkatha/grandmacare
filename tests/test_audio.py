from backend import models


def test_add_card_audio_prefers_romanized(monkeypatch):
    monkeypatch.setattr(models, "synthesize", lambda text: f"SPOKE:{text}")

    cards = [
        {"name": "A", "instruction": "Take one at night", "romanized": "rate ekti nin"},
        {"name": "B", "instruction": "Take after food", "romanized": ""},
    ]
    result = models.add_card_audio(cards)

    assert result[0]["audio"] == "SPOKE:rate ekti nin"   # romanized wins
    assert result[1]["audio"] == "SPOKE:Take after food"  # falls back to instruction


def test_add_card_audio_survives_synthesis_error(monkeypatch):
    def boom(text):
        raise RuntimeError("tts down")

    monkeypatch.setattr(models, "synthesize", boom)
    cards = [{"name": "A", "instruction": "x", "romanized": ""}]

    result = models.add_card_audio(cards)
    assert result[0]["audio"] == ""


def test_synthesize_empty_returns_blank():
    assert models.synthesize("") == ""
    assert models.synthesize(None) == ""
