import json

import gradio as gr
import spaces

from backend.models import analyze_prescription, answer_question
from backend.render import (
    initial_bucket,
    initial_extras,
    render_all_buckets,
    render_extras,
)


CHECK_MESSAGE = (
    "Here is what I read from the prescription. Please check every card, "
    "then press “This is correct”."
)
CONFIRMED_MESSAGE = (
    "Schedule confirmed. You can now ask questions out loud — "
    "press the microphone below."
)


@spaces.GPU(duration=120)
def analyze(image_path, language):
    try:
        result = analyze_prescription(image_path, language)
        schedule = result["schedule"]
        buckets = render_all_buckets(schedule)
        debug_json = json.dumps(
            {"schedule": schedule, "transcript": result["transcript"]},
            ensure_ascii=False,
            indent=2,
        )
        pending = {"image_path": result["image_path"], "schedule": schedule}
        return [
            CHECK_MESSAGE,
            debug_json,
            *buckets,
            render_extras(schedule),
            pending,
            None,                      # confirmed context resets on re-analysis
            gr.update(visible=True),   # confirm row
            gr.update(visible=False),  # voice section
        ]
    except Exception as exc:
        message = f"Sorry, I could not analyze this image yet: {exc}"
        return [
            message,
            json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
            initial_bucket("morning"),
            initial_bucket("afternoon"),
            initial_bucket("evening"),
            initial_bucket("night"),
            initial_extras(),
            None,
            None,
            gr.update(visible=False),
            gr.update(visible=False),
        ]


def confirm_schedule(pending):
    if not pending:
        return (
            gr.update(visible=False),
            None,
            gr.update(visible=False),
            "Please analyze a prescription first.",
        )
    return (
        gr.update(visible=False),
        pending,
        gr.update(visible=True),
        CONFIRMED_MESSAGE,
    )


def retake_photo():
    return [
        None,
        "Take a new photo in good, even light — avoid shadows on the page.",
        initial_bucket("morning"),
        initial_bucket("afternoon"),
        initial_bucket("evening"),
        initial_bucket("night"),
        initial_extras(),
        None,
        None,
        gr.update(visible=False),
        gr.update(visible=False),
        json.dumps({"medicines": []}, indent=2),
    ]


@spaces.GPU(duration=90)
def ask_voice(confirmed, audio_path):
    if not confirmed:
        return "Please confirm your medicine schedule first.", None
    try:
        text, audio_out = answer_question(
            confirmed["image_path"], confirmed["schedule"], audio_path
        )
        return text, audio_out
    except Exception as exc:
        return f"Sorry, I could not answer that: {exc}", None


with gr.Blocks(
    title="GrandmaCare",
    css=open("frontend/styles.css", encoding="utf-8").read(),
) as demo:
    with gr.Column(elem_classes=["page"]):
        gr.HTML(
            """
            <div class="hero">
                <h1>GrandmaCare</h1>
                <h3>Your Medicine Companion</h3>
                <p>Helping grandparents understand medicines confidently.</p>
            </div>
            """
        )

        gr.HTML('<div class="section-title">1 · Take a photo of the prescription</div>')
        prescription = gr.Image(type="filepath", show_label=False, height=320)

        gr.HTML('<div class="section-title">2 · Choose your language</div>')
        language = gr.Radio(
            ["English", "Hindi", "Bengali"],
            value="English",
            show_label=False,
            elem_classes=["language-radio"],
        )

        analyze_button = gr.Button(
            "📋 Read my prescription", variant="primary", elem_classes=["big-button"]
        )
        status = gr.Textbox(
            value="Upload a prescription photo and choose a language.",
            show_label=False,
            interactive=False,
            elem_classes=["status-box"],
        )

        morning = gr.HTML(initial_bucket("morning"))
        afternoon = gr.HTML(initial_bucket("afternoon"))
        evening = gr.HTML(initial_bucket("evening"))
        night = gr.HTML(initial_bucket("night"))
        extras = gr.HTML(initial_extras())

        with gr.Row(visible=False, elem_classes=["confirm-row"]) as confirm_row:
            confirm_button = gr.Button(
                "✓ This is correct", variant="primary", elem_classes=["big-button"]
            )
            retake_button = gr.Button(
                "↺ Re-take photo", elem_classes=["big-button", "secondary-button"]
            )

        with gr.Column(visible=False, elem_classes=["voice-section"]) as voice_section:
            gr.HTML(
                """
                <div class="section-title">3 · Ask me anything about your medicines</div>
                <p class="voice-hint">Press record, ask your question out loud,
                then press “Ask”. I answer with my voice in English.</p>
                """
            )
            voice_input = gr.Audio(
                sources=["microphone"], type="filepath", show_label=False
            )
            ask_button = gr.Button(
                "🎤 Ask GrandmaCare", variant="primary", elem_classes=["big-button"]
            )
            answer_text = gr.Textbox(
                show_label=False, interactive=False, elem_classes=["answer-box"]
            )
            answer_audio = gr.Audio(show_label=False, autoplay=True)

        with gr.Accordion("Details for the pharmacist (JSON)", open=False):
            debug = gr.Code(
                value=json.dumps({"medicines": []}, indent=2),
                language="json",
                show_label=False,
            )

    pending_state = gr.State(None)
    confirmed_state = gr.State(None)

    analyze_button.click(
        analyze,
        inputs=[prescription, language],
        outputs=[
            status,
            debug,
            morning,
            afternoon,
            evening,
            night,
            extras,
            pending_state,
            confirmed_state,
            confirm_row,
            voice_section,
        ],
    )
    confirm_button.click(
        confirm_schedule,
        inputs=[pending_state],
        outputs=[confirm_row, confirmed_state, voice_section, status],
    )
    retake_button.click(
        retake_photo,
        outputs=[
            prescription,
            status,
            morning,
            afternoon,
            evening,
            night,
            extras,
            pending_state,
            confirmed_state,
            confirm_row,
            voice_section,
            debug,
        ],
    )
    ask_button.click(
        ask_voice,
        inputs=[confirmed_state, voice_input],
        outputs=[answer_text, answer_audio],
    )


if __name__ == "__main__":
    demo.launch()
