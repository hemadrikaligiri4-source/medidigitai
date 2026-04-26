import requests
import json

OPENROUTER_API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:5000", 
    "X-Title": "MedDigit Verification"
}

payload = {
    "model": "google/gemini-2.0-flash-lite-preview-02-05:free",
    "messages": [
        {"role": "system", "content": "You are MedDigit assistant."},
        {"role": "user", "content": "Hello! Are you working?"}
    ]
}

print("Attempting to connect to OpenRouter...")
try:
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        print("Success! Connection established.")
        print("Response:", response.json()['choices'][0]['message']['content'])
    else:
        print(f"Failed. Status: {response.status_code}")
        print("Response:", response.text)
except Exception as e:
    print(f"Error: {e}")
