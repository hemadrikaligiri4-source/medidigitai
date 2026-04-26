from app import create_app
from extensions import db
from models import User, Patient, MedicalRecord
import json

app = create_app()

with app.app_context():
    user = User.query.filter_by(username='hemadri').first()
    if not user:
        print("User 'hemadri' not found.")
    else:
        print(f"Simulating for User: {user.username} (ID: {user.id})")
        patient = Patient.query.filter_by(user_id=user.id).first()
        if not patient:
            print("Patient profile not found for this user.")
        else:
            print(f"Associated Patient: {patient.name} (ID: {patient.id})")
            records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.visit_date.desc()).all()
            print(f"Found {len(records)} records.")
            
            output_records = []
            for r in records:
                try:
                    rec_dict = {
                        "id": r.id,
                        "visit_date": r.visit_date.strftime('%Y-%m-%d') if r.visit_date else 'N/A',
                        "structured_data": r.structured_data,
                        "doctor_notes": r.doctor_notes,
                        "hospital_name": r.hospital_name,
                        "treating_doctor_name": r.treating_doctor_name,
                        "record_type": r.record_type,
                        "image": r.document_image
                    }
                    output_records.append(rec_dict)
                    print(f"Successfully processed Record ID: {r.id}")
                except Exception as e:
                    print(f"Error processing Record ID {r.id}: {e}")
            
            # Try to serialize to JSON to see if that fails
            try:
                json_data = json.dumps({"records": output_records})
                print("JSON Serialization SUCCESSful.")
                # print(json_data[:200] + "...")
            except Exception as e:
                print(f"JSON Serialization FAILED: {e}")
