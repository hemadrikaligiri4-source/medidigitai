import requests
import json

KEYS = [
    "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", # From api.py
    "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", # From verify_openrouter.py
    "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"  # From test_new_key.py
]

CHATBOOT_MODELS = [
    "arcee-ai/trinity-large-preview:free",
    "qwen/qwen3-4b:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free"
]

VISION_MODELS = [
    "qwen/qwen-2.5-vl-7b-instruct:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free"
]

API_URL = "https://openrouter.ai/api/v1/chat/completions"

def test_model(api_key, model, is_vision=False):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://meddigit.ai",
        "X-Title": "MedDigit Diagnostic"
    }
    
    content = "Hello, are you working?"
    if is_vision:
        # Just text test for vision model to check availability
        content = "This is a test. Respond with 'OK'."
        
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}]
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        return response.status_code, response.text
    except Exception as e:
        return 0, str(e)

results = {}

for i, key in enumerate(KEYS):
    key_short = key[:10] + "..."
    results[key_short] = {"chatbot": {}, "vision": {}}
    print(f"\nTesting Key: {key_short}")
    
    for model in CHATBOOT_MODELS:
        status, resp = test_model(key, model)
        results[key_short]["chatbot"][model] = status
        print(f"  Chatbot {model}: {status}")
        
    for model in VISION_MODELS:
        status, resp = test_model(key, model, is_vision=True)
        results[key_short]["vision"][model] = status
        print(f"  Vision {model}: {status}")

with open("ai_verification_results.json", "w") as f:
    json.dump(results, f, indent=4)
