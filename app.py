import gradio as gr

with gr.Blocks(
    title="DidaCare",
    css=open("frontend/styles.css").read()
) as demo:

    gr.HTML("""
    <div class="hero">
        <h1>👵 DidaCare</h1>
        <h3>Your Medicine Companion</h3>
        <p>Helping grandparents understand medicines confidently.</p>
    </div>
    """)

    with gr.Row():

        with gr.Column():

            gr.HTML("""
            <div class="tile red">
                <div class="tile-icon">📄</div>
                <div class="tile-title">Upload</div>
                <div class="tile-subtitle">Prescription</div>
            </div>
            """)

            prescription = gr.Image(
                type="filepath",
                show_label=False
            )

        with gr.Column():

            gr.HTML("""
            <div class="tile orange">
                <div class="tile-icon">🌐</div>
                <div class="tile-title">Language</div>
                <div class="tile-subtitle">Choose Language</div>
            </div>
            """)

            language = gr.Radio(
                ["English", "বাংলা", "हिन्दी"],
                value="English",
                show_label=False
            )

    with gr.Row():

        morning = gr.HTML("""
        <div class="tile blue">
            <div class="tile-icon">☀</div>
            <div class="tile-title">Morning</div>
            <div class="tile-subtitle">
                Awaiting Analysis
            </div>
        </div>
        """)

        night = gr.HTML("""
        <div class="tile green">
            <div class="tile-icon">🌙</div>
            <div class="tile-title">Night</div>
            <div class="tile-subtitle">
                Awaiting Analysis
            </div>
        </div>
        """)

    with gr.Row():

        gr.HTML("""
        <div class="tile purple">
            <div class="tile-icon">🔊</div>
            <div class="tile-title">Voice Guide</div>
            <div class="tile-subtitle">
                Listen Instructions
            </div>
        </div>
        """)

        gr.HTML("""
        <div class="tile teal">
            <div class="tile-icon">👓</div>
            <div class="tile-title">Grandma Mode</div>
            <div class="tile-subtitle">
                Large Text
            </div>
        </div>
        """)

demo.launch()