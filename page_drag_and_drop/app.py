from flask import Flask, request, send_from_directory
from process_input import process_pdf, process_text
import tempfile
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('.', 'interface.html')

@app.route('/upload', methods=['POST'])
def upload_pdf():
    pdf_file = request.files.get('pdf')
    if not pdf_file or not pdf_file.filename.endswith(".pdf"):
        return "Invalid file", 400

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_file.save(tmp.name)
        output = process_pdf(tmp.name)
    
    return output

@app.route('/submit-text', methods=['POST'])
def submit_text():
    data = request.get_json()
    user_text = data.get("text", "")
    output = process_text(user_text)
    return output

if __name__ == '__main__':
    app.run(debug=True)
