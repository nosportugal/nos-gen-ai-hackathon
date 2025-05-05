# Gemini 2.0 Tutorial

In this tutorial, you will learn how to:

1. Set up your API key  
2. Use the Gemini API

---

## 1. Set up your API key

1. Go to: [https://aistudio.google.com/](https://aistudio.google.com/)  
2. Log in with your Google account.  
3. Click the **"Get API key"** button.  
4. Then click on **"Create API key"** or **"Criar chave de API"**. This will open a window to create an API on a new project.  
5. Copy the generated API key.  

🎉 You are all set!

---

## 2. Use the Gemini API

Below are code examples on how to use the API. Adapt the examples to match your solution.

```python
import requests

# Replace this with your actual API key
API_KEY = "AbCdEfGhIjKlmnopq"
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
