import requests
import json

OPENROUTER_API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:8080",
    "X-Title": "MedDigit Final Test"
}

# Testing the specific free models I added
test_models = [
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "meta-llama/llama-3.1-405b-instruct:free",
    "google/gemma-3-27b-it:free"
]

print(f"--- Final Test for Key: {OPENROUTER_API_KEY[:10]}... ---")

for model in test_models:
    print(f"\nTesting model: {model}...")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}]
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("Response:", r.json()['choices'][0]['message']['content'][:100], "...")
        else:
            print("Error Response:", r.text[:200])
    except Exception as e:
        print(f"Connection Error: {e}")

print("\n--- Final Test Complete ---")
