from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Migrating User table...")
    with db.engine.connect() as conn:
        # Check existing columns
        res = conn.execute(text("PRAGMA table_info(user)"))
        columns = [r[1] for r in res.fetchall()]
        print("Existing User columns:", columns)
        
        try:
            if 'email' not in columns:
                print("Adding email column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN email VARCHAR(120)"))
                # We can't add UNIQUE constraint via ALTER TABLE in basic SQLite for existing columns easily without recreation
                # but we can try to add it later or just handle it in app logic if necessary.
                # SQLite ALTER TABLE is limited.
            
            if 'email_verified' not in columns:
                print("Adding email_verified column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN email_verified BOOLEAN DEFAULT 0"))

            if 'specialty' not in columns:
                print("Adding specialty column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN specialty VARCHAR(100)"))

            if 'research_areas' not in columns:
                print("Adding research_areas column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN research_areas TEXT"))

            if 'years_of_experience' not in columns:
                print("Adding years_of_experience column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN years_of_experience INTEGER"))

            if 'otp_code' not in columns:
                print("Adding otp_code column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN otp_code VARCHAR(6)"))

            if 'otp_expiry' not in columns:
                print("Adding otp_expiry column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN otp_expiry DATETIME"))
            
            # Contact might already exist but we want to ensure it behaves correctly
            # Re-running unique constraint check isn't easy in SQLite ALTER.
            
            conn.commit()
            print("Migration successful.")
        except Exception as e:
            print(f"Migration error: {e}")
            conn.rollback()
