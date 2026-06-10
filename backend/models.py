import json
import os

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

from huggingface_hub import hf_hub_download

from backend.normalize import normalize_transcription
from backend.schema import merge_translation, parse_model_json, parse_raw_json


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


def translate_schedule(schedule, language):
    if AYA_MODEL_ERROR is not None:
        raise ValueError(f"tiny-aya could not be downloaded: {AYA_MODEL_ERROR}")

    language_config = LANGUAGES.get(language, LANGUAGES["English"])
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

    prompt = f"""
You are GrandmaCare, a careful medicine assistant for elderly users.
Write simple medicine instructions in {language_name}.
Also provide a romanized version for each instruction.

Return JSON only using this exact schema:
{{
  "medicines": [
    {{
      "name": "same medicine name",
      "dose": "same dose",
      "schedule": ["morning"],
      "quantities": {{"morning": 1}},
      "as_needed": false,
      "meal_relation": "same meal_relation",
      "duration": "same duration",
      "frequency_raw": "same frequency_raw",
      "needs_review": false,
      "notes": "same notes",
      "instruction": "simple instruction in {language_name} using {language_script} script",
      "romanized": "romanized version of the instruction"
    }}
  ]
}}

Write each instruction from the structured fields:
- Use the schedule and quantities for when and how much (0.5 means "half tablet").
- If meal_relation is before_food, after_food, or with_food, say so simply.
- If duration is set, mention it (e.g. "for 5 days").
- If as_needed is true, say to take it only when needed, as the doctor advised.
- If needs_review is true, say the timing is unclear and to confirm with the pharmacist.

Keep the same medicine order and copy every field except instruction and romanized unchanged.
Use warm, direct, senior-friendly language.
Do not give medical advice beyond the prescription details.

Prescription JSON:
{json.dumps(schedule, ensure_ascii=False)}
"""
    response = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1000,
    )
    text = response["choices"][0]["message"]["content"]
    translated = parse_model_json(text)
    return merge_translation(schedule, translated)


def analyze_prescription(image_path, language):
    raw = extract_medicines(image_path)            # transcription-only JSON
    schedule = normalize_transcription(raw)        # deterministic interpretation
    return translate_schedule(schedule, language)  # Aya phrasing, unchanged role
