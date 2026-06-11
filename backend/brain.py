"""
backend/brain.py — Tiny Aya Global (3.35B), the brain of GrandmaCare.

The brain is the only model that talks to the user. It turns the eyes'
verbatim digital copy into adaptive medicine cards, and it answers questions
— always in the user's own language. Aya replies in the language it is
addressed in, so the user's language is detected from how they speak, never
selected from a menu.

Safety rules live in the prompts here: doses and timings come only from the
digital copy and the confirmed cards; anything unreadable is flagged, never
guessed. Whatever the brain emits is sanitized by backend/schema.py before
it reaches the UI.
"""

import os

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.schema import parse_cards_json

BRAIN_MODEL_ID = "CohereLabs/tiny-aya-global"

# ZeroGPU: created at module level, never inside a @spaces.GPU function.
tokenizer = AutoTokenizer.from_pretrained(BRAIN_MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(BRAIN_MODEL_ID, dtype=torch.bfloat16)
model.eval()
if torch.cuda.is_available():
    model = model.cuda()


CARDS_PROMPT = """\
Below is a verbatim, line-by-line transcript of a doctor's prescription.
Turn ONLY the medicine lines into simple cards for an elderly person.

Output exactly this JSON shape, nothing else:
{{
  "medicines": [
    {{
      "name": "medicine name as written",
      "dose": "strength as written, e.g. 200mg",
      "when": "the timing in short plain {language} words, exactly as the prescription means it",
      "written": "the timing/instruction text copied verbatim from the transcript",
      "explanation": "one or two short, warm {language} sentences telling them exactly how to take it",
      "unclear": false
    }}
  ]
}}

Rules:
- "when" follows the prescription's OWN wording — "Before sleep", "After
  lunch", "Every 6 hours", "Morning and night, after food", "Only when
  needed" — whatever it actually says. Do not force it into fixed slots.
- Notation guide: 1-0-1 means morning-afternoon-night tablet counts; OD=once
  daily, BD=twice daily, TDS=three times daily, HS=at bedtime, SOS=only when
  needed, AC/b/f=before food, PC/a/f=after food; x 5 days = for 5 days.
- "written" must be copied character-for-character from the transcript.
- "when" and "explanation" must be in {language}. Keep both short.
- If the timing or name is garbled, contains <unclear>, or you are not sure,
  set "unclear": true and say in the explanation that the pharmacist must
  confirm it. NEVER guess a dose or timing.
- Skip the header, complaint line (symptoms), and vitals — they are not
  medicines.
- Output the JSON object only. No markdown, no commentary.

Transcript:
{digital_copy}
"""

ANSWER_RULES = """\
You are GrandmaCare, a warm companion helping an elderly person with their
medicines. Follow these rules exactly:
- ALWAYS reply in the same language the person used for their question.
- Doses and timings come ONLY from the VERIFIED PRESCRIPTION below. Never
  invent or change a dose, timing, or medicine.
- If a medicine is marked UNCLEAR, do not guess — tell them to check that
  one with their pharmacist.
- Never suggest new medicines or medical advice beyond the prescription.
- The answer is read on a screen by an elderly person: 1 to 3 short, warm
  sentences. No lists, no markdown.
"""

PHRASE_TIME_PROMPT = """\
{rules}

An assistant looked at the photo the person just took of their medicines and
reported, in English:
---
{finding}
---
The current local time is {local_time}.

Tell the person, in {language}, which medicine to take right now and how
(quantity, before/after food), based only on that report. If the report says
UNSURE or nothing is due now, say that honestly and suggest asking their
pharmacist or showing one medicine at a time. 1 to 3 short, warm sentences.
"""


def _chat(messages, max_new_tokens=700):
    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(model.device)
    with torch.no_grad():
        output = model.generate(input_ids, max_new_tokens=max_new_tokens, do_sample=False)
    return tokenizer.decode(
        output[0, input_ids.shape[1] :], skip_special_tokens=True
    ).strip()


def cards_to_context(digital_copy, cards):
    lines = []
    for card in cards.get("medicines", []):
        flag = " [UNCLEAR — pharmacist must confirm]" if card.get("unclear") else ""
        lines.append(
            f"- {card['name']} ({card.get('dose') or 'dose not listed'}): "
            f"{card.get('when') or 'timing not listed'} "
            f"(written on prescription: \"{card.get('written') or ''}\"){flag}"
        )
    return (
        "VERIFIED PRESCRIPTION (the only source of doses and timings):\n"
        + "\n".join(lines)
        + "\n\nVerbatim prescription transcript:\n"
        + digital_copy
    )


def build_cards(digital_copy, language="English"):
    """Digital copy -> sanitized adaptive cards, retrying once on bad JSON."""
    prompt = CARDS_PROMPT.format(language=language, digital_copy=digital_copy)
    reply = _chat([{"role": "user", "content": prompt}])
    try:
        return parse_cards_json(reply)
    except ValueError:
        reply = _chat(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": reply},
                {"role": "user", "content": "Return ONLY the JSON object, nothing else."},
            ]
        )
        return parse_cards_json(reply)


def answer(question, digital_copy, cards):
    """Answer one question, in the language the question was asked in."""
    context = cards_to_context(digital_copy, cards)
    return _chat(
        [
            {"role": "system", "content": ANSWER_RULES},
            {"role": "user", "content": f"{context}\n\nQuestion: {question}"},
        ],
        max_new_tokens=220,
    )


def phrase_medicine_time(finding, local_time, language="English"):
    """Reword the eyes' factual finding as a warm answer in the user's language."""
    prompt = PHRASE_TIME_PROMPT.format(
        rules=ANSWER_RULES, finding=finding, local_time=local_time, language=language
    )
    return _chat([{"role": "user", "content": prompt}], max_new_tokens=220)


def detect_language(text):
    """Name the language of `text` in English (e.g. 'Hindi'). Falls back to
    English when the reply is not a plausible language name."""
    reply = _chat(
        [
            {
                "role": "user",
                "content": (
                    "Reply with ONLY the English name of the language this text "
                    f"is written in, one word if possible:\n{text}"
                ),
            }
        ],
        max_new_tokens=8,
    )
    name = reply.strip().strip(".").split("\n")[0].strip()
    if not name or len(name.split()) > 3 or not all(p.isalpha() for p in name.split()):
        return "English"
    return name.title()
