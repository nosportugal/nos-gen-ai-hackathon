import sys
import requests
from PyPDF2 import PdfReader

# Configuração da API do Gemini
API_KEY = "AIzaSyDDSnGtZ0XZYkh-i4taALEjy5_6b3PhJYc"  # Substituir pela tua chave real
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

def extract_pdf_text(pdf_path: str) -> str:
    """Extrai texto de todas as páginas de um PDF."""
    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        return full_text.strip()
    except Exception as e:
        print(f"Erro ao ler o PDF: {e}")
        sys.exit(1)

def censura(text: str, temperature: float = 0.7) -> dict:
    """Envia um prompt para a API do Gemini para censurar informação pessoal."""
    headers = {
        "Content-Type": "application/json"
    }

    prompt = (
        "Keep the original language of the following text and act as someone that censors personal information "
        "including names, addresses, documents, billing information, salary, etc. "
        "Replace every personal information word with '*' of the same length:\n\n"
        f"{text}"
    )

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature
        }
    }

    response = requests.post(API_URL, headers=headers, json=body)

    if not response.ok:
        print(f"Erro na API Gemini: {response.status_code} {response.text}")
        sys.exit(1)

    return response.json()

def main():
    if len(sys.argv) < 2:
        print("Uso: python script.py <caminho_para_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Extrair texto do PDF
    extracted_text = extract_pdf_text(pdf_path)
    if not extracted_text:
        print("PDF sem texto extraível.")
        sys.exit(1)

    # Enviar para censura via API Gemini
    output = censura(extracted_text, temperature=0.7)

    # Mostrar a resposta censurada
    try:
        response_text = output['candidates'][0]['content']['parts'][0]['text']
        print("Texto censurado:\n")
        print(response_text)
    except (KeyError, IndexError) as e:
        print("Erro ao extrair resposta da API.")
        print(output)

if __name__ == "__main__":
    main()
