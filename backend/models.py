import os

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

from huggingface_hub import hf_hub_download

from backend.schema import (
    parse_cards_text,
    parse_pill_text,
    truncate_transcript,
)


MINICPM_MODEL_ID = "openbmb/MiniCPM-V-4_6"
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
_vision_processor = None


def _load_vision_model():
    global _vision_model, _vision_processor
    if _vision_model is not None and _vision_processor is not None:
        return _vision_model, _vision_processor

    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    _vision_processor = AutoProcessor.from_pretrained(
        MINICPM_MODEL_ID,
        trust_remote_code=True,
    )
    _vision_model = AutoModelForImageTextToText.from_pretrained(
        MINICPM_MODEL_ID,
        dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    _vision_model.eval()
    return _vision_model, _vision_processor


def _vision_generate(image_path, prompt, max_new_tokens):
    from PIL import Image

    model, processor = _load_vision_model()
    image = Image.open(image_path).convert("RGB")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    input_token_count = inputs["input_ids"].shape[-1]
    generated_ids = output_ids[:, input_token_count:]
    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0]


TRANSCRIBE_PRESCRIPTION_PROMPT = """
Transcribe every piece of text you can read in this prescription image, exactly as written.

Rules:
- Output plain text only. One line of output per line in the image.
- Copy spellings, numbers, and shorthand exactly (for example "1-0-1", "TDS", "BD", "SOS").
- If a word is unreadable, write [unclear] in its place.
- Do not interpret, summarize, translate, reorder, or add anything that is not in the image.
- Do not use markdown or JSON.
"""

TRANSCRIBE_PILL_PROMPT = """
Transcribe all text printed on this medicine strip, bottle, or box, exactly as written.
Plain text only, one line per printed line. Write [unclear] for unreadable words.
Do not interpret or add anything.
"""


def transcribe_prescription(image_path):
    if not image_path:
        raise ValueError("Please upload a prescription photo first.")
    transcript = _vision_generate(image_path, TRANSCRIBE_PRESCRIPTION_PROMPT, max_new_tokens=600).strip()
    if not transcript:
        raise ValueError("I could not read any text in that image.")
    return transcript


def transcribe_pill_label(image_path):
    if not image_path:
        raise ValueError("Please take a photo of the medicine first.")
    label_text = _vision_generate(image_path, TRANSCRIBE_PILL_PROMPT, max_new_tokens=200).strip()
    if not label_text:
        raise ValueError("I could not read any text on that medicine.")
    return label_text


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


def structure_and_translate(transcript, language):
    language_config = LANGUAGES.get(language, LANGUAGES["English"])
    language_name = language_config["name"]
    language_script = language_config["script"]

    prompt = f"""
You are GrandmaCare, a careful medicine assistant for elderly users.
Below is a transcript of a doctor's prescription. Write one simple card for each medicine.

Write each card exactly like this example, one field per line, with an empty line between cards:

MEDICINE: Paracetamol
DOSE: 500 mg
WHEN: 1-0-1 after food
TAKE: Take one tablet in the morning and one at night, after eating.
SAY: Take one tablet in the morning and one at night, after eating.
NOTE: for 5 days

Rules:
- Start every card with the MEDICINE line.
- WHEN: copy the doctor's timing words exactly as written. Do not reword them.
- TAKE: one short, warm sentence in {language_name} using {language_script} script telling the patient how to take it.
- SAY: the same sentence written in Latin letters.
- Skip the DOSE or NOTE line if the prescription does not say.
- Ignore lines that are not medicines (clinic name, doctor name, patient name, date, signature).
- Do not invent medicines or details that are not in the transcript.
- No JSON, no markdown, no extra commentary.

Transcript:
{truncate_transcript(transcript)}
"""
    text = _aya_complete(prompt, max_tokens=1400)
    return parse_cards_text(text), text.strip()


def match_pill(label_text, medicines, language):
    language_config = LANGUAGES.get(language, LANGUAGES["English"])
    language_name = language_config["name"]
    language_script = language_config["script"]

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

The patient photographed a medicine package. The text on it reads:
{truncate_transcript(label_text, max_chars=800)}

Decide whether this package matches one of the prescription medicines. Names may have small
spelling differences or be a brand name for the same medicine, but only match when you are confident.

Answer in exactly this format, one field per line:

MATCH: the matching prescription medicine name, or NONE
ANSWER: your answer for the patient
SAY: the same answer written in Latin letters

Rules:
- If it matches: ANSWER is 1-2 short sentences in {language_name} using {language_script} script saying which medicine this is and when and how to take it, using the prescription timing.
- If it does not match: MATCH is NONE, and ANSWER says in {language_name} that this medicine is not on the prescription and they should ask their pharmacist.
- Never guess dosage information that is not in the prescription.
- No JSON, no markdown, no extra commentary.
"""
    text = _aya_complete(prompt, max_tokens=400)
    return parse_pill_text(text)
