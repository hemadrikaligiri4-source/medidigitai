from app import create_app
from extensions import db
from models import User, Patient, MedicalRecord, AuditLog

app = create_app()

with app.app_context():
    with open('audit_report.txt', 'w') as f:
        f.write("--- Recent Audit Logs ---\n")
        logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()
        for l in logs:
            f.write(f"ID: {l.id}, UserID: {l.user_id}, Action: {l.action}, Time: {l.timestamp}, PatientID: {l.patient_id}\n")

        f.write("\n--- Medical Record Details (Patient 3) ---\n")
        records = MedicalRecord.query.filter_by(patient_id=3).all()
        for r in records:
            f.write(f"ID: {r.id}, visit_date: {r.visit_date}, hcw_id: {r.hcw_id}, type: {r.record_type}\n")
            f.write(f"Structured Data: {r.structured_data}\n\n")

    print("Audit report written to audit_report.txt")
