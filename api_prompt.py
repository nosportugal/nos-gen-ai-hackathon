import requests
import yaml
import os
from text_utils import extract_text_from_pdf, remove_all_special_characters

API_KEY_FILE = os.path.abspath("nos-gen-ai-hackathon/API_key.yaml")
if (os.path.exists("nos-gen-ai-hackathon/API_key.yaml") == False):
    with open(API_KEY_FILE, 'w') as file:
        key = input("You don't have a key set yet. Please enter your Google API key:\n")
        file.write(f"GOOGLE_API_KEY: {key}")
        
# Replace this with your actual API key
with open(os.path.abspath("nos-gen-ai-hackathon/API_key.yaml"), 'r') as file:
    keys = yaml.safe_load(file)
    
API_KEY = keys["GOOGLE_API_KEY"] 
API_URL = f"https://generativYou are a helpful assistant. Please summarize the following text:\nelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

FILE = "/home/rodrigo/Documents/NOSHackathon/nos-gen-ai-hackathon/raw_data/document_to_anonymize.pdf"

def read_pdf(file_path: str) -> str:
    text = extract_text_from_pdf(file_path)
    return remove_all_special_characters(text)

def generate_content(prompt_text: str, temperature: float) -> dict:
    """Generates content based on the given prompt text and temperature.

    Args:
        prompt_text (str): The text prompt to generate content from.
        temperature (float): The temperature parameter for controlling randomness.
    """

    headers = {
        "Content-Type": "application/json"
    }

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature
        }
    }

    response = requests.post(API_URL, headers=headers, json=body)

    return response.json()

def read_file(file_path: str) -> str:
    """Reads the content of a file and returns it as a string.

    Args:
        file_path (str): The path to the file to read.
    """
    if file_path.endswith('.pdf'):
        return read_pdf(file_path)

    elif file_path.endswith('.txt'):
        with open(file_path, 'r') as file:
            return remove_all_special_characters(file.read())
        
    else:
        raise ValueError("Unsupported file format. Only .pdf and .txt files are supported.")

# Example usage
initial_prompt = """You are a data protection assistant tasked with anonymizing a Portuguese medical document in strict compliance with the GDPR (General Data Protection Regulation). The document contains sensitive personal, biometric, medical, and financial information.

Your goal is to redact or replace all personally identifiable information (PII) and sensitive data so that the resulting text retains its structure and semantic meaning but cannot be used to re-identify the individual(s). all values must be a '*' and non-traceable.

Perform the following transformations:

    Names (People and Professionals): Replace each personal name (patient, children, relatives, doctors, emergency contacts) with asterisks *, one per word in the original name. Do not preserve initials.

    Addresses: Replace each word (including numbers and city names) in any postal address with asterisks.

    Contact Information:

        Phone numbers: Replace with asterisk (*), maintaining the general formatting.

        Email addresses: Replace all characters, including domain names, with asterisk. (e.g., *@*.*)

    Government Identifiers: Replace NIF, Cartão de Cidadão, Segurança Social, and CRM numbers with * per different number.

    Medical History:

        Retain general conditions (e.g., hypertension, diabetes), medications, and clinical findings.

        Replace rare genetic identifiers (e.g., "BRCA1") and highly unique data with the phrase: "*" (known genetic predisposition).

        Replace biometric IDs (e.g., fingerprint ID, facial ID) with *.

    Financial Information:

        Replace health insurance provider name, policy number, income, and credit card number with *.

    Demographics:

        Preserve general descriptors (e.g., man, 35 years old”)

        Remove or mask religious or culturally identifying data with *, unless clinically relevant.

    Professional Details:

        Generalize roles

        Remove or mask the institution name entirely using *.

    Dates:

        Shift or generalize precise dates to "Month Year" format (e.g., “30 de dezembro de 2025” → “dezembro de 2025”).

    Emergency Contacts:

        Replace all names, phone numbers, and emails of emergency contacts with *.

    Digital Signature Block:

        Replace names, CRM, email addresses, and phone numbers with *.

    Additional Compromising Details:

        Censor any other data points that may lead to identification or profiling using the same * policy.

Final Output Instructions:

    Keep the original section headers and layout intact (e.g., "Informações do Paciente", "Histórico Médico").

    Do not include any explanation or comments—output the anonymized document only.

    Ensure no real-world personal data remains in the document.\n\n"""
file_prompt = read_file(FILE)
output = generate_content(initial_prompt + file_prompt, 0.0)
# Get only the response text
response_text = output['candidates'][0]['content']['parts'][0]['text']

print(response_text)