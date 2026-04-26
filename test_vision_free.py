import requests
import json
import base64

OPENROUTER_API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

# Just a tiny black pixel as a test image
pixel = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82').decode('utf-8')

payload = {
    "model": "google/gemini-2.0-flash-exp:free",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is in this image?"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{pixel}"}}
            ]
        }
    ]
}

r = requests.post(API_URL, headers=headers, json=payload)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
