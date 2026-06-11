---
title: GrandmaCare
sdk: gradio
sdk_version: 6.16.0
python_version: "3.12"
app_file: app.py
pinned: false
---

# 👵 GrandmaCare

**AI-powered multilingual medicine assistant for elderly users**

GrandmaCare helps elderly individuals understand and manage their prescribed
medications independently. A prescription photo becomes a faithful digital
copy, then simple medicine cards in the user's own language — and at medicine
time, grandma can show her medicines to the camera and be told which one to
take right now.

Built for the **Hugging Face Build Small Hackathon**: three small, specialized
models instead of one big one.

---

## 🚩 Problem Statement

Many elderly individuals depend on family members to understand:

* Handwritten prescriptions
* Medical abbreviations (1-0-1, OD, BD, HS, SOS, a/f…)
* Dosage instructions and schedules

Prescriptions don't follow one format — some say *before meal / after meal*,
others *before sleep*, *after lunch*, *every 6 hours*. GrandmaCare adapts to
however the prescription is written instead of forcing it into fixed slots.

---

## 🏗️ Architecture — eyes, brain, ears

| Role | Model | Job |
|---|---|---|
| 👁 **Eyes** | [`openbmb/MiniCPM-V-4.6`](https://huggingface.co/openbmb/MiniCPM-V-4.6) (1B) | Reads the prescription **verbatim** into a digital copy; identifies medicines shown to the camera. Never explains — only looks. |
| 🧠 **Brain** | [`CohereLabs/tiny-aya-global-GGUF`](https://huggingface.co/CohereLabs/tiny-aya-global-GGUF) (3.35B Q4_K_M, 70+ languages, ungated) | Turns the digital copy into adaptive cards and answers questions — always in the user's own language. llama.cpp with CUDA, loaded inside the ZeroGPU window. |
| 👂 **Ears** | [`nvidia/nemotron-3.5-asr-streaming-0.6b`](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b) (0.6B) | Speech → text, so nobody has to type. |

```
Prescription photo
   ↓  image clean-up (shadow removal, contrast — backend/preprocess.py)
   ↓  EYES: verbatim transcription → digital copy
   ↓  BRAIN: digital copy → adaptive medicine cards (user's language)
   ↓  user confirms once → cards + digital copy = single source of truth
   ↓
   ├── voice question → EARS → BRAIN → BIG answer card (same language)
   └── "medicine time" camera photo → EYES (what is visible & due)
                                    → BRAIN (phrases the answer)
```

Deterministic Python (`backend/schema.py`, `backend/render.py`) sits between
the models and the screen: every model output is validated, sanitized, and
escaped before rendering — and ambiguous readings are flagged for the
pharmacist, never guessed.

---

## ✨ Features

### 📄 Digital copy, not interpretation
The eyes transcribe exactly what is written — unreadable words become
`<unclear>` markers, never guesses.

### 🗂️ Adaptive medicine cards
One card per medicine, with the timing **in the prescription's own words** —
"Before sleep", "After lunch", "Every 6 hours" — no fixed morning/noon/night
boxes. Every card shows the verbatim text from the paper so family can verify.

### ✅ Confirm-once safety flow
The cards are shown once, big and clear; the user confirms "This is correct"
(or re-takes the photo). The confirmed cards — not a fresh read of the image —
are the source of truth for everything afterwards.

### 🗣️ Speak your language — it just knows
No language menu. Ask out loud in Hindi, English, or 70+ other languages; the
answer comes back **in writing, in your language**, on a big high-contrast
card. When you switch language, the medicine cards re-explain themselves in it
too.

### 🕐 "Which medicine do I take now?"
At medicine time, show your strips and boxes to the camera. The app matches
what it sees against your confirmed cards and your local time and tells you
exactly which one to take — and says honestly when it isn't sure.

### 👴 Senior-friendly interface
Large fonts, one column, big buttons, minimal cognitive load.

---

## ⚠️ Honest Limitations

* **Handwriting reading is best-effort.** Garbled entries get an amber
  "confirm with your pharmacist" badge rather than a guess.
* **Voice input has no Bengali** (Nemotron ASR covers Hindi, English and ~38
  others, not Bengali yet). Written answers and cards work in Bengali.
* **Answers are written, not spoken** — voice in, big readable text out.
* Tiny Aya Global is **CC-BY-NC** (non-commercial) — fine for this hackathon
  project. The brain runs from the quantized (Q4_K_M) GGUF.
* GrandmaCare never replaces a pharmacist — the confirm step and the amber
  badges exist precisely because OCR of handwriting cannot be fully trusted.

---

## 🎯 Hackathon Alignment

GrandmaCare addresses the **Backyard AI** challenge with three small models
(≈5B parameters total, ~10 GB VRAM, ZeroGPU-ready) doing one job each:

* Real-world impact for elderly family members and caregivers
* Small-model deployment — specialized beats monolithic
* Accessibility and local-language support, auto-detected from speech
* Human-centered design with an explicit safety gate

---

## 📁 Project Structure

```text
grandmacare/
│
├── app.py                  # Gradio UI: read → confirm → ask / medicine time
├── requirements.txt
├── README.md
│
├── backend/
│   ├── eyes.py             # MiniCPM-V-4.6: transcribe & identify
│   ├── brain.py            # Tiny Aya: cards, answers, language detection
│   ├── ears.py             # Nemotron ASR: speech → text
│   ├── schema.py           # deterministic card-JSON validation (the trust boundary)
│   ├── render.py           # deterministic, escaped HTML cards
│   └── preprocess.py       # OpenCV photo clean-up
│
├── frontend/               # styles
└── tests/                  # GPU-free unit tests (schema, render)
```

---

## 🚀 Deployment

Runs as a Hugging Face Space (Gradio SDK, Python 3.12) with **ZeroGPU**. The
eyes (PyTorch) load at startup; the brain is a CUDA llama.cpp instance
created inside each `@spaces.GPU` window (`n_gpu_layers=-1` — the GGUF file
is downloaded once at startup and OS-cached, so per-request loads take
seconds); the ears run on CPU. All three model repos are ungated — no token
or license click-through needed.

```bash
pip install -r requirements.txt
python app.py
```

Note: `nemo-toolkit-asr` (the ears) is Linux-only — like the Space it runs on.

GPU-free tests:

```bash
python -m pytest tests/
```

---

## 👥 Team

* Roopkatha Bhattacharjee
* Soumyajit Ray

---

## ❤️ Vision

Technology should empower people, not exclude them.

GrandmaCare is built with the belief that elderly individuals deserve
healthcare tools that speak their language, respect their needs, and help
them maintain independence with confidence.
