from app import app, db
from models import MedicalRecord
from sqlalchemy import text

with app.app_context():
    try:
        # Check if column exists
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(medical_record)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'doctor_notes' not in columns:
                print("Column 'doctor_notes' missing. Adding it...")
                conn.execute(text("ALTER TABLE medical_record ADD COLUMN doctor_notes TEXT"))
                conn.commit()
                print("Column added successfully.")
            else:
                print("Column 'doctor_notes' already exists.")
                
            # Verify again
            result = conn.execute(text("PRAGMA table_info(medical_record)"))
            columns = [row[1] for row in result.fetchall()]
            print(f"Current columns in medical_record: {columns}")
            
    except Exception as e:
        print(f"Error: {e}")
