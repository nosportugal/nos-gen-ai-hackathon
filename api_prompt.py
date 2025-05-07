import requests
import yaml
import os
from text_utils import extract_text_from_pdf, remove_all_special_characters

API_KEY_FILE = os.path.abspath("nos-gen-ai-hackathon/API_key.yaml")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key="
FILE = "/home/rods/Documents/Nos_gen_ai/nos-gen-ai-hackathon/raw_data/document_to_anonymize.pdf"


def load_api_key(file_path: str) -> dict:
    if (os.path.exists("nos-gen-ai-hackathon/API_key.yaml") == False):
        with open(API_KEY_FILE, 'w') as file:
            key = input("You don't have a key set yet. Please enter your Google API key:\n")
            file.write(f"GOOGLE_API_KEY: {key}")
        
    # Replace this with your actual API key
    with open(os.path.abspath("nos-gen-ai-hackathon/API_key.yaml"), 'r') as file:
        return yaml.safe_load(file)

keys = load_api_key(API_KEY_FILE)

API_KEY = keys["GOOGLE_API_KEY"] 


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

    response = requests.post(API_URL + API_KEY, headers=headers, json=body)

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
initial_prompt = "You are a helpful assistant. Please summarize the following text:\n"
file_prompt = read_file(FILE)
output = generate_content(initial_prompt + file_prompt, 0.0)
# Get only the response text
response_text = output['candidates'][0]['content']['parts'][0]['text']

print(response_text)