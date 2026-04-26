import os
import csv
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import Patient, MedicalRecord, db, User, DoctorPatientAccess, PatientVitals
from ocr_engine import OCREngine
from datetime import datetime
import json

api = Blueprint('api', __name__)

@api.route('/register_patient', methods=['POST'])
@login_required
def register_patient():
    if current_user.role != 'HCW':
        return jsonify({"error": "Unauthorized"}), 403
        
    name = request.form.get('name')
    age = request.form.get('age')
    gender = request.form.get('gender')
    contact = request.form.get('contact')
    photo = request.files.get('photo')
    consent = request.form.get('consent') == 'true'
    
    if not consent:
        return jsonify({"error": "Patient consent is required"}), 400
        
    photo_path = None
    if photo:
        filename = secure_filename(f"patient_{datetime.now().timestamp()}.jpg")
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'patients', filename)
        photo.save(save_path)
        photo_path = os.path.join('uploads', 'patients', filename)
    
    new_patient = Patient(
        name=name,
        age=int(age) if age else None,
        gender=gender,
        contact=contact,
        face_photo=photo_path,
        has_consent=consent
    )
    db.session.add(new_patient)
    db.session.commit()
    
    # Audit Log
    from models import AuditLog
    log = AuditLog(user_id=current_user.id, action="Registered new patient", patient_id=new_patient.id)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"message": "Patient registered successfully", "patient_id": new_patient.id})

@api.route('/upload_record', methods=['POST'])
@login_required
def upload_record():
    if current_user.role not in ['HCW', 'Doctor', 'Patient']:
        return jsonify({"error": "Unauthorized"}), 403
        
    if current_user.role == 'Patient':
        # Default to the 'Self' patient, but allow selecting a family member
        requested_patient_id = request.form.get('patient_id')
        if requested_patient_id:
            patient = Patient.query.filter_by(id=requested_patient_id, user_id=current_user.id).first()
        else:
            patient = Patient.query.filter_by(user_id=current_user.id, relationship='Self').first()
            
        if not patient:
            return jsonify({"error": "Patient profile not found"}), 404
        patient_id = patient.id
    else:
        patient_id = request.form.get('patient_id')
    document = request.files.get('document')
    record_type = request.form.get('record_type', 'Prescription')
    
    doctor_notes = request.form.get('doctor_notes')
    hospital_name = request.form.get('hospital_name')
    treating_doctor_name = request.form.get('treating_doctor_name')
    
    if not document:
        return jsonify({"error": "No document uploaded"}), 400
        
    filename = secure_filename(f"record_{datetime.now().timestamp()}.jpg")
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'records', filename)
    document.save(save_path)
    
    # Process AI Verification & Data Extraction
    visit_date = datetime.utcnow()
    try:
        ai_result = OCREngine.analyze_document_ai(save_path)
        
        if not ai_result.get('is_valid', False):
            # Delete the invalid file
            if os.path.exists(save_path):
                os.remove(save_path)
            return jsonify({"error": ai_result.get('error', "Invalid medical document. Please upload a legitimate prescription or lab report.")}), 400
            
        # Parse official consultation date from AI
        extracted_date_str = ai_result.get('extracted_date', 'N/A')
        if extracted_date_str != 'N/A':
            try:
                visit_date = datetime.strptime(extracted_date_str, '%Y-%m-%d')
            except:
                pass # Keep current date if parsing fails
        
        # Use AI extracted metadata as fallback
        if not hospital_name or hospital_name.strip() == '':
            hospital_name = ai_result.get('hospital_name', 'N/A')
        if not treating_doctor_name or treating_doctor_name.strip() == '':
            treating_doctor_name = ai_result.get('doctor_name', 'N/A')
            
        structured_data = {
            "symptoms": ai_result.get('symptoms', []),
            "medications": ai_result.get('medications', []),
            "summarization": ai_result.get('summarization', ''),
            "key_points": ai_result.get('key_points', [])
        }
    except Exception as e:
        print(f"AI Processing Error: {e}")
        return jsonify({"error": "AI verification service error. Please try again."}), 500
    
    new_record = MedicalRecord(
        patient_id=patient_id,
        hcw_id=current_user.id,
        visit_date=visit_date,
        raw_ocr_text=ai_result.get('summarization', '') or ai_result.get('summary', ''),
        structured_data=structured_data,
        document_image=f"static/uploads/records/{filename}",
        record_type=record_type,
        hospital_name=hospital_name,
        treating_doctor_name=treating_doctor_name,
        doctor_notes=doctor_notes
    )
    db.session.add(new_record)
    
    # Audit Log
    from models import AuditLog
    log = AuditLog(user_id=current_user.id, action=f"Uploaded {record_type} record", patient_id=patient_id)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        "message": "Record uploaded and digitized",
        "structured_data": structured_data,
        "record_type": record_type
    })

