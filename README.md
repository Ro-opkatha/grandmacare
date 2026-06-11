---
title: GrandmaCare
sdk: gradio
sdk_version: 6.16.0
app_file: app.py
pinned: false
---

# 👵 GrandmaCare

**AI-powered multilingual medicine assistant for elderly users**

GrandmaCare is a senior-friendly healthcare assistant designed to help elderly individuals understand and manage their prescribed medications independently. By leveraging multimodal AI, the application transforms complex prescriptions into simple, easy-to-follow medication schedules in the user's preferred language.

Built for the **Hugging Face Build Small Hackathon**, GrandmaCare focuses on solving a real-world problem faced by millions of elderly patients who struggle with handwritten prescriptions, medical jargon, and medication management.

---

## 🚩 Problem Statement

Many elderly individuals depend on family members to understand:

* Handwritten prescriptions
* Medical abbreviations
* Dosage instructions
* Medication schedules

This often leads to confusion, missed doses, and reduced independence.

GrandmaCare aims to bridge this gap by converting prescriptions into clear, accessible, and language-friendly guidance.

---

## ✨ Features

### 📄 Prescription Understanding

Upload a prescription image and extract relevant medication information using multimodal AI.

### 💊 Simplified Medicine Instructions

Convert complex medical terminology into easy-to-understand explanations.

### 🌏 Multilingual Support

Generate medicine schedules in:

* English
* Bengali
* Hindi

### 🗓️ Daily Medication Schedule

Organize medicines into:

* Morning
* Afternoon
* Evening
* Night

for easier adherence.

### ✅ Confirm-Once Safety Flow

The prescription is read **once**, shown as big cards, and the user confirms
"This is correct" (or re-takes the photo). The confirmed schedule — not a fresh
read of the image — is the single source of truth for everything afterwards.

### 🔊 Voice Q&A

After confirming, ask questions out loud ("when do I take the white pill?").
MiniCPM-o 4.5 hears the question and answers with a spoken reply. Doses and
timings in answers come only from the confirmed schedule; the photo is used
only for visual questions.

### 👴 Senior-Friendly Interface

Designed with:

* Large fonts
* Clear navigation
* Minimal cognitive load
* Accessible layouts

---

## 🏗️ System Architecture

**One model sees, reads, and speaks; deterministic Python keeps it honest.**

Prescription Photo

↓
Image clean-up (shadow removal, contrast, upscale — `backend/preprocess.py`)

↓
MiniCPM-o 4.5 transcribes what is literally written (two passes: verbatim
lines, then verbatim JSON — no interpretation)

↓
Deterministic notation interpreter (`backend/normalize.py`: 1-0-1 patterns,
OD/BD/TDS/HS/SOS, AC/PC, durations; anything unclear is flagged for the
pharmacist, never guessed)

↓
Deterministic instruction templates (`backend/templates.py`, EN/HI/BN —
no model composes dosing text)

↓
User confirms the schedule once → confirmed schedule + photo become the
context for turn-based voice Q&A (MiniCPM-o 4.5 speech in/out)

---

## 🛠️ Tech Stack

### Frontend

* Gradio
* Python

### AI Model

* OpenBMB MiniCPM-o 4.5 (vision + speech, single model)

### Additional Components

* Deterministic prescription-notation interpreter + instruction templates
  (the safety boundary: models transcribe and chat, never compose schedules)
* OpenCV photo preprocessing
* GPU-free unit test suite (`tests/`)

---

## ⚠️ Honest Limitations

* **Handwriting reading is best-effort.** Garbled or ambiguous entries are
  flagged with an amber "ask your pharmacist" badge rather than guessed —
  expect flags on messy cursive or shadowed photos.
* **Spoken answers are English** (the model's speech output supports English
  and Chinese). Hindi/Bengali appear as on-screen text; the Hindi/Bengali
  template strings currently show English placeholders pending native review.
* Voice is **turn-based** (record → answer), not a live conversation.
* GrandmaCare never replaces a pharmacist — the confirm step and review
  badges exist precisely because OCR of handwriting cannot be fully trusted.

---

## 🎯 Hackathon Alignment

GrandmaCare directly addresses the **Backyard AI** challenge by solving a real problem for elderly family members and caregivers.

The project emphasizes:

* Real-world impact
* Small-model deployment
* Accessibility
* Local-language support
* Human-centered design

---

## 📁 Project Structure

```text
grandmacare/
│
├── app.py
├── requirements.txt
├── README.md
│
├── frontend/
├── backend/
├── components/
├── assets/
└── examples/
```

---

## 🚀 Getting Started

### Clone the Repository

```bash
git clone https://github.com/Ro-opkatha/grandmacare.git
cd grandmacare
```

### Create a Virtual Environment

```bash
python -m venv venv
```

### Activate the Environment

Windows:

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
python app.py
```

---

## 👥 Team

* Roopkatha Bhattacharjee
* Soumyajit Ray

---

## ❤️ Vision

Technology should empower people, not exclude them.

GrandmaCare is built with the belief that elderly individuals deserve healthcare tools that speak their language, respect their needs, and help them maintain independence with confidence.
