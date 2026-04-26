from app import create_app
from models import EmergencyRequest, db

app = create_app()
with app.app_context():
    requests = EmergencyRequest.query.order_by(EmergencyRequest.id.desc()).limit(10).all()
    print("Recent Emergency Requests:")
    for r in requests:
        print(f"ID: {r.id}, Status: {r.status}, Time: {r.created_at}")