@api.route('/patients', methods=['GET'])
@login_required
def get_patients():
    patients = Patient.query.all()
    return jsonify([{
        "id": p.id,
        "name": p.name,
        "age": p.age,
        "gender": p.gender
    } for p in patients])

@api.route('/chatbot', methods=['POST'])
@login_required
def chatbot():
    from flask import session
    data = request.json
    message = data.get('message', '')
    # Priority: 1. Request data, 2. Session, 3. Default English
    lang_code = data.get('language') or session.get('selected_language', 'en')
    
    lang_names = {
        'en': 'English',
        'te': 'Telugu (తెలుగు)',
        'hi': 'Hindi (हिन्दी)',
        'ta': 'Tamil (தமிழ்)'
    }
    target_lang = lang_names.get(lang_code, 'English')
    
    if not message:
        return jsonify({"response": "Please say something!"})

    # OpenRouter Configuration
    OPENROUTER_API_KEY = "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"
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://meddigit.ai", 
        "X-Title": "MedDigit"
    }
    
    # List of models to try (Prioritizing VERIFIED free models for this specific key)
    models = [
        "arcee-ai/trinity-large-preview:free",
        "google/gemma-3-27b-it:free",
        "nvidia/nemotron-nano-12b-v2-vl:free"
    ]

    import requests

    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": f"You are MedDigit, a highly specialized medical assistant. Your sole purpose is to assist with medical records, health questions, symptoms, and hospital logistics. You MUST respond ONLY in {target_lang}. If the target language is not English, translate your medical knowledge accurately but keep the tone professional. You MUST STRICTLY REFUSE to answer any questions unrelated to medicine or health (e.g., coding, sports, general knowledge, creative writing). If a user asks a non-medical question, politely reply in {target_lang}: 'I am designed to assist only with medical and health-related inquiries.'"},
                {"role": "user", "content": message}
            ]
        }
        
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                ai_data = response.json()
                if 'choices' in ai_data and len(ai_data['choices']) > 0:
                    ai_response = ai_data['choices'][0]['message']['content']
                    return jsonify({"response": ai_response})
            elif response.status_code == 429:
                print(f"Rate limit on {model}, trying next...")
                continue # Try next model
            else:
                print(f"Error on {model}: {response.status_code}")
                print(f"Response: {response.text}")
                continue # Try next model
                
        except Exception as e:
            print(f"Connection error on {model}: {e}")
            continue

    # If all models fail
    return jsonify({"response": "All my AI brains are currently busy or offline. Please try again in a minute."})

@api.route('/patient/<int:id>/history', methods=['GET'])
@login_required
def get_patient_history(id):
    patient = Patient.query.get_or_404(id)
    records = MedicalRecord.query.filter_by(patient_id=id).order_by(MedicalRecord.visit_date.desc()).all()
    
    # Audit Log for access
    from models import AuditLog
    log = AuditLog(user_id=current_user.id, action="Viewed patient history", patient_id=id)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        "patient": {
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "contact": patient.contact,
            "photo": patient.face_photo
        },
        "records": [{
            "id": r.id,
            "visit_date": r.visit_date.strftime('%Y-%m-%d'),
            "structured_data": r.structured_data,
            "doctor_notes": r.doctor_notes,
            "hospital_name": r.hospital_name,
            "treating_doctor_name": r.treating_doctor_name,
            "record_type": r.record_type,
            "image": r.document_image
        } for r in records]
    })

