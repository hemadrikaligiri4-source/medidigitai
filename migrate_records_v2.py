from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Migrating MedicalRecord table...")
    with db.engine.connect() as conn:
        # Check existing columns
        res = conn.execute(text("PRAGMA table_info(medical_record)"))
        columns = [r[1] for r in res.fetchall()]
        print("Existing MedicalRecord columns:", columns)
        
        try:
            if 'hospital_name' not in columns:
                print("Adding hospital_name column...")
                conn.execute(text("ALTER TABLE medical_record ADD COLUMN hospital_name VARCHAR(100)"))
            
            if 'treating_doctor_name' not in columns:
                print("Adding treating_doctor_name column...")
                conn.execute(text("ALTER TABLE medical_record ADD COLUMN treating_doctor_name VARCHAR(100)"))
            
            conn.commit()
            print("Migration successful.")
        except Exception as e:
            print(f"Migration error: {e}")
            conn.rollback()
