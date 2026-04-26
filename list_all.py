from app import create_app
from extensions import db
from models import User, Patient, MedicalRecord

app = create_app()

with app.app_context():
    print("--- All Users ---")
    users = User.query.all()
    for u in users:
        print(f"ID: {u.id}, Username: {u.username}, Role: {u.role}")

    print("\n--- All Patients ---")
    patients = Patient.query.all()
    for p in patients:
        print(f"ID: {p.id}, Name: {p.name}, UserID: {p.user_id}")

    print("\n--- Medical Records ---")
    print(f"Total Medical Records: {MedicalRecord.query.count()}")
