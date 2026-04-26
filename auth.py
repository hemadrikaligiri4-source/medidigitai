from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import db, login_manager, mail
from flask_mail import Message
import random
from datetime import datetime, timedelta

from flask_jwt_extended import create_access_token


auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Search for user by username, email, or contact
        from sqlalchemy import or_
        user = User.query.filter(or_(
            User.username == username,
            User.email == username,
            User.contact == username
        )).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.email_verified:
                # For users who haven't verified or registered before OTP feature
                otp = str(random.randint(100000, 999999))
                user.otp_code = otp
                user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
                db.session.commit()
                
                try:
                    msg = Message("MedDigit AI - Verify Your Email",
                                  recipients=[user.email])
                    msg.body = f"Hello {user.full_name},\n\nPlease verify your email to access your MedDigit account.\n\nYour OTP is: {otp}\n\nThis code will expire in 10 minutes.\n\nThank you,\nMedDigit AI Team"
                    mail.send(msg)
                except Exception as e:
                    print(f"Login OTP send failed: {e}")
                
                if request.headers.get('Accept') == 'application/json' or request.is_json:
                    return jsonify({
                        "error": "Email not verified. A new OTP has been sent to your email.", 
                        "redirect": url_for('auth.verify_otp', user_id=user.id)
                    }), 403
                flash('Please verify your email first. A new OTP has been sent.')
                return redirect(url_for('auth.verify_otp', user_id=user.id))
                
            login_user(user)
            access_token = create_access_token(identity={'username': user.username, 'role': user.role})
            
            if request.headers.get('Accept') == 'application/json' or request.is_json:
                return jsonify({"message": "Login successful", "redirect": url_for('main.dashboard')})
                
            return redirect(url_for('main.dashboard'))
        
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return jsonify({"error": "Invalid credentials"}), 401
            
        flash('Invalid credentials')
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        contact = request.form.get('contact')
        password = request.form.get('password')
        role = request.form.get('role')
        full_name = request.form.get('full_name')
        specialty = request.form.get('specialty')
        research_areas = request.form.get('research_areas')
        years_of_experience = request.form.get('years_of_experience')
        
        from sqlalchemy import or_
        if User.query.filter(or_(User.username == username, User.email == email, User.contact == contact)).first():
            if request.headers.get('Accept') == 'application/json' or request.is_json:
                return jsonify({"error": "Identity already exists (username, email or mobile)"}), 400
            flash('Identity already exists')
            return redirect(url_for('auth.register'))
        
        new_user = User(
            username=username,
            email=email,
            contact=contact,
            password_hash=generate_password_hash(password),
            role=role,
            full_name=full_name,
            specialty=specialty if role == 'Doctor' else None,
            research_areas=research_areas if role == 'Doctor' else None,
            years_of_experience=int(years_of_experience) if role == 'Doctor' and years_of_experience else None
        )
        db.session.add(new_user)
        db.session.flush() # Get user ID before commit
        
        if role == 'Patient':
            from models import Patient
            import os
            from werkzeug.utils import secure_filename
            from flask import current_app
            
            # Handle condition document upload
            condition_doc_path = None
            if 'condition_document' in request.files:
                file = request.files['condition_document']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'conditions')
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, f"{username}_{filename}")
                    file.save(file_path)
                    condition_doc_path = f"static/uploads/conditions/{username}_{filename}"

            # Try to find an existing patient record with the same name that isn't linked yet
            existing_patient = Patient.query.filter_by(name=full_name).filter(Patient.user_id == None).first()
            if existing_patient:
                existing_patient.user_id = new_user.id
                if condition_doc_path:
                    existing_patient.condition_document = condition_doc_path
            else:
                # Create a placeholder patient record
                new_patient = Patient(name=full_name, user_id=new_user.id, contact=contact, has_consent=True, condition_document=condition_doc_path)
                db.session.add(new_patient)
        
        db.session.commit()
        
        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        new_user.otp_code = otp
        new_user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        new_user.email_verified = False
        
        db.session.commit()
        
        # Send OTP Email
        try:
            msg = Message("MedDigit AI - Email Verification",
                          recipients=[email])
            msg.body = f"Hello {full_name},\n\nYour OTP for registration is: {otp}\n\nThis code will expire in 10 minutes.\n\nThank you,\nMedDigit AI Team"
            mail.send(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")
            # If email fails, we should probably inform the user but let them try again later?
            # For now, let's treat it as a failure since user requested valid email.
            db.session.delete(new_user)
            db.session.commit()
            if request.headers.get('Accept') == 'application/json' or request.is_json:
                return jsonify({"error": "Failed to send verification email. Please enter a valid email ID."}), 400
            flash('Failed to send verification email. Please enter a valid email ID.')
            return redirect(url_for('auth.register'))
        
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return jsonify({"message": "OTP sent to your email", "redirect": url_for('auth.verify_otp', user_id=new_user.id)})
            
        return redirect(url_for('auth.verify_otp', user_id=new_user.id))
    return render_template('register.html')

@auth.route('/verify-otp/<int:user_id>', methods=['GET', 'POST'])
def verify_otp(user_id):
    user = User.query.get_or_404(user_id)
    if user.email_verified:
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        otp_input = request.form.get('otp')
        
        if user.otp_code == otp_input and user.otp_expiry > datetime.utcnow():
            user.email_verified = True
            user.otp_code = None
            user.otp_expiry = None
            db.session.commit()
            
            if request.headers.get('Accept') == 'application/json' or request.is_json:
                return jsonify({"message": "Email verified successfully!", "redirect": url_for('auth.login')})
            flash('Email verified successfully! You can now login.')
            return redirect(url_for('auth.login'))
        else:
            error = "Invalid or expired OTP"
            if request.headers.get('Accept') == 'application/json' or request.is_json:
                return jsonify({"error": error}), 400
            flash(error)
            
    return render_template('otp_verify.html', user_id=user_id, email=user.email)

@auth.route('/resend-otp/<int:user_id>')
def resend_otp(user_id):
    user = User.query.get_or_404(user_id)
    if user.email_verified:
        return redirect(url_for('auth.login'))
        
    otp = str(random.randint(100000, 999999))
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    
    try:
        msg = Message("MedDigit AI - Resend Email Verification",
                      recipients=[user.email])
        msg.body = f"Hello {user.full_name},\n\nYour new OTP for registration is: {otp}\n\nThis code will expire in 10 minutes.\n\nThank you,\nMedDigit AI Team"
        mail.send(msg)
        flash('A new OTP has been sent to your email.')
    except Exception as e:
        print(f"Failed to resend email: {e}")
        flash('Failed to send verification email. Please try again later.')
        
    return redirect(url_for('auth.verify_otp', user_id=user_id))

@auth.route('/change-email/<int:user_id>', methods=['POST'])
def change_email(user_id):
    user = User.query.get_or_404(user_id)
    if user.email_verified:
        return redirect(url_for('auth.login'))
        
    new_email = request.form.get('new_email')
    if not new_email:
        flash('Email is required')
        return redirect(url_for('auth.verify_otp', user_id=user_id))
        
    # Check if email is already taken
    existing_user = User.query.filter_by(email=new_email).first()
    if existing_user and existing_user.id != user_id:
        flash('This email is already registered to another account.')
        return redirect(url_for('auth.verify_otp', user_id=user_id))
        
    user.email = new_email
    otp = str(random.randint(100000, 999999))
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    
    try:
        msg = Message("MedDigit AI - Verify Your New Email",
                      recipients=[new_email])
        msg.body = f"Hello {user.full_name},\n\nYou have updated your email address.\n\nYour new verification OTP is: {otp}\n\nThis code will expire in 10 minutes.\n\nThank you,\nMedDigit AI Team"
        mail.send(msg)
        flash('Email updated and new OTP sent!')
    except Exception as e:
        print(f"Failed to send email to new address: {e}")
        flash('Email updated but failed to send verification code. Please try resending.')
        
    return redirect(url_for('auth.verify_otp', user_id=user_id))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
