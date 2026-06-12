import json

import gradio as gr
import spaces

from backend.models import (
    match_pill,
    structure_and_translate,
    transcribe_pill_label,
    transcribe_prescription,
)
from backend.render import (
    empty_transcript,
    empty_view,
    render_notice,
    render_pill_result,
    render_transcript,
    render_view,
)


def voice_coming_later():
    return "Voice guide is coming later. For now, please use the romanized text shown on each medicine card."


@spaces.GPU(duration=120)
def analyze(image_path, language, view):
    try:
        transcript = transcribe_prescription(image_path)
    except Exception as exc:
        message = f"Sorry, I could not read this image yet: {exc}"
        return [
            message,
            None,
            empty_view(),
            empty_transcript(),
            json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
        ]

    try:
        medicines = structure_and_translate(transcript, language)
    except Exception as exc:
        state = {"transcript": transcript, "language": language, "medicines": []}
        message = (
            "I made a digital copy of the prescription but could not build the "
            "schedule. Please check the digital copy below with a pharmacist."
        )
        return [
            message,
            state,
            empty_view(),
            render_transcript(transcript),
            json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
        ]

    state = {"transcript": transcript, "language": language, "medicines": medicines}
    status = "Prescription analyzed. Please confirm the schedule with a doctor or pharmacist."
    debug_json = json.dumps({"medicines": medicines}, ensure_ascii=False, indent=2)
    return [
        status,
        state,
        render_view(medicines, view),
        render_transcript(transcript),
        debug_json,
    ]


@spaces.GPU(duration=90)
def pill_check(pill_image_path, state):
    if not state or not state.get("medicines"):
        return render_notice("Please analyze a prescription first, then check your medicine.")

    try:
        label_text = transcribe_pill_label(pill_image_path)
        result = match_pill(label_text, state["medicines"], state["language"])
        return render_pill_result(result)
    except Exception as exc:
        return render_notice(f"Sorry, I could not check this medicine yet: {exc}")


def rerender(view, state):
    if not state or not state.get("medicines"):
        return empty_view()
    return render_view(state["medicines"], view)


with gr.Blocks(
    title="GrandmaCare",
    css=open("frontend/styles.css", encoding="utf-8").read(),
) as demo:
    session = gr.State(None)

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

    view_toggle = gr.Radio(
        ["By medicine", "By time"],
        value="By medicine",
        show_label=False,
        elem_classes=["view-toggle"],
    )
    schedule_view = gr.HTML(empty_view())

    with gr.Accordion("Digital copy of your prescription", open=False):
        transcript_view = gr.HTML(empty_transcript())

    gr.HTML(
        """
        <div class="tile teal control-tile">
            <div class="tile-icon pill"></div>
            <div class="tile-title">Pill Check</div>
            <div class="tile-subtitle">Which medicine is this?</div>
        </div>
        """
    )
    with gr.Row():
        pill_image = gr.Image(
            type="filepath",
            sources=["upload", "webcam"],
            show_label=False,
        )
        with gr.Column():
            pill_button = gr.Button("Check this medicine", variant="primary")
            pill_result = gr.HTML("")

    with gr.Row():
        voice_button = gr.Button(
            "🔊\nVoice Guide\nComing Later",
            elem_classes=["voice-button"],
        )
        gr.HTML(
            """
            <div class="tile purple control-tile">
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
        inputs=[prescription, language, view_toggle],
        outputs=[status, session, schedule_view, transcript_view, debug],
    )
    view_toggle.change(
        rerender,
        inputs=[view_toggle, session],
        outputs=[schedule_view],
    )
    pill_button.click(
        pill_check,
        inputs=[pill_image, session],
        outputs=[pill_result],
    )
    voice_button.click(voice_coming_later, outputs=voice_status)


if __name__ == "__main__":
    demo.launch()
