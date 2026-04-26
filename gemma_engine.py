"""
gemma_engine.py — Gemma LLM Integration for MedDigit AI
=========================================================
Dedicated Gemma/Gemini AI module using Google AI Studio (free tier).
This is a NEW feature alongside the existing OpenRouter chatbot.

The existing /api/chatbot endpoint is NOT changed.
This adds a new /api/gemma_chat endpoint via api.py.

Requires environment variable:
    GEMINI_API_KEY   from https://aistudio.google.com/apikey (free)

Model: gemini-2.0-flash (Google's latest fast model, free tier)
If API key is missing, returns a helpful placeholder response.
"""

import os


# ── Gemma / Gemini Client ─────────────────────────────────────────────────────
def _get_client():
    """Returns a configured Gemini client, or None if key is missing."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai
    except Exception as e:
        print(f"⚠️  Gemma engine init failed: {e}")
        return None


# ── Medical Analysis ──────────────────────────────────────────────────────────
def gemma_medical_analysis(user_message: str, language: str = "English") -> dict:
    """
    Sends a medical query to Gemma (via Google AI Studio) and returns
    a structured response.

    Args:
        user_message: The patient's query or symptom description
        language:     Target language for the response (English, Telugu, Hindi, Tamil)

    Returns:
        dict with keys: 'response', 'model', 'success'
    """
    genai = _get_client()

    if genai is None:
        return {
            "response": (
                "🔑 Gemma AI is not configured yet. "
                "Please set GEMINI_API_KEY in your .env file "
                "(get a free key at https://aistudio.google.com/apikey)."
            ),
            "model": "not_configured",
            "success": False
        }

    system_prompt = (
        f"You are MedDigit Gemma — a specialized medical AI assistant. "
        f"Your role is to help with medical records, symptoms, health questions, "
        f"and hospital logistics. "
        f"CRITICAL: Respond ONLY in {language}. "
        f"CRITICAL: Refuse any non-medical questions politely. "
        f"Always add a disclaimer that your response is not a substitute for "
        f"professional medical advice."
    )

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system_prompt
        )
        response = model.generate_content(user_message)
        return {
            "response": response.text,
            "model": "gemini-2.0-flash (Gemma)",
            "success": True
        }
    except Exception as e:
        print(f"⚠️  Gemma generation error: {e}")
        return {
            "response": "Gemma AI is temporarily unavailable. Please try again.",
            "model": "gemini-2.0-flash",
            "success": False,
            "error": str(e)
        }


# ── OCR Document Analysis ─────────────────────────────────────────────────────
def gemma_analyze_document(image_path: str) -> dict:
    """
    Uses Gemma's vision capability to analyze a medical document image.
    Returns structured extraction: symptoms, medications, summary.

    Args:
        image_path: Absolute path to the uploaded medical document image

    Returns:
        dict with extracted medical data, or error info
    """
    genai = _get_client()
    if genai is None:
        return {"success": False, "error": "GEMINI_API_KEY not configured"}

    try:
        import PIL.Image
        image = PIL.Image.open(image_path)

        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = (
            "Analyze this medical document image. Extract and return as JSON: "
            "{ \"symptoms\": [], \"medications\": [], \"summary\": \"\", "
            "\"doctor_name\": \"\", \"hospital_name\": \"\", \"date\": \"\" }. "
            "Only return valid JSON, no extra text."
        )
        response = model.generate_content([prompt, image])
        return {
            "success": True,
            "raw_response": response.text,
            "model": "gemini-2.0-flash-vision"
        }
    except Exception as e:
        print(f"⚠️  Gemma document analysis error: {e}")
        return {"success": False, "error": str(e)}
