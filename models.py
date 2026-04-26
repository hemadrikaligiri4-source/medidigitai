from extensions import db

from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Doctor, HCW, Driver, Admin
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    contact = db.Column(db.String(20), unique=True)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Doctor specific fields
    specialty = db.Column(db.String(100))
    research_areas = db.Column(db.Text)
    years_of_experience = db.Column(db.Integer)
    
    # OTP fields
    otp_code = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    contact = db.Column(db.String(20))
    face_photo = db.Column(db.String(200))
    health_card_number = db.Column(db.String(50))
    health_card_type = db.Column(db.String(50)) # Arogyasri, Ayushman Bharat, etc.
    condition_document = db.Column(db.String(255)) # Uploaded medical background document
    has_consent = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) # Link to login account
    relationship = db.Column(db.String(50), default='Self') # Self, Father, Mother, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    records = db.relationship('MedicalRecord', backref='patient', lazy=True)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    hcw_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    raw_ocr_text = db.Column(db.Text)
    structured_data = db.Column(db.JSON)
    document_image = db.Column(db.String(200))
    record_type = db.Column(db.String(50), default='Prescription') # Prescription, Lab Report, Clinical Notes, etc.
    hospital_name = db.Column(db.String(100))
    treating_doctor_name = db.Column(db.String(100))
    doctor_notes = db.Column(db.Text)

class Ambulance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='Available')  # Available, Busy, Offline
    current_lat = db.Column(db.Float)
    current_lng = db.Column(db.Float)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EmergencyRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Completed, Rejected
    pickup_lat = db.Column(db.Float)
    pickup_lng = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DoctorPatientAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships for easier querying
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref='patient_access_list')
    patient = db.relationship('Patient', foreign_keys=[patient_id], backref='authorized_doctors')

class PatientVitals(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    heart_rate = db.Column(db.Integer)  # bpm
    blood_pressure_sys = db.Column(db.Integer) # systolic
    blood_pressure_dia = db.Column(db.Integer) # diastolic
    temperature = db.Column(db.Float) # Celsius
    spo2 = db.Column(db.Integer) # Percentage
    notes = db.Column(db.String(200))

    patient = db.relationship('Patient', backref=db.backref('vitals_history', lazy=True))
