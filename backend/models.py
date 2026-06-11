"""
backend/models.py — MiniCPM-o 4.5 (vision + speech) wrapper.

One model sees, reads, and speaks. It is only ever asked to TRANSCRIBE and
to ANSWER QUESTIONS — schedules are interpreted by backend/normalize.py and
phrased by backend/templates.py, deterministically. Doses and timings in
voice answers come from the confirmed schedule passed in context, never from
re-reading the image.
"""

import os
import tempfile

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

import torch
from transformers import AutoModel

from backend.normalize import normalize_transcription
from backend.preprocess import preprocess_prescription
from backend.schema import parse_raw_json
from backend.templates import localize_schedule

MINICPM_MODEL_ID = "openbmb/MiniCPM-o-4_5"

# ZeroGPU: the model must be created at module level (startup), never inside
# a @spaces.GPU function. Pins per the model card: transformers==4.51.0,
# minicpmo-utils[all]>=1.0.5, torch<=2.8.0.
model = AutoModel.from_pretrained(
    MINICPM_MODEL_ID,
    trust_remote_code=True,
    attn_implementation="sdpa",
    torch_dtype=torch.bfloat16,
    init_vision=True,
    init_audio=True,
    init_tts=True,
)
model.eval()
if torch.cuda.is_available():
    model = model.cuda()


TRANSCRIBE_PROMPT = """\
Transcribe this doctor's prescription EXACTLY as written, line by line.

- Copy every character: numbers, dashes (1-0-1), circled numbers (⑥),
  abbreviations (OD, BD, TDS, HS, SOS, AC, PC, b/f, a/f), units (mg, ml).
- One output line per written line, in order. Include the header, the
  complaint line, and every medicine line.
- If a word is unreadable, write <unclear> in its place — do not guess.
- Do NOT interpret, expand, translate, or summarize anything.
- Output plain text lines only. No JSON, no commentary.
"""

STRUCTURE_PROMPT = """\
Below is a line-by-line transcript of a doctor's prescription.
Convert ONLY the medicine lines into JSON. Copy text verbatim from the
transcript into fields — never interpret or expand it.

Use exactly this schema:
{
  "medicines": [
    {
      "name": "medicine name as written",
      "dose": "strength as written, e.g. 200mg",
      "frequency_raw": "timing notation EXACTLY as written, e.g. 1-0-1, BD, OD HS",
      "meal_raw": "before/after food marking as written, e.g. AC, b/f, after food",
      "duration_raw": "duration as written, e.g. x 5 days",
      "quantity_to_buy": "circled number if present, e.g. 6 for ⑥",
      "notes": "anything else readable on that line"
    }
  ]
}

Rules:
- The Rx / complaint line (symptoms like "cold, fever") and vitals (B.P., HR,
  SpO2, Temp) are NOT medicines. Skip them.
- Frequency looks like digit-dash patterns (1-0-1, 0-0-1, ½-0-½) or
  abbreviations (OD, BD, TDS, QID, HS, SOS). Put it in frequency_raw only.
- Circled numbers like ⑥ are the pharmacy dispensing quantity. Put the digit
  in quantity_to_buy — NEVER in frequency_raw or dose.
- (b/f) means before food, (a/f) means after food — copy into meal_raw as written.
- Worked example: the line "T. Opox-CV 200mg 1-0-1 ⑥" becomes
  {"name": "Opox-CV", "dose": "200mg", "frequency_raw": "1-0-1",
   "meal_raw": "", "duration_raw": "", "quantity_to_buy": "6", "notes": ""}
- Use an empty string for anything not written. Keep <unclear> markers as-is.
- Output JSON only. No markdown, no commentary.

Transcript:
"""

