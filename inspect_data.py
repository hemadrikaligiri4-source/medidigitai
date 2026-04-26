from app import create_app
from extensions import db
from models import User, Patient, MedicalRecord

app = create_app()

with app.app_context():
    print("--- User Info ---")
    user = User.query.filter_by(username='hemadri').first()
    if user:
        print(f"ID: {user.id}, Username: {user.username}, Role: {user.role}, Email: {user.email}")
        
        print("\n--- Patient Info ---")
        patient = Patient.query.filter_by(user_id=user.id).first()
        if patient:
            print(f"Patient ID: {patient.id}, Name: {patient.name}")
            
            print("\n--- Medical Records for this Patient ---")
            records = MedicalRecord.query.filter_by(patient_id=patient.id).all()
            if records:
                print(f"Found {len(records)} records:")
                for r in records:
                    # Using r.doctor_notes or raw_ocr_text since summary wasn't in the model I saw
                    print(f"- ID: {r.id}, Date: {r.visit_date}, Type: {r.record_type}")
            else:
                print("No medical records found for this specific patient.")
        else:
            print("No patient record linked to this user.")
    else:
        print("User 'hemadri' not found in database.")

    print("\n--- System-Wide Stats ---")
    print(f"Total Users: {User.query.count()}")
    print(f"Total Patients: {Patient.query.count()}")
    print(f"Total Medical Records: {MedicalRecord.query.count()}")
    
    if MedicalRecord.query.count() > 0:
        print("\nRecent 5 Medical Records in System:")
        for r in MedicalRecord.query.order_by(MedicalRecord.id.desc()).limit(5).all():
            print(f"- ID: {r.id}, PatientID: {r.patient_id}, Doctor: {r.treating_doctor_name}")
