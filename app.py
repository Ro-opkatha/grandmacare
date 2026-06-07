import gradio as gr

with gr.Blocks() as demo:
    gr.Markdown("# DidaCare")
    gr.Markdown("Upload a prescription and get medicine guidance.")

    image = gr.Image(type="filepath")
    output = gr.Textbox(label="Result")

    btn = gr.Button("Analyze")

demo.launch()