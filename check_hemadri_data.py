from app import create_app
from extensions import db
from models import User, Patient, MedicalRecord
import json

app = create_app()

with app.app_context():
    # Find user 'hemadri'
    user = User.query.filter_by(username='hemadri').first()
    if not user:
        print("User 'hemadri' not found.")
    else:
        print(f"Checking data for user: {user.username} (ID: {user.id})")
        # Find patient record
        patient = Patient.query.filter_by(user_id=user.id).first()
        if not patient:
            print("No patient profile found for this user.")
        else:
            print(f"Found Patient Profile: {patient.name} (ID: {patient.id})")
            # Get records
            records = MedicalRecord.query.filter_by(patient_id=patient.id).all()
            print(f"Total Medical Records found: {len(records)}")
            
            for r in records:
                print(f"--- Record ID: {r.id} ---")
                print(f"  Type: {r.record_type}")
                print(f"  Date: {r.visit_date}")
                print(f"  Hospital: {r.hospital_name}")
                print(f"  Doctor: {r.treating_doctor_name}")
                print(f"  Structured Data (first 100 chars): {str(r.structured_data)[:100]}...")
                
            # Verify the API response format
            response_records = [{
                "id": r.id,
                "visit_date": r.visit_date.strftime('%Y-%m-%d') if r.visit_date else 'N/A',
                "structured_data": r.structured_data,
                "doctor_notes": r.doctor_notes,
                "hospital_name": r.hospital_name,
                "treating_doctor_name": r.treating_doctor_name,
                "record_type": r.record_type,
                "image": r.document_image
            } for r in records]
            
            print("\nAPI Response Simulation Clean Check:")
            try:
                json_str = json.dumps(response_records)
                print("✓ JSON Serialization successful.")
            except Exception as e:
                print(f"✗ JSON Serialization failed: {e}")
