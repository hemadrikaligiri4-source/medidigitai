from app import create_app
from extensions import db
from models import MedicalRecord, AuditLog, Patient, EmergencyRequest, PatientVitals
from datetime import datetime, timedelta
import random

app = create_app()

with app.app_context():
    now = datetime.utcnow()
    print(f"Updating all records to handle today's date: {now}")
    
    # Update Medical Records
    records = MedicalRecord.query.all()
    for i, r in enumerate(records):
        # Stagger them slightly so they aren't all EXACTLY the same second
        r.visit_date = now - timedelta(minutes=random.randint(1, 120))
        print(f"Updated MedicalRecord {r.id} to {r.visit_date}")
    
    # Update Audit Logs
    logs = AuditLog.query.all()
    for l in logs:
        l.timestamp = now - timedelta(minutes=random.randint(1, 60))
    
    # Update Emergency Requests
    reqs = EmergencyRequest.query.all()
    for req in reqs:
        req.created_at = now - timedelta(minutes=random.randint(1, 30))
        
    # Update Vitals
    vitals = PatientVitals.query.all()
    for v in vitals:
        v.recorded_at = now - timedelta(minutes=random.randint(1, 180))

    db.session.commit()
    print("\n✓ Successfully updated all database timestamps to today.")
