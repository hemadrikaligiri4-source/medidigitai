import requests
import json

# Using the new key provided by the user
OPENROUTER_API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:8080",
    "X-Title": "MedDigit Debug"
}

# Test with a lightweight model
payload = {
    "model": "google/gemini-2.0-flash-lite-preview-02-05:free",
    "messages": [
        {"role": "user", "content": "hi"}
    ]
}

print(f"Testing new API key with model: {payload['model']}")
try:
    r = requests.post(API_URL, headers=headers, json=payload, timeout=15)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    
    if r.status_code == 200:
        data = r.json()
        print("\nSuccess! Chatbot response:")
        print(data['choices'][0]['message']['content'])
    else:
        print("\nFailed with status code:", r.status_code)
except Exception as e:
    print(f"\nError: {e}")

# Now test a paid model to see if there's credit
payload_paid = {
    "model": "openai/gpt-4o-mini",
    "messages": [
        {"role": "user", "content": "hi"}
    ]
}

print(f"\nTesting new API key with paid model: {payload_paid['model']}")
try:
    r = requests.post(API_URL, headers=headers, json=payload_paid, timeout=15)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"\nError: {e}")
