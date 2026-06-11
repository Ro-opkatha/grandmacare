import json

import gradio as gr
import spaces

from backend import brain, ears, eyes
from backend.preprocess import preprocess_prescription
from backend.render import initial_cards, render_answer_card, render_cards


CHECK_MESSAGE = (
    "Here is what I read from the prescription. Please check every card, "
    "then press “This is correct”."
)
CONFIRMED_MESSAGE = (
    "Schedule confirmed. Ask questions out loud in your own language, or show "
    "me your medicines when it is time to take them."
)
START_MESSAGE = "Take a photo of the prescription to begin."

CLIENT_TIME_JS = (
    "(confirmed, photo, time, language) => [confirmed, photo, "
    "new Date().toLocaleString([], {weekday: 'long', hour: 'numeric', "
    "minute: '2-digit'}), language]"
)


def _analyze_error(message):
    return [
        f"Sorry, I could not read this image yet: {message}",
        json.dumps({"error": str(message)}, ensure_ascii=False, indent=2),
        initial_cards(),
        None,                      # pending
        None,                      # confirmed
        gr.update(visible=False),  # confirm row
        gr.update(visible=False),  # voice section
        gr.update(visible=False),  # medicine-time section
    ]


@spaces.GPU(duration=180)
def analyze(image_path, language):
    if not image_path:
        return _analyze_error("please upload a prescription photo first.")
    try:
        processed_path = preprocess_prescription(image_path)
        digital_copy = eyes.transcribe_prescription(processed_path)   # eyes: verbatim
        cards = brain.build_cards(digital_copy, language)             # brain: cards
        if not cards["medicines"]:
            return _analyze_error("I could not find any readable medicines.")
        debug_json = json.dumps(
            {"digital_copy": digital_copy, "cards": cards},
            ensure_ascii=False,
            indent=2,
        )
        pending = {
            "image_path": processed_path,
            "digital_copy": digital_copy,
            "cards": cards,
        }
        return [
            CHECK_MESSAGE,
            debug_json,
            render_cards(cards),
            pending,
            None,                      # confirmed context resets on re-analysis
            gr.update(visible=True),   # confirm row
            gr.update(visible=False),  # voice section
            gr.update(visible=False),  # medicine-time section
        ]
    except Exception as exc:
        return _analyze_error(exc)


def confirm_schedule(pending):
    if not pending:
        return (
            gr.update(visible=False),
            None,
            gr.update(visible=False),
            gr.update(visible=False),
            "Please read a prescription first.",
        )
    return (
        gr.update(visible=False),
        pending,
        gr.update(visible=True),
        gr.update(visible=True),
        CONFIRMED_MESSAGE,
    )


def retake_photo():
    return [
        None,
        "Take a new photo in good, even light — avoid shadows on the page.",
        initial_cards(),
        None,
        None,
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        json.dumps({"medicines": []}, indent=2),
    ]


@spaces.GPU(duration=120)
def ask_voice(confirmed, audio_path, language):
    if not confirmed:
        return (
            render_answer_card("Please confirm your medicine cards first."),
            gr.update(),
            confirmed,
            language,
            gr.update(),
        )
    try:
        question = ears.transcribe_audio(audio_path)                  # ears
        reply = brain.answer(question, confirmed["digital_copy"], confirmed["cards"])
        status = f"You asked: {question}"

        cards_update = gr.update()
        detected = brain.detect_language(question)
        if detected != language:
            # She spoke a new language — re-explain the cards in it too.
            cards = brain.build_cards(confirmed["digital_copy"], detected)
            if cards["medicines"]:
                confirmed = {**confirmed, "cards": cards}
                cards_update = render_cards(cards)
            language = detected

        return render_answer_card(reply), cards_update, confirmed, language, status
    except Exception as exc:
        return (
            render_answer_card(f"Sorry, I could not answer that: {exc}"),
            gr.update(),
            confirmed,
            language,
            gr.update(),
        )


@spaces.GPU(duration=120)
def medicine_time(confirmed, photo_path, client_time, language):
    if not confirmed:
        return render_answer_card("Please read and confirm your prescription first.")
    if not photo_path:
        return render_answer_card("Please take a photo of your medicines first.")
    try:
        finding = eyes.identify_medicine_now(photo_path, confirmed["cards"], client_time)
        reply = brain.phrase_medicine_time(finding, client_time, language)
        return render_answer_card(reply)
    except Exception as exc:
        return render_answer_card(f"Sorry, I could not check that: {exc}")


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

        analyze_button = gr.Button(
            "📋 Read my prescription", variant="primary", elem_classes=["big-button"]
        )
        status = gr.Textbox(
            value=START_MESSAGE,
            show_label=False,
            interactive=False,
            elem_classes=["status-box"],
        )

        gr.HTML('<div class="section-title">2 · Your medicines</div>')
        cards_html = gr.HTML(initial_cards())

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
                <p class="voice-hint">Press record and ask out loud, in your own
                language. I will answer in writing, in your language — no typing
                needed.</p>
                """
            )
            voice_input = gr.Audio(
                sources=["microphone"], type="filepath", show_label=False
            )
            ask_button = gr.Button(
                "🎤 Ask GrandmaCare", variant="primary", elem_classes=["big-button"]
            )
            answer_html = gr.HTML("")

        with gr.Column(visible=False, elem_classes=["voice-section"]) as medtime_section:
            gr.HTML(
                """
                <div class="section-title">4 · Time for your medicine?</div>
                <p class="voice-hint">Show me your medicines with the camera and
                I will tell you which one to take right now.</p>
                """
            )
            med_photo = gr.Image(
                sources=["webcam"], type="filepath", show_label=False, height=320
            )
            medtime_button = gr.Button(
                "🕐 Which medicine do I take now?",
                variant="primary",
                elem_classes=["big-button"],
            )
            medtime_answer = gr.HTML("")

        with gr.Accordion("Details for the pharmacist (digital copy)", open=False):
            debug = gr.Code(
                value=json.dumps({"medicines": []}, indent=2),
                language="json",
                show_label=False,
            )

    pending_state = gr.State(None)
    confirmed_state = gr.State(None)
    language_state = gr.State("English")   # auto-detected from speech, never selected
    client_time = gr.Textbox(visible=False)

    analyze_button.click(
        analyze,
        inputs=[prescription, language_state],
        outputs=[
            status,
            debug,
            cards_html,
            pending_state,
            confirmed_state,
            confirm_row,
            voice_section,
            medtime_section,
        ],
    )
    confirm_button.click(
        confirm_schedule,
        inputs=[pending_state],
        outputs=[confirm_row, confirmed_state, voice_section, medtime_section, status],
    )
    retake_button.click(
        retake_photo,
        outputs=[
            prescription,
            status,
            cards_html,
            pending_state,
            confirmed_state,
            confirm_row,
            voice_section,
            medtime_section,
            debug,
        ],
    )
    ask_button.click(
        ask_voice,
        inputs=[confirmed_state, voice_input, language_state],
        outputs=[answer_html, cards_html, confirmed_state, language_state, status],
    )
    medtime_button.click(
        medicine_time,
        inputs=[confirmed_state, med_photo, client_time, language_state],
        outputs=[medtime_answer],
        js=CLIENT_TIME_JS,
    )


if __name__ == "__main__":
    demo.launch()
