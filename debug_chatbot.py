import requests
import json

OPENROUTER_API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://meddigit.ai",
    "X-Title": "MedDigit"
}

# Extensive list of models to find a working one
models_to_test = [
    "deepseek/deepseek-chat:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "meta-llama/llama-3-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "openchat/openchat-7b:free",
    "gryphe/mythomist-7b:free",
    "google/gemini-flash-1.5-8b",
    "anthropic/claude-3-haiku",
    "openai/gpt-3.5-turbo"
]

results = []

for model in models_to_test:
    print(f"Testing model: {model}...")
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "hi"}
        ]
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        status = response.status_code
        text = response.text
        print(f"  Status: {status}")
        results.append({
            "model": model,
            "status": status,
            "response": text[:200]
        })
        if status == 200:
            print(f"  SUCCESS!")
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        results.append({
            "model": model,
            "status": "EXCEPTION",
            "error": str(e)
        })
    print("-" * 20)

with open('chatbot_test_results.json', 'w') as f:
    json.dump(results, f, indent=4)
