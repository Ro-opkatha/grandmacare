---
title: GrandmaCare
emoji: 👵
colorFrom: red
colorTo: green
sdk: gradio
sdk_version: 6.16.0
app_file: app.py
python_version: 3.12
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

### 🔊 Voice Assistance

Coming later: the MVP keeps romanized text ready for future VoxCPM-powered speech.

### 👴 Senior-Friendly Interface

Designed with:

* Large fonts
* Clear navigation
* Minimal cognitive load
* Accessible layouts

---

## 🏗️ System Architecture

Prescription Image

↓
MiniCPM-V

↓
Medicine Information Extraction

↓
Structured Medication Schedule

↓
Multilingual Instruction Generation

↓
Romanized Guidance & User Interface

---

## 🛠️ Tech Stack

### Frontend

* Gradio
* Python

### AI Models

* OpenBMB MiniCPM-V 4.6
* CohereLabs tiny-aya-global

### Additional Components

* Multilingual instruction generation
* Medication schedule engine
* Romanized text seam for future Text-to-Speech (TTS)

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
