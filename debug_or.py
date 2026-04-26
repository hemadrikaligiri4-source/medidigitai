import requests
import json

OPENROUTER_API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "google/gemini-2.0-flash-lite-preview-02-05:free",
    "messages": [
        {"role": "user", "content": "hi"}
    ]
}

r = requests.post(API_URL, headers=headers, json=payload)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
