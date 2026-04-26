import cv2
import pytesseract
import numpy as np
from PIL import Image
import re
import base64
import requests
import json
import os

class OCREngine:
    @staticmethod
    def preprocess_image(image_path):
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
        
        return denoised

    @staticmethod
    def extract_text(image_path):
        # Preprocess
        processed_img = OCREngine.preprocess_image(image_path)
        if processed_img is None:
            return ""
            
        # Extract text using Tesseract
        text = pytesseract.image_to_string(processed_img)
        
        return text

    @staticmethod
    def analyze_document_ai(image_path, language="English"):
        """Uses OpenRouter Vision AI to verify and extract data from medical docs."""
        OPENROUTER_API_KEY = "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"
        API_URL = "https://openrouter.ai/api/v1/chat/completions"
        
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            return {"is_valid": False, "error": f"Could not read file: {str(e)}"}
            
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://meddigit.ai",
            "X-Title": "MedDigit AI"
        }
        
        prompt = f"""
        Analyze this medical document image with high precision. Your goal is to provide a clear, professional clinical summarization that a doctor or patient can understand instantly.
        
        CRITICAL RULES:
        1. VALIDITY: Is this a legitimate medical/health document? (Prescription, Lab, Scan, X-ray, Bill, etc.). Answer YES/NO.
        2. DATE: Extract the consultation/report date in YYYY-MM-DD format.
        3. CLINICAL SUMMARIZATION: Write a comprehensive, 2-3 sentence analysis. Clearly state WHAT this document is, the CURRENT STATUS of the patient based on it, and the MAIN CONCLUSION. 
           TRANSALTION RULE: You MUST write the 'summarization' and 'key_points' in {language}.
        4. KEY MEDICAL POINTS: Extract the top 4 most important medical takeaways (e.g., specific high/low values, diagnoses, or follow-up instructions) in {language}.
        5. METADATA: Extract Hospital, Doctor, Symptoms, and Medications. Keep proper names as they are but translate symptoms if possible to {language}.
        
        Format your response EXACTLY as a JSON object:
        {{
            "is_valid": true,
            "extracted_date": "YYYY-MM-DD",
            "hospital_name": "...",
            "doctor_name": "...",
            "symptoms": ["..."],
            "medications": ["..."],
            "summarization": "Detailed clinical analysis in {language} here...",
            "key_points": ["Point 1 in {language}", "..."]
        }}
        """
        
        models = [
            "nvidia/nemotron-nano-12b-v2-vl:free",
            "arcee-ai/trinity-large-preview:free",
            "google/gemma-3-27b-it:free"
        ]
        
        for model in models:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "response_format": { "type": "json_object" }
            }
            
            try:
                response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
                if response.status_code != 200:
                    print(f"Model {model} failed with status {response.status_code}. Trying next...")
                    continue
                    
                ai_data = response.json()
                content = ai_data['choices'][0]['message']['content']
                
                # Robust JSON parsing
                try:
                    return json.loads(content)
                except:
                    # Handle potential markdown code blocks
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        return json.loads(match.group())
                    print(f"Failed to parse JSON from {model}. Trying next...")
                    continue
            except Exception as e:
                print(f"Error with model {model}: {e}")
                continue
        else:
            return {"is_valid": False, "error": "All AI verification models failed or were unavailable."}

    @staticmethod
    def analyze_skin_disease(image_path, language="English"):
        """Uses OpenRouter Vision AI to classify skin disease with a disclaimer."""
        OPENROUTER_API_KEY = "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"
        API_URL = "https://openrouter.ai/api/v1/chat/completions"
        
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            return {"condition": "Error", "error": f"Could not read file: {str(e)}"}
            
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://meddigit.ai",
            "X-Title": "MedDigit AI"
        }
        
        prompt = f"""
        Analyze this image of a skin condition. Note: this is for informational purposes only.
        Analyze the color, texture, and shape to provide a potential classification.
        
        Respond ONLY in the following exact JSON format without additional text:
        {{
            "condition": "Name of the predicted condition (in {language})",
            "confidence": "High, Medium, or Low",
            "guidance": "2-3 short sentences of basic preventive guidance or precautions in {language}",
            "disclaimer": "This is an AI-generated analysis. It is not conclusive medical advice. Please consult a certified dermatologist for a professional clinical diagnosis."
        }}
        """
        
        models = [
            "nvidia/nemotron-nano-12b-v2-vl:free",
            "arcee-ai/trinity-large-preview:free",
            "google/gemma-3-27b-it:free"
        ]
        
        for model in models:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "response_format": { "type": "json_object" }
            }
            
            try:
                response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
                if response.status_code != 200:
                    continue
                    
                ai_data = response.json()
                content = ai_data['choices'][0]['message']['content']
                
                try:
                    return json.loads(content)
                except:
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        return json.loads(match.group())
                    continue
            except Exception as e:
                continue
        else:
            return {
                "condition": "Analysis Failed", 
                "confidence": "None",
                "guidance": "The AI model is currently unavailable or the image format is unsupported.",
                "disclaimer": "This is an AI-generated analysis. It is not conclusive medical advice. Please consult a certified dermatologist for a professional clinical diagnosis."
            }

    @staticmethod
    def structure_data(text):
        # Kept for backward compatibility or as fallback
        data = {
            "symptoms": [],
            "medications": [],
            "date": ""
        }
        
        date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
        dates = re.findall(date_pattern, text)
        if dates:
            data["date"] = dates[0]
            
        lines = text.split('\n')
        for line in lines:
            line = line.strip().lower()
            if not line: continue
            
            if any(k in line for k in ['mg', 'tablet', 'cap', 'twice', 'daily']):
                data["medications"].append(line)
            elif any(k in line for k in ['pain', 'fever', 'cough', 'cold', 'headache']):
                data["symptoms"].append(line)
                
        return data
