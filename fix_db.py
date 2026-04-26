from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Checking database schema...")
    with db.engine.connect() as conn:
        # Check columns
        res = conn.execute(text("PRAGMA table_info(medical_record)"))
        columns = [r[1] for r in res.fetchall()]
        print("Existing columns:", columns)
        
        if 'doctor_notes' not in columns:
            print("Adding doctor_notes column...")
            try:
                conn.execute(text("ALTER TABLE medical_record ADD COLUMN doctor_notes TEXT"))
                conn.commit()
                print("Column 'doctor_notes' added successfully.")
            except Exception as e:
                print(f"Error adding column: {e}")
        else:
            print("Column 'doctor_notes' already exists.")
