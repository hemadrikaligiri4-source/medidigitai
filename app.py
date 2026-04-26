import os
from flask import Flask
from extensions import db, login_manager, jwt, socketio, mail
from datetime import timedelta


def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'medical-digitization-secret-key-123')
    
    # Use an absolute path for the SQLite database to ensure it points to the persistent disk on Render
    # On Render, we will mount a disk to /app/instance
    instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(instance_path, 'medical_system.db')}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-456')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    
    # Upload Folder (should also be on a persistent disk)
    # We can mount another disk or use a subfolder in the instance disk for simplicity
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', os.path.join(instance_path, 'uploads'))
    
    # Mail Configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '1234hemadri@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'xvmx tkkv zedi dpor')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', '1234hemadri@gmail.com')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)
    mail.init_app(app)
    
    # ── Auth0 Social Login (additive — existing login unchanged) ──────────────
    from auth0_helper import register_auth0
    register_auth0(app)

    
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'patients'))
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'records'))

    with app.app_context():
        # Import blueprints and models here to avoid circular imports
        from auth import auth as auth_blueprint
        from main import main as main_blueprint
        from api import api as api_blueprint
        
        app.register_blueprint(auth_blueprint)
        app.register_blueprint(main_blueprint)
        app.register_blueprint(api_blueprint, url_prefix='/api')
        
        from models import User, Patient, MedicalRecord, Ambulance, EmergencyRequest, AuditLog, Announcement
        db.create_all()
        
    # WebSocket Events
    @socketio.on('update_location')
    def handle_location(data):
        # data format: {driver_id: 1, lat: 12.3, lng: 77.5}
        from models import Ambulance, db
        from flask_socketio import emit
        amb = Ambulance.query.filter_by(driver_id=data['driver_id']).first()
        if amb:
            amb.current_lat = data['lat']
            amb.current_lng = data['lng']
            db.session.commit()
            emit('ambulance_location_updated', data, broadcast=True)

    @socketio.on('toggle_status')
    def handle_status(data):
        # data format: {driver_id: 1, status: 'Available'/'Offline'}
        from models import Ambulance, db
        amb = Ambulance.query.filter_by(driver_id=data['driver_id']).first()
        if not amb:
            amb = Ambulance(driver_id=data['driver_id'], status=data['status'])
            db.session.add(amb)
        else:
            amb.status = data['status']
        db.session.commit()

    @socketio.on('request_ambulance')
    def handle_request(data):
        # data format: {patient_id: 1, lat: 12.3, lng: 77.5}
        from models import EmergencyRequest, AuditLog, db
        from flask_socketio import emit
        
        print(f"\n🚨 EMERGENCY REQUEST RECEIVED 🚨")
        print(f"Patient ID: {data['patient_id']}")
        print(f"Location: ({data['lat']}, {data['lng']})")
        
        # Create a database record for the request
        req = EmergencyRequest(
            patient_id=data['patient_id'],
            pickup_lat=data['lat'],
            pickup_lng=data['lng'],
            status='Pending'
        )
        db.session.add(req)
        
        # Log the emergency request
        log = AuditLog(user_id=data.get('user_id', 1), action=f"Emergency request for Patient #{data['patient_id']}", patient_id=data['patient_id'])
        db.session.add(log)
        db.session.commit()
        
        print(f"✓ Request saved to DB with ID: {req.id}")
        print(f"📡 Broadcasting 'new_emergency_request' to all drivers...")
        
        # Broadcast to all drivers
        emit('new_emergency_request', {
            'request_id': req.id,
            'patient_id': data['patient_id'],
            'lat': data['lat'],
            'lng': data['lng']
        }, broadcast=True)
        
        print(f"✓ Broadcast complete!\n")

    @socketio.on('accept_emergency')
    def handle_accept(data):
        # data format: {request_id: 1, driver_id: 1}
        from models import EmergencyRequest, db
        from flask_socketio import emit
        
        print(f"\n✅ ACCEPT REQUEST RECEIVED")
        print(f"Request ID: {data['request_id']}, Driver ID: {data['driver_id']}")
        
        req = EmergencyRequest.query.get(data['request_id'])
        if req and req.status == 'Pending':
            req.status = 'Accepted'
            req.driver_id = data['driver_id']
            db.session.commit()
            
            print(f"✓ Request #{req.id} marked as Accepted")
            print(f"📡 Broadcasting 'emergency_accepted' to all clients...")
            
            # Notify the patient & other drivers
            emit('emergency_accepted', {
                'request_id': req.id,
                'driver_id': req.driver_id,
                'status': 'Accepted',
                'lat': req.pickup_lat,
                'lng': req.pickup_lng
            }, broadcast=True)
            
            print(f"✓ Broadcast complete!\n")

    @socketio.on('reject_emergency')
    def handle_reject(data):
        # Optional: handle rejection by logging or notifying other drivers
        pass

    @app.route('/update_language', methods=['POST'])
    def update_language():
        from flask import request, session, jsonify
        data = request.get_json()
        if data and 'language' in data:
            session['selected_language'] = data['language']
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error'}), 400

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"\n🚀 MedDigit AI starting on: http://127.0.0.1:{port}")
    socketio.run(app, host='127.0.0.1', port=port, debug=True)