@api.route('/my_records', methods=['GET'])
@login_required
def get_my_records():
    # Find patient associated with this user
    requested_patient_id = request.args.get('patient_id')
    if requested_patient_id:
        patient = Patient.query.filter_by(id=requested_patient_id, user_id=current_user.id).first()
    else:
        patient = Patient.query.filter_by(user_id=current_user.id, relationship='Self').first()
        
    if not patient:
        return jsonify({"error": "Patient profile not found"}), 404
        
    records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.visit_date.desc()).all()
    
    # Audit Log
    from models import AuditLog
    log = AuditLog(user_id=current_user.id, action="Patient viewed their own records", patient_id=patient.id)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        "patient": {
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "contact": patient.contact
        },
        "records": [{
            "id": r.id,
            "visit_date": r.visit_date.strftime('%Y-%m-%d'),
            "structured_data": r.structured_data,
            "doctor_notes": r.doctor_notes,
            "hospital_name": r.hospital_name,
            "treating_doctor_name": r.treating_doctor_name,
            "record_type": r.record_type,
            "image": r.document_image
        } for r in records]
    })

@api.route('/summarize_record/<int:record_id>', methods=['POST'])
@login_required
def summarize_record(record_id):
    from flask import session
    from models import MedicalRecord, Patient, db
    from ocr_engine import OCREngine
    from datetime import datetime
    
    lang_code = session.get('selected_language', 'en')
    lang_names = {'en': 'English', 'te': 'Telugu', 'hi': 'Hindi', 'ta': 'Tamil'}
    target_lang = lang_names.get(lang_code, 'English')
    
    record = MedicalRecord.query.get_or_404(record_id)
    
    # Check if the user is authorized to view this record
    if current_user.role == 'Patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient or record.patient_id != patient.id:
            return jsonify({"error": "Unauthorized"}), 403

    # Absolute path to the image
    image_path = os.path.join(current_app.root_path, record.document_image)
    if not os.path.exists(image_path):
        # Handle cases where path might be relative to static or missing static
        if 'static' not in record.document_image:
             image_path = os.path.join(current_app.root_path, 'static', record.document_image)
        else:
             image_path = os.path.join(os.getcwd(), record.document_image)

    try:
        from ocr_engine import OCREngine
        ai_result = OCREngine.analyze_document_ai(image_path, language=target_lang)
        
        if not ai_result.get('is_valid', False):
            return jsonify({"error": ai_result.get('error', "AI could not recognize this as a medical document.")}), 400
            
        # Update record with new AI data
        extracted_date_str = ai_result.get('extracted_date', 'N/A')
        if extracted_date_str != 'N/A':
            try:
                record.visit_date = datetime.strptime(extracted_date_str, '%Y-%m-%d')
            except:
                pass
        
        # Merge or update metadata
        record.hospital_name = ai_result.get('hospital_name', record.hospital_name)
        record.treating_doctor_name = ai_result.get('doctor_name', record.treating_doctor_name)
        
        record.structured_data = {
            "symptoms": ai_result.get('symptoms', []),
            "medications": ai_result.get('medications', []),
            "summarization": ai_result.get('summarization', ''),
            "key_points": ai_result.get('key_points', [])
        }
        record.raw_ocr_text = ai_result.get('summarization', '')
        
        db.session.commit()
        
        return jsonify({
            "message": "Record re-summarized successfully",
            "summarization": record.structured_data['summarization'],
            "key_points": record.structured_data['key_points'],
            "visit_date": record.visit_date.strftime('%Y-%m-%d'),
            "record_type": record.record_type
        })
    except Exception as e:
        print(f"Manual Summarization Error: {e}")
        return jsonify({"error": "Failed to re-summarize record."}), 500

@api.route('/search_doctors', methods=['POST'])
@login_required
def search_doctors():
    query = request.json.get('query', '')
    if len(query) < 2:
        return jsonify([])
        
    # Search by name or ID
    doctors = User.query.filter(
        User.role == 'Doctor',
        (User.full_name.ilike(f'%{query}%')) | (User.id.cast(db.String).ilike(f'%{query}%'))
    ).all()
    
    return jsonify([{
        "id": d.id,
        "name": d.full_name,
        "specialty": "General Physician" # Placeholder for now
    } for d in doctors])

