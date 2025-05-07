import requests
import yaml
import os
API_KEY_FILE = os.path.abspath("nos-gen-ai-hackathon/API_key.yaml")
if (os.path.exists("nos-gen-ai-hackathon/API_key.yaml") == False):
    with open(API_KEY_FILE, 'w') as file:
        key = input("You don't have a key set yet. Please enter your Google API key:\n")
        file.write(f"GOOGLE_API_KEY: {key}")
        
# Replace this with your actual API key
with open(os.path.abspath("nos-gen-ai-hackathon/API_key.yaml"), 'r') as file:
    keys = yaml.safe_load(file)
    
API_KEY = keys["GOOGLE_API_KEY"] 
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

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

# Example usage
prompt = "Tell me a one sentence story"
output = generate_content(prompt, 0.0)
# Get only the response text
response_text = output['candidates'][0]['content']['parts'][0]['text']

print(response_text)