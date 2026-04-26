from app import create_app
from extensions import db
from models import User, Patient, MedicalRecord

app = create_app()

with app.app_context():
    with open('db_report.txt', 'w') as f:
        f.write("--- All Users ---\n")
        users = User.query.all()
        for u in users:
            f.write(f"ID: {u.id}, Username: {u.username}, Role: {u.role}, Email: {u.email}\n")

        f.write("\n--- All Patients ---\n")
        patients = Patient.query.all()
        for p in patients:
            f.write(f"ID: {p.id}, Name: {p.name}, UserID: {p.user_id}\n")

        f.write("\n--- All Medical Records ---\n")
        records = MedicalRecord.query.all()
        for r in records:
            f.write(f"ID: {r.id}, PatientID: {r.patient_id}, Doctor: {r.treating_doctor_name}\n")
    
    print("Report written to db_report.txt")
