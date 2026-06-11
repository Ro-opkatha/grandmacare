import json

import gradio as gr
import spaces

from backend.models import analyze_prescription
from backend.render import initial_bucket, render_all_buckets


def voice_coming_later():
    return "Voice guide is coming later. For now, please use the romanized text shown on each medicine card."


@spaces.GPU(duration=120)
def analyze(image_path, language):
    try:
        schedule = analyze_prescription(image_path, language)
        buckets = render_all_buckets(schedule)
        status = "Prescription analyzed. Please confirm the schedule with a doctor or pharmacist."
        debug_json = json.dumps(schedule, ensure_ascii=False, indent=2)
        return [status, debug_json, *buckets]
    except Exception as exc:
        message = f"Sorry, I could not analyze this image yet: {exc}"
        return [
            message,
            json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
            initial_bucket("morning"),
            initial_bucket("afternoon"),
            initial_bucket("evening"),
            initial_bucket("night"),
        ]


with gr.Blocks(
    title="GrandmaCare",
    css=open("frontend/styles.css", encoding="utf-8").read(),
) as demo:
    gr.HTML(
        """
        <div class="tile white">
            <h1>GrandmaCare</h1>
            <h3>Your Medicine Companion</h3>
            <p>Helping grandparents understand medicines confidently.</p>
        </div>
        """
    )

    with gr.Row():
        with gr.Column():
            gr.HTML(
                """
                <div class="tile red control-tile">
                    <div class="tile-icon document"></div>
                    <div class="tile-title">Upload</div>
                    <div class="tile-subtitle">Prescription</div>
                </div>
                """
            )
            prescription = gr.Image(type="filepath", show_label=False)

        with gr.Column():
            gr.HTML(
                """
                <div class="tile orange control-tile">
                    <div class="tile-icon globe"></div>
                    <div class="tile-title">Language</div>
                    <div class="tile-subtitle">Choose Language</div>
                </div>
                """
            )
            language = gr.Radio(
                ["English", "Hindi", "Bengali"],
                value="English",
                show_label=False,
            )

    analyze_button = gr.Button("Analyze prescription", variant="primary")
    status = gr.Textbox(
        value="Upload a prescription photo and choose a language.",
        show_label=False,
        interactive=False,
        elem_classes=["status-box"],
    )

    with gr.Row():
        morning = gr.HTML(initial_bucket("morning"))
        afternoon = gr.HTML(initial_bucket("afternoon"))

    with gr.Row():
        evening = gr.HTML(initial_bucket("evening"))
        night = gr.HTML(initial_bucket("night"))

    with gr.Row():
        voice_button = gr.Button(
            "🔊\nVoice Guide\nComing Later",
            elem_classes=["voice-button"],
        )
        gr.HTML(
            """
            <div class="tile teal control-tile">
                <div class="tile-icon glasses"></div>
                <div class="tile-title">Grandma Mode</div>
                <div class="tile-subtitle">Large Text</div>
            </div>
            """
        )

    voice_status = gr.Textbox(show_label=False, interactive=False, visible=True)

    with gr.Accordion("Final JSON", open=False):
        debug = gr.Code(
            value=json.dumps({"medicines": []}, indent=2),
            language="json",
            show_label=False,
        )

    analyze_button.click(
        analyze,
        inputs=[prescription, language],
        outputs=[status, debug, morning, afternoon, evening, night],
    )
    voice_button.click(voice_coming_later, outputs=voice_status)


if __name__ == "__main__":
    demo.launch()
