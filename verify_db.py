from app import app, db
from models import Announcement

with app.app_context():
    db.create_all()
    print("Database tables verified/created.")