@api.route('/grant_access', methods=['POST'])
@login_required
def grant_access():
    if current_user.role != 'Patient':
        return jsonify({"error": "Only patients can grant access"}), 403
        
    doctor_id = request.json.get('doctor_id')
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    if not patient:
        return jsonify({"error": "Patient profile not found"}), 404
        
    # Check if access already exists
    existing = DoctorPatientAccess.query.filter_by(doctor_id=doctor_id, patient_id=patient.id).first()
    if existing:
        return jsonify({"message": "Access already granted"})
        
    new_access = DoctorPatientAccess(doctor_id=doctor_id, patient_id=patient.id)
    db.session.add(new_access)
    
    # Audit Log
    from models import AuditLog
    log = AuditLog(user_id=current_user.id, action=f"Granted access to Doctor ID: {doctor_id}", patient_id=patient.id)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"message": "Access granted successfully"})

@api.route('/revoke_access', methods=['POST'])
@login_required
def revoke_access():
    if current_user.role != 'Patient':
        return jsonify({"error": "Only patients can revoke access"}), 403
        
    doctor_id = request.json.get('doctor_id')
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    access = DoctorPatientAccess.query.filter_by(doctor_id=doctor_id, patient_id=patient.id).first()
    if access:
        db.session.delete(access)
        
        # Audit Log
        from models import AuditLog
        log = AuditLog(user_id=current_user.id, action=f"Revoked access from Doctor ID: {doctor_id}", patient_id=patient.id)
        db.session.add(log)
        db.session.commit()
        
    return jsonify({"message": "Access revoked successfully"})

@api.route('/authorized_doctors', methods=['GET'])
@login_required
def get_authorized_doctors():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify([])
        
    access_list = DoctorPatientAccess.query.filter_by(patient_id=patient.id).all()
    return jsonify([{
        "id": a.doctor.id,
        "name": a.doctor.full_name,
        "granted_at": a.granted_at.strftime('%Y-%m-%d %H:%M')
    } for a in access_list])

@api.route('/update_health_card', methods=['POST'])
@login_required
def update_health_card():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({"error": "Patient profile not found"}), 404
        
    data = request.json
    patient.health_card_number = data.get('card_number')
    patient.health_card_type = data.get('card_type')
    db.session.commit()
    
    return jsonify({"message": "Health card details updated successfully"})

@api.route('/add_family_member', methods=['POST'])
@login_required
def add_family_member():
    if current_user.role != 'Patient':
        return jsonify({"error": "Only patients can add family members"}), 403
        
    data = request.json
    name = data.get('name')
    relationship = data.get('relationship')
    age = data.get('age')
    gender = data.get('gender')
    contact = data.get('contact')
    
    if not name or not relationship:
        return jsonify({"error": "Name and relationship are required"}), 400
        
    new_member = Patient(
        name=name,
        relationship=relationship,
        age=int(age) if age else None,
        gender=gender,
        contact=contact,
        user_id=current_user.id,
        has_consent=True # Assume consent for family members added by the user
    )
    db.session.add(new_member)
    db.session.commit()
    
    return jsonify({"message": f"Family member '{name}' added successfully", "patient_id": new_member.id})

@api.route('/list_family', methods=['GET'])
@login_required
def list_family():
    members = Patient.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        "id": m.id,
        "name": m.name,
        "relationship": m.relationship,
        "age": m.age,
        "gender": m.gender
    } for m in members])


