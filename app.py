import gradio as gr


with gr.Blocks(
    title="DidaCare",
    css=open("frontend/styles.css", encoding="utf-8").read(),
    theme=gr.themes.Soft(
        primary_hue="orange",
        secondary_hue="rose",
        neutral_hue="slate",
        font=["Segoe UI", "Noto Sans Bengali", "Noto Sans Devanagari", "Arial", "sans-serif"],
    ),
) as demo:
    gr.HTML(
        """
        <section class="dc-hero">
            <div>
                <p class="dc-kicker">AI medicine assistant</p>
                <h1>DidaCare</h1>
                <p class="dc-subtitle">A warm, simple dashboard for medicine times, voice help, and family confidence.</p>
            </div>
            <div class="dc-mode-pill">
                <span class="dc-mode-dot"></span>
                Grandma Mode visible
            </div>
        </section>
        """
    )

    with gr.Row(elem_classes=["dc-dashboard-row"]):
        with gr.Column(scale=2, elem_classes=["dc-schedule-panel"]):
            gr.HTML(
                """
                <section class="dc-panel-heading">
                    <div>
                        <p class="dc-kicker">Today's medicine schedule</p>
                        <h2>What to take next</h2>
                    </div>
                    <div class="dc-next-dose">
                        <span>Next</span>
                        <strong>8:00 AM</strong>
                    </div>
                </section>

                <div class="dc-schedule-grid">
                    <article class="dc-dose-tile dc-dose-active">
                        <div class="dc-dose-time">Morning</div>
                        <div class="dc-dose-icon">Sun</div>
                        <h3>After breakfast</h3>
                        <p>Awaiting prescription analysis</p>
                    </article>
                    <article class="dc-dose-tile">
                        <div class="dc-dose-time">Afternoon</div>
                        <div class="dc-dose-icon">Day</div>
                        <h3>After lunch</h3>
                        <p>No medicines added yet</p>
                    </article>
                    <article class="dc-dose-tile">
                        <div class="dc-dose-time">Night</div>
                        <div class="dc-dose-icon">Moon</div>
                        <h3>Before sleep</h3>
                        <p>Awaiting prescription analysis</p>
                    </article>
                </div>
                """
            )

        with gr.Column(scale=1, elem_classes=["dc-side-stack"]):
            gr.HTML(
                """
                <section class="dc-action-tile dc-voice-tile">
                    <div class="dc-tile-icon">Voice</div>
                    <h2>Voice Assistant</h2>
                    <p>Hear instructions in a calm, clear voice.</p>
                    <span>Start listening</span>
                </section>
                """
            )
            gr.HTML(
                """
                <section class="dc-action-tile dc-grandma-tile">
                    <div class="dc-tile-icon">Aa</div>
                    <h2>Grandma Mode</h2>
                    <p>Large text, soft contrast, fewer choices.</p>
                    <span>Always visible</span>
                </section>
                """
            )

    with gr.Row(elem_classes=["dc-dashboard-row", "dc-input-row"]):
        with gr.Column(elem_classes=["dc-input-card"]):
            gr.HTML(
                """
                <div class="dc-input-heading">
                    <div class="dc-tile-icon">Rx</div>
                    <div>
                        <h2>Upload Prescription</h2>
                        <p>Take a photo or add an image of the medicine list.</p>
                    </div>
                </div>
                """
            )
            prescription = gr.Image(
                type="filepath",
                show_label=False,
                height=250,
                elem_classes=["dc-prescription-input"],
            )

        with gr.Column(elem_classes=["dc-input-card"]):
            gr.HTML(
                """
                <div class="dc-input-heading">
                    <div class="dc-tile-icon">Lang</div>
                    <div>
                        <h2>Choose Language</h2>
                        <p>Simple words for English, Bengali, and Hindi speakers.</p>
                    </div>
                </div>
                """
            )
            language = gr.Radio(
                ["English", "বাংলা", "हिन्दी"],
                value="English",
                show_label=False,
                elem_classes=["dc-language-radio"],
            )

    gr.HTML(
        """
        <section class="dc-family-strip">
            <strong>Family note</strong>
            <span>DidaCare highlights medicine timing first, keeps voice help close, and makes every tap large.</span>
        </section>
        """
    )

demo.launch()
