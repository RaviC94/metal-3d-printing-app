# app.py - Main application file
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///printing_service.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='operator')
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

# Order Model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='enquiry')
    current_department = db.Column(db.String(50), nullable=False, default='marketing')
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Machine Model
class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_name = db.Column(db.String(50), nullable=False)
    machine_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='idle')
    current_order = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    last_maintenance = db.Column(db.DateTime)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:  # In production, use proper password hashing
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get department-specific data
    if current_user.department == 'marketing':
        orders = Order.query.filter_by(current_department='marketing').all()
    elif current_user.department == 'production':
        orders = Order.query.filter_by(current_department='production').all()
        machines = Machine.query.all()
        return render_template('production_dashboard.html', orders=orders, machines=machines)
    else:
        orders = Order.query.filter_by(current_department=current_user.department).all()
    
    return render_template('dashboard.html', orders=orders)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# API Routes for dynamic updates
@app.route('/api/orders')
@login_required
def get_orders():
    orders = Order.query.filter_by(current_department=current_user.department).all()
    return jsonify([{
        'id': order.id,
        'order_number': order.order_number,
        'customer_name': order.customer_name,
        'status': order.status,
        'created_date': order.created_date.strftime('%Y-%m-%d %H:%M')
    } for order in orders])

@app.route('/api/machines')
@login_required
def get_machines():
    if current_user.department == 'production':
        machines = Machine.query.all()
        return jsonify([{
            'id': machine.id,
            'name': machine.machine_name,
            'status': machine.status,
            'current_order': machine.current_order
        } for machine in machines])
    return jsonify([])

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default users if they don't exist
        if not User.query.first():
            departments = [
                ('marketing', 'Marketing'),
                ('application', 'Application & R&D'),
                ('production', 'Production'),
                ('scm', 'Supply Chain Management'),
                ('metallurgy', 'Metallurgy'),
                ('stores', 'Stores & Inspection'),
                ('maintenance', 'Machine Maintenance')
            ]
            
            for dept_code, dept_name in departments:
                user = User(
                    username=f'{dept_code}_user',
                    email=f'{dept_code}@company.com',
                    password='password123',  # Change in production
                    department=dept_code,
                    role='operator'
                )
                db.session.add(user)
            
            # Create admin user
            admin = User(
                username='admin',
                email='admin@company.com',
                password='admin123',
                department='management',
                role='admin'
            )
            db.session.add(admin)
            
            # Create sample machines
            machines = [
                Machine(machine_name='SLM-1', machine_type='SLM', status='idle'),
                Machine(machine_name='SLM-2', machine_type='SLM', status='idle'),
                Machine(machine_name='EBM-1', machine_type='EBM', status='maintenance')
            ]
            
            for machine in machines:
                db.session.add(machine)
            
            db.session.commit()
            print("✅ Database initialized with sample data")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)