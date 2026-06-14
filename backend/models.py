import os

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

from huggingface_hub import hf_hub_download

from backend.schema import parse_cards_text, parse_pill_text


MINICPM_MODEL_ID = "openbmb/MiniCPM-V-4_5"
AYA_REPO_ID = "CohereLabs/tiny-aya-global-GGUF"
AYA_FILENAME = "tiny-aya-global-q4_k_m.gguf"

LANGUAGES = {
    "English": {"name": "English", "script": "English"},
    "Hindi": {"name": "Hindi", "script": "Devanagari"},
    "Bengali": {"name": "Bengali", "script": "Bengali"},
}

AYA_MODEL_PATH = None
AYA_MODEL_ERROR = None
try:
    AYA_MODEL_PATH = hf_hub_download(repo_id=AYA_REPO_ID, filename=AYA_FILENAME)
except Exception as exc:
    AYA_MODEL_ERROR = exc

_vision_model = None
_vision_tokenizer = None


def _load_vision_model():
    global _vision_model, _vision_tokenizer
    if _vision_model is not None and _vision_tokenizer is not None:
        return _vision_model, _vision_tokenizer

    import torch
    from transformers import AutoModel, AutoTokenizer

    _vision_tokenizer = AutoTokenizer.from_pretrained(
        MINICPM_MODEL_ID,
        trust_remote_code=True,
    )
    model = AutoModel.from_pretrained(
        MINICPM_MODEL_ID,
        trust_remote_code=True,
        attn_implementation="sdpa",
        torch_dtype=torch.bfloat16,
    )
    model = model.eval()
    if torch.cuda.is_available():
        model = model.cuda()
    _vision_model = model
    return _vision_model, _vision_tokenizer


def _vision_chat(image_path, prompt):
    from PIL import Image

    model, tokenizer = _load_vision_model()
    image = Image.open(image_path).convert("RGB")
    messages = [{"role": "user", "content": [image, prompt]}]
    answer = model.chat(msgs=messages, tokenizer=tokenizer)
    return str(answer or "").strip()


TRANSCRIBE_PRESCRIPTION_PROMPT = """
Transcribe every piece of text you can read in this prescription image, exactly as written.

Rules:
- Output plain text only. One line of output per line in the image.
- Copy spellings, numbers, and shorthand exactly (for example "1-0-1", "TDS", "BD", "SOS").
- If a word is unreadable, write [unclear] in its place.
- Do not interpret, summarize, translate, reorder, or add anything that is not in the image.
- Do not use markdown or JSON.
"""

EXTRACT_CARDS_PROMPT = """
You are GrandmaCare, a careful medicine assistant for elderly users.
Look at this doctor's prescription image and list every medicine that is prescribed.

Write one card per medicine, exactly like this example, one field per line, with an empty line between cards:

MEDICINE: Amoxicillin
DOSE: 500 mg
WHEN: 1-0-1 after food
LABEL: Morning and night
TAKE: Take one tablet in the morning and one at night, after food.
NOTE: for 5 days

Rules:
- Start every card with the MEDICINE line, using the medicine name as written on the paper.
- DOSE: the strength or quantity if written, otherwise skip the line.
- WHEN: copy the doctor's timing words EXACTLY as written (for example "1-0-1 after food", "at bedtime"). Do not reword them.
- LABEL: a very short, simple English label for when to take it, at most 4 words (for example "Morning and night", "Before lunch", "At bedtime", "When needed").
- TAKE: one short, warm instruction in plain ENGLISH telling the patient how to take it.
- NOTE: duration or any extra detail if written, otherwise skip the line.
- Ignore everything that is not a prescribed medicine (clinic name, doctor name, patient name, age, date, vitals like BP/HR/SpO2/temperature, signature, phone numbers).
- Read carefully. Do NOT invent or substitute medicines. Only list what is actually written on this prescription.
- No JSON, no markdown, no extra commentary.
"""


def transcribe_prescription(image_path):
    if not image_path:
        raise ValueError("Please upload a prescription photo first.")
    transcript = _vision_chat(image_path, TRANSCRIBE_PRESCRIPTION_PROMPT)
    if not transcript:
        raise ValueError("I could not read any text in that image.")
    return transcript


def extract_cards(image_path):
    if not image_path:
        raise ValueError("Please upload a prescription photo first.")
    text = _vision_chat(image_path, EXTRACT_CARDS_PROMPT)
    return parse_cards_text(text), text


