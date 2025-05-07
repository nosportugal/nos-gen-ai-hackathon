#####################################################
# This code serves to give the prompt to GEMINI and #
# output the result as a string.                    #
#####################################################

import requests

API_KEY = "AIzaSyCBkJwTvPlz9jR2RTbZLJe7K0rNRci-3CY"
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

#Alter this name in case your prompt .txt has another name
prompt = "Prompt.txt"
output = generate_content(prompt, 0.0)

# Get only the response text
response_text = output['candidates'][0]['content']['parts'][0]['text']