VOICE_SYSTEM_RULES = """\
You are GrandmaCare, a warm voice companion helping an elderly person with
their medicines. Follow these rules exactly:
- Doses and timings come ONLY from the VERIFIED SCHEDULE text you were given.
  Never re-read doses or timings from the photo.
- The photo is only for visual questions, like "which one is the white round
  pill?".
- If a medicine is marked NEEDS REVIEW, do not guess — say "please check that
  one with your pharmacist".
- Never suggest medicines, doses, or changes beyond the verified schedule.
- Answer warmly and simply, in 1 to 3 short sentences.
"""


def _chat_text(content, max_new_tokens=700):
    msgs = [{"role": "user", "content": content}]
    result = model.chat(msgs=msgs, max_new_tokens=max_new_tokens, use_tts_template=False)
    return result if isinstance(result, str) else str(result)


def transcribe_prescription(image):
    return _chat_text([image, TRANSCRIBE_PROMPT])


def structure_transcript(transcript):
    text = _chat_text([STRUCTURE_PROMPT + transcript])
    return parse_raw_json(text)


def extract_medicines(image_path):
    if not image_path:
        raise ValueError("Please upload a prescription or medicine photo first.")

    from PIL import Image

    image = Image.open(image_path).convert("RGB")
    transcript = transcribe_prescription(image)
    transcription = structure_transcript(transcript)

    if not isinstance(transcription, dict) or not transcription.get("medicines"):
        raise ValueError("I could not find any readable medicines in that image.")
    return transcription, transcript


def analyze_prescription(image_path, language):
    processed_path = preprocess_prescription(image_path)
    raw, transcript = extract_medicines(processed_path)   # perception only
    schedule = normalize_transcription(raw)               # deterministic interpretation
    schedule = localize_schedule(schedule, language)      # deterministic phrasing
    return {
        "schedule": schedule,
        "image_path": processed_path,
        "transcript": transcript,
    }


def schedule_to_context_text(schedule):
    """Compact text of the confirmed schedule for the voice context."""
    lines = []
    for medicine in schedule.get("medicines", []):
        if medicine.get("needs_review"):
            lines.append(
                f"- {medicine['name']} ({medicine['dose']}): NEEDS REVIEW — timing "
                f"written as \"{medicine.get('frequency_raw', '')}\"; the user must "
                "ask their pharmacist."
            )
            continue
        if medicine.get("as_needed"):
            timing = "only when needed (SOS)"
        else:
            quantities = medicine.get("quantities") or {}
            parts = []
            for bucket in medicine.get("schedule", []):
                qty = quantities.get(bucket)
                parts.append(f"{bucket}: {qty:g} tablet" if qty else bucket)
            timing = ", ".join(parts) if parts else "timing unknown"
        details = [timing]
        if medicine.get("meal_relation"):
            details.append(medicine["meal_relation"].replace("_", " "))
        if medicine.get("duration"):
            details.append(f"for {medicine['duration']}")
        lines.append(f"- {medicine['name']} ({medicine['dose']}): {'; '.join(details)}")
    return "VERIFIED SCHEDULE (the only source of doses and timings):\n" + "\n".join(lines)


def answer_question(image_path, schedule, audio_path):
    """One turn-based voice exchange: spoken question in, text + speech out."""
    if not audio_path:
        raise ValueError("Please record your question first.")

    import librosa
    from PIL import Image

    user_audio, _ = librosa.load(audio_path, sr=16000, mono=True)
    image = Image.open(image_path).convert("RGB")
    context = schedule_to_context_text(schedule)

    msgs = [
        {"role": "system", "content": [VOICE_SYSTEM_RULES]},
        {"role": "user", "content": [image, context, user_audio]},
    ]
    output_audio_path = os.path.join(tempfile.gettempdir(), "grandmacare_answer.wav")
    result = model.chat(
        msgs=msgs,
        max_new_tokens=256,
        generate_audio=True,
        output_audio_path=output_audio_path,
    )

    if isinstance(result, str):
        text = result
    elif isinstance(result, dict):
        text = str(result.get("text") or result.get("content") or result)
    else:
        text = str(getattr(result, "text", result))
    return text, output_audio_path
