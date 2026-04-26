from app import create_app
from models import EmergencyRequest, User, Patient, db

app = create_app()

with app.app_context():
    print("=== Emergency Requests in Database ===")
    requests = EmergencyRequest.query.all()
    
    if not requests:
        print("❌ NO REQUESTS FOUND IN DATABASE")
    else:
        for req in requests:
            print(f"\nRequest ID: {req.id}")
            print(f"  Patient ID: {req.patient_id}")
            print(f"  Driver ID: {req.driver_id}")
            print(f"  Status: {req.status}")
            print(f"  Location: ({req.pickup_lat}, {req.pickup_lng})")
            print(f"  Created: {req.created_at}")
    
    print("\n=== Driver Users ===")
    drivers = User.query.filter_by(role='Driver').all()
    for driver in drivers:
        print(f"Driver: {driver.username} (ID: {driver.id})")
    
    print("\n=== Patient Users ===")
    patients = Patient.query.all()
    for patient in patients:
        print(f"Patient: {patient.name} (ID: {patient.id}, User ID: {patient.user_id})")
