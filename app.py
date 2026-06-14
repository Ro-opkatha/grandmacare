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
from backend.reminders import schedule_reminder, split_due
from backend.schema import group_by_timing
from backend.render import (
    GROUP_COLORS,
    alarm_caveat,
    empty_transcript,
    empty_view,
    render_card_body,
    render_freestyle,
    render_group_header,
    render_notice,
    render_pill_result,
    render_transcript,
    say_text,
)


@spaces.GPU(duration=60)
def speak(text):
    # On-demand TTS: a card's 🔊 Listen button (or a fired reminder) sends its
    # romanized text here; the returned waveform autoplays in the voice player.
    # Returns None for empty text, so it is a cheap no-op on idle reminder ticks.
    return synthesize_voice(text)


def add_reminder(alarms, minutes, name, say):
    # Relative, server-side reminder (no wall-clock/timezone assumptions —
    # HF Spaces runs in UTC). Pure logic lives in backend.reminders.
    alarms, minutes = schedule_reminder(alarms, minutes, name, say)
    return alarms, f"⏰ Reminder set for {name} in {minutes} min"


def check_due(alarms):
    # Runs every timer tick (cheap, no GPU). Splits out reminders whose deadline
    # has passed, shows the banner, and hands the first due line to due_say —
    # whose .change fires speak() so the GPU is touched only when one fires.
    due, remaining = split_due(alarms)
    if not due:
        return remaining, gr.update(visible=False), ""
    names = ", ".join(a["med"] for a in due)
    banner = gr.update(visible=True, value=f"🔔 Time to take {names}")
    return remaining, banner, due[0]["say"]


@spaces.GPU(duration=180)
def analyze(image_path, language):
    # Sets session state; the @gr.render schedule block rebuilds the cards
    # whenever that state changes (no schedule HTML returned here).
    try:
        transcript = transcribe_prescription(image_path)
    except Exception as exc:
        message = f"Sorry, I could not read this image yet: {exc}"
        return [
            message,
            None,
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
        return [status, state, render_transcript(transcript), debug_json]

    status = "Prescription analyzed. Please confirm the schedule with a doctor or pharmacist."
    return [status, state, render_transcript(transcript), debug_json]


@spaces.GPU(duration=120)
def pill_check(pill_image_path, state):
    if not state or not state.get("medicines"):
        return render_notice("Please analyze a prescription first, then check your medicine.")

    try:
        result = identify_pill(pill_image_path, state["medicines"], state["language"])
        return render_pill_result(result)
    except Exception as exc:
        return render_notice(f"Sorry, I could not check this medicine yet: {exc}")


APP_CSS = open("frontend/styles.css", encoding="utf-8").read()

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

    # Shared voice player. Each card's native 🔊 Listen button (and a fired
    # reminder) outputs VoxCPM audio here, which autoplays.
    voice_player = gr.Audio(
        label="🔊 Voice",
        autoplay=True,
        interactive=False,
        elem_id="gc-tts-audio",
    )

    # Relative reminders, fully server-side. alarm_state holds pending reminders;
    # a Timer ticks every 15s and check_due() fires the ones whose deadline passed.
    alarm_state = gr.State([])
    reminder_banner = gr.HTML(visible=False, elem_id="gc-reminder-banner")
    reminder_timer = gr.Timer(15)
    due_say = gr.State("")

    @gr.render(inputs=[session, view_toggle])
    def render_schedule(state, view):
        if not state or not state.get("medicines"):
            gr.HTML(render_freestyle(state.get("raw", "")) if state else empty_view())
            return

        medicines = state["medicines"]
        if view == "By time":
            groups = list(enumerate(group_by_timing(medicines)))
        else:
            groups = [(None, (None, medicines))]

        for index, (label, group) in groups:
            if label is not None:
                color = GROUP_COLORS[index % len(GROUP_COLORS)]
                gr.HTML(render_group_header(label, color))
            for medicine in group:
                with gr.Group(elem_classes=["medicine-card-wrap"]):
                    gr.HTML(render_card_body(medicine))
                    say_state = gr.State(say_text(medicine))
                    name_state = gr.State(medicine.get("name", "Medicine"))
                    with gr.Row():
                        listen = gr.Button("🔊 Listen", elem_classes=["sound-btn"])
                        listen.click(speak, inputs=[say_state], outputs=[voice_player])
                        minutes = gr.Number(
                            value=30,
                            precision=0,
                            minimum=1,
                            label="Remind in (min)",
                        )
                        set_reminder = gr.Button(
                            "Set reminder", elem_classes=["alarm-set"]
                        )
                        feedback = gr.Markdown(elem_classes=["alarm-status"])
                    set_reminder.click(
                        add_reminder,
                        inputs=[alarm_state, minutes, name_state, say_state],
                        outputs=[alarm_state, feedback],
                    )
        gr.HTML(alarm_caveat())

    # Tick: cheap, no GPU. Only an actual due reminder changes due_say, whose
    # .change fires speak() — so the GPU is never touched on an idle tick.
    reminder_timer.tick(
        check_due,
        inputs=[alarm_state],
        outputs=[alarm_state, reminder_banner, due_say],
    )
    due_say.change(speak, inputs=[due_say], outputs=[voice_player])

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
        inputs=[prescription, language],
        outputs=[status, session, transcript_view, debug],
    )
    # The @gr.render schedule block re-runs automatically on session/view_toggle
    # change, so no explicit re-render wiring is needed here.
    pill_button.click(
        pill_check,
        inputs=[pill_image, session],
        outputs=[pill_result],
    )


if __name__ == "__main__":
    demo.launch(css=APP_CSS)
