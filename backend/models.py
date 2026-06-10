import os

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

from huggingface_hub import hf_hub_download

from backend.normalize import build_instruction, normalize_transcription
from backend.schema import (
    merge_translation,
    normalize_schedule,
    parse_model_json,
    parse_raw_json,
    uses_expected_script,
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


def extract_medicines(image_path):
    if not image_path:
        raise ValueError("Please upload a prescription or medicine photo first.")

    from PIL import Image

    model, processor = _load_vision_model()
    image = Image.open(image_path).convert("RGB")
    prompt = """
You are transcribing a prescription or medicine label photo.
Report ONLY what is literally written. Do not interpret anything.

Use exactly this schema:
{
  "medicines": [
    {
      "name": "medicine name as written",
      "dose": "strength as written, e.g. 40 mg",
      "frequency_raw": "timing EXACTLY as written, e.g. 1-0-1, BD, TDS, OD HS",
      "meal_raw": "any before/after food instruction exactly as written, e.g. AC, after food",
      "duration_raw": "any duration exactly as written, e.g. x 5 days",
      "notes": "anything else readable and relevant"
    }
  ]
}

Rules:
- Copy notation character-for-character (e.g. write "1-0-1", not "twice a day").
- Do NOT interpret or expand abbreviations like OD, BD, TDS, AC, PC, SOS.
- Every line that lists a medicine (often starting with -, T., Tab., Cap., Syp.)
  is a separate entry. Transcribe ALL of them, even if part of the image is
  dark or blurry — transcribe whatever characters you can read.
- Slot patterns like 1-0-1 or 0-0-1 always go in frequency_raw, never in name or dose.
- Include a medicine only if you can read it from the image.
- Use an empty string for any field that is not written on the prescription.
- Do not add markdown, comments, or text outside JSON.
"""
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

    output_ids = model.generate(**inputs, max_new_tokens=700, do_sample=False)
    input_token_count = inputs["input_ids"].shape[-1]
    generated_ids = output_ids[:, input_token_count:]
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    transcription = parse_raw_json(text)

    if not isinstance(transcription, dict) or not transcription.get("medicines"):
        raise ValueError("I could not find any readable medicines in that image.")
    return transcription


def _translate_with_aya(schedule, language_config):
    if AYA_MODEL_ERROR is not None:
        raise ValueError(f"tiny-aya could not be downloaded: {AYA_MODEL_ERROR}")

    language_name = language_config["name"]
    language_script = language_config["script"]

    from llama_cpp import Llama

    llm = Llama(
        model_path=AYA_MODEL_PATH,
        n_gpu_layers=-1,
        n_ctx=4096,
        flash_attn=True,
        verbose=False,
    )

    numbered = "\n".join(
        f"{index + 1}. {medicine['instruction']}"
        for index, medicine in enumerate(schedule["medicines"])
    )
    prompt = f"""
You are GrandmaCare, a careful translator for elderly patients.
Translate each numbered English sentence below into {language_name},
written in {language_script} script, plus a romanized (Latin letters) version.

Return JSON only using this exact schema, one entry per sentence, same order:
{{
  "medicines": [
    {{
      "instruction": "translation in {language_name} using {language_script} script",
      "romanized": "the same translation in Latin letters"
    }}
  ]
}}

Translate faithfully. Do not add, remove, or change any medical detail.
Use warm, direct, senior-friendly language.

Sentences:
{numbered}
"""
    response = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1000,
    )
    text = response["choices"][0]["message"]["content"]
    return parse_model_json(text)


def translate_schedule(schedule, language):
    schedule = normalize_schedule(schedule)
    for medicine in schedule["medicines"]:
        medicine["instruction"] = build_instruction(medicine)
        medicine["romanized"] = ""

    language_config = LANGUAGES.get(language, LANGUAGES["English"])
    if language_config["name"] == "English":
        return schedule

    try:
        translated = _translate_with_aya(schedule, language_config)
    except Exception:
        # English instructions are always safe to show; never fail the
        # whole analysis because translation misbehaved.
        return schedule

    merged = merge_translation(schedule, translated)
    for index, medicine in enumerate(merged["medicines"]):
        if not uses_expected_script(medicine["instruction"], language_config["script"]):
            medicine["instruction"] = schedule["medicines"][index]["instruction"]
            medicine["romanized"] = ""
    return merged


def analyze_prescription(image_path, language):
    raw = extract_medicines(image_path)            # transcription-only JSON
    schedule = normalize_transcription(raw)        # deterministic interpretation
    return translate_schedule(schedule, language)  # Aya phrasing, unchanged role
