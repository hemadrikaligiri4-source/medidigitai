from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import Patient, MedicalRecord, Ambulance, EmergencyRequest
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Doctor':
        # Doctors only see patients who have explicitly granted them access
        from models import DoctorPatientAccess
        access_list = DoctorPatientAccess.query.filter_by(doctor_id=current_user.id).all()
        patient_ids = [a.patient_id for a in access_list]
        patients = Patient.query.filter(Patient.id.in_(patient_ids)).all() if patient_ids else []
        return render_template('doctor_dashboard.html', patients=patients)
    elif current_user.role == 'HCW':
        # Healthcare workers see patient registration and upload
        return render_template('hcw_dashboard.html')
    elif current_user.role == 'Driver':
        # Drivers see emergency requests assigned to them OR pending ones
        from sqlalchemy import or_
        requests = EmergencyRequest.query.filter(
            or_(
                EmergencyRequest.status == 'Pending',
                EmergencyRequest.driver_id == current_user.id
            )
        ).all()
        
        # DEBUG: Print what we found
        print(f"\n=== DRIVER DASHBOARD DEBUG ===")
        print(f"Current Driver ID: {current_user.id}")
        print(f"Total requests found: {len(requests)}")
        for req in requests:
            print(f"  - Request #{req.id}: Status={req.status}, Driver={req.driver_id}, Patient={req.patient_id}")
        print(f"==============================\n")
        
        # Fetch status for persistence
        ambulance = Ambulance.query.filter_by(driver_id=current_user.id).first()
        return render_template('driver_dashboard.html', requests=requests, ambulance=ambulance)
    elif current_user.role == 'Patient':
        # Patients see their own medical history dashboard
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        return render_template('patient_dashboard.html', patient=patient)
    elif current_user.role == 'Admin':
        return render_template('admin_dashboard.html')
    return redirect(url_for('main.index'))

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', now=datetime.now().strftime('%Y-%m-%d %H:%M'))