@api.route('/suggest_schemes', methods=['GET'])
@login_required
def suggest_schemes():
    from flask import session
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({"error": "Patient profile not found"}), 404
        
    lang_code = session.get('selected_language', 'en')
    lang_names = {'en': 'English', 'te': 'Telugu', 'hi': 'Hindi', 'ta': 'Tamil'}
    target_lang = lang_names.get(lang_code, 'English')
    
    records = MedicalRecord.query.filter_by(patient_id=patient.id).all()
    
    # Compile a summary of health data for the AI
    health_summary = []
    for r in records:
        record_info = f"Type: {r.record_type}, Date: {r.visit_date.strftime('%Y-%m-%d')}"
        if r.structured_data:
            symptoms = ", ".join(r.structured_data.get('symptoms', []))
            meds = ", ".join(r.structured_data.get('medications', []))
            summary = r.structured_data.get('summarization', '')
            health_summary.append(f"{record_info} | Symptoms: {symptoms} | Meds: {meds} | Summary: {summary}")
        else:
            health_summary.append(f"{record_info} | Content: {r.raw_ocr_text}")
            
    prompt_context = "\n".join(health_summary)
    card_info = f"Health Card Type: {patient.health_card_type}, Number: {patient.health_card_number}" if patient.health_card_type else "No existing health card linked."
    
    # AI Request for schemes
    OPENROUTER_API_KEY = "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"
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "arcee-ai/trinity-large-preview:free",
        "messages": [
            {"role": "system", "content": f"You are a Government Health Scheme Expert. Based on the patient's medical history and current health card details, identify 3-4 relevant Indian Government health schemes. \n\nCRITICAL: You MUST use ONLY official verified government portal URLs. If you are unsure, use the main ministry portal (mohfw.gov.in). \n\nLANGUAGE RULE: You MUST provide the response (title, relevance, benefits, how_to_apply) in {target_lang}.\n\nVerified Link Reference:\n- Ayushman Bharat (PM-JAY): https://pmjay.gov.in/\n- PMSSY (Pradhan Mantri Swasthya Suraksha Yojana): https://pmssy-mohfw.nic.in/\n- Arogyasri (Telangana): https://aarogyasri.telangana.gov.in/\n- Arogyasri (Andhra Pradesh): https://www.ysraarogyasri.ap.gov.in/\n- CGHS (Central Govt Health Scheme): https://cghs.gov.in/\n- National Health Mission (NHM): https://nhm.gov.in/\n\nProvide the response in valid JSON format as a list of objects, each with 'title', 'relevance', 'benefits', 'how_to_apply', and 'portal_url' (the official government website link for the scheme). Do not include any text outside the JSON block."},
            {"role": "user", "content": f"Patient Medical History Summary:\n{prompt_context}\n\nPatient Card Info:\n{card_info}"}
        ],
        "response_format": { "type": "json_object" }
    }
    
    import requests
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            # Sometimes AI wraps in markdown blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            schemes_data = json.loads(content)
            # Ensure it handles both {"schemes": [...]} and [...]
            if isinstance(schemes_data, dict) and "schemes" in schemes_data:
                return jsonify({"schemes": schemes_data["schemes"]})
            return jsonify({"schemes": schemes_data})
        else:
            print(f"AI Scheme Error: {response.status_code} - {response.text}")
            return jsonify({"error": "Could not generate scheme suggestions at this time."}), 500
    except Exception as e:
        print(f"Scheme generation exception: {e}")
        return jsonify({"error": "Processing error"}), 500
@api.route('/suggest_doctors', methods=['GET'])
@login_required
def suggest_doctors():
    from flask import session
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({"error": "Patient profile not found"}), 404
        
    lang_code = session.get('selected_language', 'en')
    lang_names = {'en': 'English', 'te': 'Telugu', 'hi': 'Hindi', 'ta': 'Tamil'}
    target_lang = lang_names.get(lang_code, 'English')
    
    records = MedicalRecord.query.filter_by(patient_id=patient.id).all()
    
    # Compile health context
    health_summary = []
    for r in records:
        record_info = f"Type: {r.record_type}, Date: {r.visit_date.strftime('%Y-%m-%d')}"
        if r.structured_data:
            symptoms = ", ".join(r.structured_data.get('symptoms', []))
            summary = r.structured_data.get('summarization', '')
            health_summary.append(f"{record_info} | Symptoms: {symptoms} | Summary: {summary}")
        else:
            health_summary.append(f"{record_info} | Content: {r.raw_ocr_text[:200]}")
            
    prompt_context = "\n".join(health_summary)
    
    # Get available doctors
    doctors = User.query.filter_by(role='Doctor').all()
    doctor_list = []
    for d in doctors:
        doctor_list.append({
            "id": d.id,
            "name": d.full_name,
            "specialty": d.specialty or "General Physician",
            "experience": d.years_of_experience or 0,
            "research_areas": d.research_areas or "N/A"
        })
    
    if not doctor_list:
        return jsonify({"message": "No doctors available in the network yet."})

    # AI Request for recommendations
    OPENROUTER_API_KEY = "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"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    import json
    payload = {
        "model": "arcee-ai/trinity-large-preview:free",
        "messages": [
            {"role": "system", "content": f"You are a Medical Matchmaking AI. Based on the patient's medical history and the list of available doctors, recommend 2-3 specific doctors who best match the patient's needs. Explain why each doctor is a good fit.\n\nLANGUAGE RULE: You MUST provide the response (doctor_name, specialty, recommendation_reason) in {target_lang}.\n\nProvide response in valid JSON format as a list of objects: {{'doctor_id', 'doctor_name', 'specialty', 'recommendation_reason', 'match_score' (0-100)}}. Do not include text outside JSON."},
            {"role": "user", "content": f"Patient Health History:\n{prompt_context}\n\nAvailable Doctors:\n{json.dumps(doctor_list)}"}
        ],
        "response_format": { "type": "json_object" }
    }
    
    try:
        import requests
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        ai_data = response.json()
        
        # Check if the AI returned the expected structure
        content = ai_data['choices'][0]['message']['content']
        recommendations = json.loads(content)
        
        # Handle different possible JSON structures from AI
        if isinstance(recommendations, dict) and 'recommendations' in recommendations:
            recommendations = recommendations['recommendations']
        elif isinstance(recommendations, dict) and 'doctors' in recommendations:
            recommendations = recommendations['doctors']
            
        return jsonify({"recommendations": recommendations})
        
    except Exception as e:
        print(f"AI Suggestion Error: {e}")
        return jsonify({"error": "Failed to generate AI recommendations"}), 500

