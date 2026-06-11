"""
backend/eyes.py — MiniCPM-V-4.6 (1B), the eyes of GrandmaCare.

The eyes only ever LOOK: they transcribe the prescription verbatim into the
digital copy, and they identify medicines shown to the camera. They never
explain or phrase anything for the user — that is the brain's job
(backend/brain.py), so each model stays small and on-task.
"""

import os

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

import torch
from transformers import AutoModelForImageTextToText, AutoProcessor

EYES_MODEL_ID = "openbmb/MiniCPM-V-4.6"

# ZeroGPU: models must be created at module level (startup), never inside a
# @spaces.GPU function. MiniCPM-V-4.6 is natively integrated in
# transformers>=5.7 — no trust_remote_code, no .chat() API, plain generate().
processor = AutoProcessor.from_pretrained(EYES_MODEL_ID)
model = AutoModelForImageTextToText.from_pretrained(EYES_MODEL_ID, dtype=torch.bfloat16)
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

IDENTIFY_PROMPT = """\
The photo shows medicine packets, strips, bottles or pills that an elderly
person is holding up to the camera right now.

Their CONFIRMED medicine list (the only medicines they take):
{medicine_list}

The current local time for them is: {local_time}.

Look at the photo and report, briefly and factually, in English:
1. Which medicines from the CONFIRMED list you can actually see — match the
   printed names on the packaging. For each, quote the name you read.
2. Of the visible ones, which (if any) is due around the current time,
   according to its listed timing.
3. If a printed name is unreadable or not on the confirmed list, say UNSURE
   for it. Never guess a medicine that you cannot clearly read.
"""


def _generate(content, max_new_tokens=700):
    messages = [{"role": "user", "content": content}]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    generated = output[:, inputs["input_ids"].shape[1] :]
    return processor.batch_decode(generated, skip_special_tokens=True)[0].strip()


def transcribe_prescription(image_path):
    """Prescription photo -> verbatim digital copy (plain text lines)."""
    return _generate(
        [
            {"type": "image", "path": image_path},
            {"type": "text", "text": TRANSCRIBE_PROMPT},
        ]
    )


def identify_medicine_now(image_path, cards, local_time):
    """Camera photo of medicines in hand -> factual English finding of what is
    visible and what is due now, judged against the confirmed cards."""
    lines = []
    for card in cards.get("medicines", []):
        when = card.get("when") or "timing not listed"
        if card.get("unclear"):
            when += " (UNCLEAR — pharmacist must confirm)"
        lines.append(f"- {card['name']} ({card.get('dose') or 'dose not listed'}): {when}")
    medicine_list = "\n".join(lines) if lines else "- (no confirmed medicines)"

    prompt = IDENTIFY_PROMPT.format(medicine_list=medicine_list, local_time=local_time)
    return _generate(
        [
            {"type": "image", "path": image_path},
            {"type": "text", "text": prompt},
        ],
        max_new_tokens=350,
    )
