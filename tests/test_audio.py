from backend import models


def test_synthesize_voice_empty_returns_none():
    assert models.synthesize_voice("") is None
    assert models.synthesize_voice(None) is None
    assert models.synthesize_voice("   ") is None


def test_synthesize_voice_returns_sr_and_wav(monkeypatch):
    class FakeModel:
        def generate(self, text):
            return [0.0, 0.1, -0.1]  # stand-in waveform

    monkeypatch.setattr(models, "_load_tts_model", lambda: FakeModel())
    result = models.synthesize_voice("sokale ekti nin")

    assert result == (models.VOX_SAMPLE_RATE, [0.0, 0.1, -0.1])
    assert models.VOX_SAMPLE_RATE == 16000