@api.route('/symptom_checker', methods=['POST'])
@login_required
def symptom_checker():
    from flask import session
    data = request.json
    symptoms = data.get('symptoms', [])
    lang_code = session.get('selected_language', 'en')
    lang_names = {'en': 'English', 'te': 'Telugu', 'hi': 'Hindi', 'ta': 'Tamil'}
    target_lang = lang_names.get(lang_code, 'English')

    if not symptoms:
        return jsonify({"error": "No symptoms selected"}), 400

    symptoms_text = ", ".join(symptoms)
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY = "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"
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "arcee-ai/trinity-large-preview:free",
        "messages": [
            {"role": "system", "content": f"You are a medical symptom analyzer AI. Based on the selected symptoms, provide a structured response including possible conditions, health guidance, and a mandatory disclaimer. \n\nCRITICAL: You MUST respond ONLY in {target_lang}. \n\nProvide the response in valid JSON format with the following keys: 'possible_conditions' (list of strings), 'health_guidance' (list of strings), and 'disclaimer' (string). The disclaimer MUST state that this is NOT a medical diagnosis and the user should consult a doctor. Do not include any text outside the JSON block."},
            {"role": "user", "content": f"Symptoms: {symptoms_text}"}
        ],
        "response_format": { "type": "json_object" }
    }
    
    try:
        import requests
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Clean up markdown if necessary
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            analysis_data = json.loads(content)
            return jsonify(analysis_data)
        else:
            print(f"Symptom Checker Error: {response.status_code} - {response.text}")
            return jsonify({"error": "AI service error. Please try again later."}), 500
    except Exception as e:
        print(f"Symptom Checker exception: {e}")
        return jsonify({"error": "Failed to analyze symptoms"}), 500

@api.route('/save_vitals', methods=['POST'])
@login_required
def save_vitals():
    data = request.json
    patient_id = data.get('patient_id') # If empty, it's for current_user's self profile
    
    if not patient_id:
        patient = Patient.query.filter_by(user_id=current_user.id, relationship='Self').first()
    else:
        patient = Patient.query.get(patient_id)
        # Check permission: HCW can save for any, Patient can save for self/family
        if current_user.role == 'Patient':
            # Check if this patient belongs to current user
            if patient.user_id != current_user.id:
                return jsonify({"error": "Unauthorized"}), 403
    
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    vitals = PatientVitals(
        patient_id=patient.id,
        heart_rate=data.get('heart_rate'),
        blood_pressure_sys=data.get('blood_pressure_sys'),
        blood_pressure_dia=data.get('blood_pressure_dia'),
        temperature=data.get('temperature'),
        spo2=data.get('spo2'),
        notes=data.get('notes'),
        recorded_at=datetime.utcnow()
    )
    
    db.session.add(vitals)
    db.session.commit()
    return jsonify({"message": "Vitals recorded successfully"})

