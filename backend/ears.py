"""
backend/ears.py — Nemotron 3.5 ASR streaming 0.6B, the ears of GrandmaCare.

Voice in, text out: elderly users should never have to type. The ears only
transcribe — understanding and answering is the brain's job. The model stays
on CPU: a 0.6B conformer transcribes a short spoken question in a couple of
seconds without spending the ZeroGPU budget.

Runs on nemo-toolkit-asr (the ASR-only split of NeMo, no transformers pin,
Linux-only — like the Space it runs on).
"""

import os
import tempfile

import nemo.collections.asr as nemo_asr

EARS_MODEL_ID = "nvidia/nemotron-3.5-asr-streaming-0.6b"

# ZeroGPU: created at module level, never inside a @spaces.GPU function.
model = nemo_asr.models.ASRModel.from_pretrained(model_name=EARS_MODEL_ID)
model.eval()


def transcribe_audio(audio_path):
    """Recorded question (any format gradio saves) -> transcribed text."""
    if not audio_path:
        raise ValueError("Please record your question first.")

    import librosa
    import soundfile

    audio, _ = librosa.load(audio_path, sr=16000, mono=True)
    wav_path = os.path.join(tempfile.gettempdir(), "grandmacare_question.wav")
    soundfile.write(wav_path, audio, 16000)

    results = model.transcribe([wav_path])
    if not results:
        raise ValueError("I could not hear anything in that recording.")
    first = results[0]
    text = (first.text if hasattr(first, "text") else str(first)).strip()
    if not text:
        raise ValueError("I could not hear anything in that recording.")
    return text