def _create_llm():
    if AYA_MODEL_ERROR is not None:
        raise ValueError(f"tiny-aya could not be downloaded: {AYA_MODEL_ERROR}")

    from llama_cpp import Llama

    return Llama(
        model_path=AYA_MODEL_PATH,
        n_gpu_layers=-1,
        n_ctx=4096,
        flash_attn=True,
        verbose=False,
    )


def _aya_complete(prompt, max_tokens):
    llm = _create_llm()
    response = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=max_tokens,
    )
    return response["choices"][0]["message"]["content"]


def translate_cards(cards, language):
    if not cards or language == "English":
        return cards

    language_config = LANGUAGES.get(language, LANGUAGES["English"])
    language_name = language_config["name"]
    language_script = language_config["script"]

    listing = "\n".join(
        f"MEDICINE: {card.get('name', 'Medicine')}\nTAKE: {card.get('instruction', '')}"
        for card in cards
    )

    prompt = f"""
You are GrandmaCare. Translate each medicine instruction into {language_name}.

For every medicine below, repeat its MEDICINE line exactly, then give two lines:
TAKE: the instruction translated into {language_name} using {language_script} script
SAY: the SAME translated sentence written in English (Latin) letters, the way it sounds out loud. This must be a transliteration, NOT the English meaning.

Example for Bengali:
MEDICINE: Amoxicillin
TAKE: সকালে এবং রাতে খাবারের পরে একটি ট্যাবলেট নিন।
SAY: sokale ebong rate khabarer pore ekti tablet nin.

Keep the same medicines in the same order. No extra commentary.

Medicines:
{listing}
"""
    text = _aya_complete(prompt, max_tokens=1200)
    translated = parse_cards_text(text)

    for index, card in enumerate(cards):
        if index < len(translated):
            card["instruction"] = translated[index].get("instruction", card.get("instruction", ""))
            card["romanized"] = translated[index].get("romanized", "")

    return cards


def _translate_answer(english_text, language):
    if language == "English" or not english_text:
        return english_text, ""

    language_config = LANGUAGES.get(language, LANGUAGES["English"])
    language_name = language_config["name"]
    language_script = language_config["script"]

    prompt = f"""
Translate the message below into {language_name}.

Answer in exactly two lines:
ANSWER: the message translated into {language_name} using {language_script} script
SAY: the SAME translated sentence written in English (Latin) letters, the way it sounds out loud. A transliteration, NOT the English meaning.

Message:
{english_text}
"""
    result = parse_pill_text(_aya_complete(prompt, max_tokens=400))
    return result["answer"], result["romanized"]


def analyze_prescription(image_path, language):
    transcript = transcribe_prescription(image_path)
    cards, raw = extract_cards(image_path)
    cards = translate_cards(cards, language)
    return transcript, cards, raw


def identify_pill(pill_image_path, medicines, language):
    if not pill_image_path:
        raise ValueError("Please take a photo of the medicine first.")

    listing = "\n".join(
        "- " + " | ".join(
            part
            for part in (
                medicine.get("name", ""),
                medicine.get("dose", ""),
                medicine.get("timing", ""),
            )
            if part
        )
        for medicine in medicines
    )

    prompt = f"""
You are GrandmaCare, helping an elderly patient identify a medicine.

The patient's prescription contains these medicines:
{listing}

Look at the medicine package in this photo. Decide whether it matches one of the prescription
medicines. Names may have small spelling differences or be a brand name for the same medicine,
but only match when you are confident.

Answer in exactly this format, one field per line:

MATCH: the matching prescription medicine name, or NONE
ANSWER: your answer for the patient
SAY: leave this blank

Rules:
- If it matches: ANSWER is 1-2 short sentences in plain ENGLISH saying which medicine this is and when and how to take it, using the prescription timing.
- If it does not match: MATCH is NONE, and ANSWER says in plain ENGLISH that this medicine is not on the prescription and they should ask their pharmacist.
- Never guess dosage information that is not in the prescription.
- No JSON, no markdown, no extra commentary.
"""
    result = parse_pill_text(_vision_chat(pill_image_path, prompt))

    if language != "English":
        answer, romanized = _translate_answer(result["answer"], language)
        result["answer"] = answer
        result["romanized"] = romanized

    return result