@api.route('/get_vitals', methods=['GET'])
@login_required
def get_vitals():
    patient_id = request.args.get('patient_id')
    
    if not patient_id:
        patient = Patient.query.filter_by(user_id=current_user.id, relationship='Self').first()
    else:
        patient = Patient.query.get(patient_id)
    
    if not patient:
        return jsonify({"error": "Patient not found"}), 404
        
    # Permission check
    if current_user.role == 'Patient':
        if patient.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
    elif current_user.role == 'Doctor':
        # Check if doctor has access
        access = DoctorPatientAccess.query.filter_by(doctor_id=current_user.id, patient_id=patient.id).first()
        if not access:
            return jsonify({"error": "Access denied"}), 403
            
    vitals_data = PatientVitals.query.filter_by(patient_id=patient.id).order_by(PatientVitals.recorded_at.asc()).all()
    
    results = []
    for v in vitals_data:
        results.append({
            "id": v.id,
            "recorded_at": v.recorded_at.strftime('%Y-%m-%d %H:%M'),
            "heart_rate": v.heart_rate,
            "blood_pressure_sys": v.blood_pressure_sys,
            "blood_pressure_dia": v.blood_pressure_dia,
            "temperature": v.temperature,
            "spo2": v.spo2,
            "notes": v.notes
        })
        
    return jsonify({"vitals": results})

@api.route('/disease_trends', methods=['GET'])
@login_required
def get_disease_trends():
    if current_user.role != 'Admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    disease_filter = request.args.get('disease')
    region_filter = request.args.get('region')
    
    csv_path = os.path.join(current_app.root_path, 'static', 'data', 'disease_trends.csv')
    if not os.path.exists(csv_path):
        return jsonify({"error": "Data file not found"}), 404
        
    trends = []
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if disease_filter and disease_filter != 'All' and row['disease'] != disease_filter:
                    continue
                if region_filter and region_filter != 'All' and row['region'] != region_filter:
                    continue
                trends.append({
                    "date": row['date'],
                    "disease": row['disease'],
                    "region": row['region'],
                    "cases": int(row['cases'])
                })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    return jsonify({"trends": trends})

@api.route('/admin/users', methods=['GET'])
@login_required
def get_all_users():
    if current_user.role != 'Admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    users = User.query.all()
    results = []
    for u in users:
        results.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "verified": u.email_verified
        })
    return jsonify({"users": results})

@api.route('/analyze_skin', methods=['POST'])
@login_required
def analyze_skin():
    if current_user.role not in ['HCW', 'Doctor', 'Patient']:
        return jsonify({"error": "Unauthorized"}), 403
        
    skin_image = request.files.get('image')
    if not skin_image:
        return jsonify({"error": "No image uploaded"}), 400
        
    filename = secure_filename(f"skin_{datetime.now().timestamp()}.jpg")
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'patients', filename)
    skin_image.save(save_path)
    
    # Process AI Verification
    try:
        ai_result = OCREngine.analyze_skin_disease(save_path)
        
        # Clean up the file as it's not a medical record, just a temporary scan
        if os.path.exists(save_path):
            os.remove(save_path)
            
        return jsonify(ai_result)
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        return jsonify({"error": str(e)}), 500

@api.route('/admin/delete_user/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if current_user.role != 'Admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if user.id == current_user.id:
        return jsonify({"error": "Cannot delete yourself"}), 400

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api.route('/admin/update_user', methods=['POST'])
@login_required
def update_user():
    if current_user.role != 'Admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    user_id = data.get('id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    if 'role' in data:
        user.role = data['role']
    if 'verified' in data:
        user.email_verified = data['verified']
        
    try:
        db.session.commit()
        return jsonify({"message": "User updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api.route('/admin/hospitals', methods=['GET'])
@login_required
def get_hospitals():
    if current_user.role != 'Admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    records = MedicalRecord.query.with_entities(MedicalRecord.hospital_name, db.func.count(MedicalRecord.id)).group_by(MedicalRecord.hospital_name).all()
    
    results = []
    for hospital_name, count in records:
        if hospital_name:
            results.append({
                "name": hospital_name,
                "record_count": count
            })
    return jsonify({"hospitals": results})

@api.route('/admin/stats', methods=['GET'])
@login_required
def get_admin_stats():
    if current_user.role != 'Admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    total_users = User.query.count()
    total_patients = Patient.query.count()
    total_doctors = User.query.filter_by(role='Doctor').count()
    total_records = MedicalRecord.query.count()
    
    return jsonify({
        "total_users": total_users,
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_records": total_records
    })
