import json

import gradio as gr
import spaces

from backend.models import (
    extract_cards,
    identify_pill,
    synthesize_voice,
    transcribe_prescription,
    translate_cards,
)
from backend.render import (
    empty_transcript,
    empty_view,
    render_freestyle,
    render_notice,
    render_pill_result,
    render_transcript,
    render_view,
)


@spaces.GPU(duration=60)
def speak(text):
    # On-demand TTS: a card's 🔊 button sends its romanized text here and the
    # returned waveform autoplays in the shared voice player.
    return synthesize_voice(text)


@spaces.GPU(duration=180)
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
        medicines, raw_text = extract_cards(image_path)
        medicines = translate_cards(medicines, language)
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

    state = {
        "transcript": transcript,
        "language": language,
        "medicines": medicines,
        "raw": raw_text,
    }
    debug_json = json.dumps(
        {"medicines": medicines, "raw": raw_text}, ensure_ascii=False, indent=2
    )

    if not medicines:
        status = (
            "I wrote out the schedule as best I could. Please confirm it with a "
            "doctor or pharmacist."
        )
        return [
            status,
            state,
            render_freestyle(raw_text),
            render_transcript(transcript),
            debug_json,
        ]

    status = "Prescription analyzed. Please confirm the schedule with a doctor or pharmacist."
    return [
        status,
        state,
        render_view(medicines, view),
        render_transcript(transcript),
        debug_json,
    ]


@spaces.GPU(duration=120)
def pill_check(pill_image_path, state):
    if not state or not state.get("medicines"):
        return render_notice("Please analyze a prescription first, then check your medicine.")

    try:
        result = identify_pill(pill_image_path, state["medicines"], state["language"])
        return render_pill_result(result)
    except Exception as exc:
        return render_notice(f"Sorry, I could not check this medicine yet: {exc}")


def rerender(view, state):
    if not state:
        return empty_view()
    if not state.get("medicines"):
        return render_freestyle(state.get("raw", ""))
    return render_view(state["medicines"], view)


APP_CSS = open("frontend/styles.css", encoding="utf-8").read()
APP_JS = open("frontend/alarm.js", encoding="utf-8").read()

with gr.Blocks(title="GrandmaCare") as demo:
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

    # Shared voice player. A card's 🔊 button fills the hidden textbox and
    # clicks the hidden trigger; speak() returns audio that autoplays here.
    voice_player = gr.Audio(
        label="🔊 Voice",
        autoplay=True,
        interactive=False,
        elem_id="gc-tts-audio",
    )
    tts_text = gr.Textbox(visible=False, elem_id="gc-tts-text")
    tts_trigger = gr.Button(visible=False, elem_id="gc-tts-trigger")
    tts_trigger.click(speak, inputs=[tts_text], outputs=[voice_player])

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

    gr.HTML(
        """
        <div class="tile purple control-tile">
            <div class="tile-icon glasses"></div>
            <div class="tile-title">Grandma Mode</div>
            <div class="tile-subtitle">Large Text</div>
        </div>
        """
    )

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

    # Load the voice + alarm engine on page load. demo.load(js=...) is the
    # reliable on-load JS hook (launch(js=...) does not run it in Gradio 6).
    demo.load(None, None, None, js=APP_JS)


if __name__ == "__main__":
    demo.launch(css=APP_CSS)
