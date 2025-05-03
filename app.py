from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
import pytz
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

# Database Models
class TimeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False)
    clock_out = db.Column(db.DateTime, nullable=True)
    timezone = db.Column(db.String(50), nullable=False)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Routes
@app.route('/')
def index():
    # Get unique full names from past entries
    names = db.session.query(TimeEntry.fullname).distinct().all()
    unique_names = sorted(set(name[0] for name in names if name[0]))
    return render_template('index.html', unique_names=unique_names)

@app.route('/clock-in', methods=['POST'])
def clock_in():
    fullname = request.form.get('fullname')
    role = request.form.get('role')
    timezone = request.form.get('timezone')

    if not fullname or not role or not timezone:
        return jsonify({"status": "error", "message": "All fields required."})

    fullname = ' '.join(word.capitalize() for word in fullname.strip().split())

    existing = TimeEntry.query.filter(
        func.lower(TimeEntry.fullname) == fullname.lower(),
        TimeEntry.clock_out == None
    ).first()

    if existing:
        return jsonify({"status": "error", "message": "Already clocked in. Please clock out first."})

    entry = TimeEntry(
        fullname=fullname,
        role=role,
        clock_in=datetime.now(pytz.timezone(timezone)),
        timezone=timezone
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({"status": "success", "message": "Clocked in successfully."})

@app.route('/clock-out', methods=['POST'])
def clock_out():
    fullname = request.form.get('fullname')
    fullname = fullname.strip()

    entry = TimeEntry.query.filter(
        func.lower(TimeEntry.fullname) == fullname.lower(),
        TimeEntry.clock_out == None
    ).order_by(TimeEntry.clock_in.desc()).first()

    if not entry:
        return jsonify({"status": "error", "message": "No active clock-in found."})

    entry.clock_out = datetime.now(pytz.timezone(entry.timezone))
    db.session.commit()

    return jsonify({"status": "success", "message": "Clocked out successfully."})

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials. Please try again."

    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    fullname = request.args.get('fullname', '')
    role = request.args.get('role', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = TimeEntry.query

    if fullname:
        query = query.filter(TimeEntry.fullname.ilike(f"%{fullname}%"))
    if role:
        query = query.filter(TimeEntry.role.ilike(f"%{role}%"))
    if start_date:
        query = query.filter(TimeEntry.clock_in >= start_date)
    if end_date:
        query = query.filter(TimeEntry.clock_in <= end_date)

    pagination = query.order_by(TimeEntry.clock_in.desc()).paginate(page=page, per_page=per_page)
    entries = pagination.items

    total_hours_per_employee = {}
    for entry in query:
        if entry.clock_in and entry.clock_out:
            duration = (entry.clock_out - entry.clock_in).total_seconds() / 3600
        else:
            duration = 0
        total_hours_per_employee[entry.fullname] = total_hours_per_employee.get(entry.fullname, 0) + duration

    return render_template('dashboard.html',
                           entries=entries,
                           total_hours_per_employee=total_hours_per_employee,
                           pagination=pagination,
                           fullname=fullname,
                           role=role,
                           start_date=start_date,
                           end_date=end_date)

@app.route('/delete/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    entry = TimeEntry.query.get(entry_id)
    if entry:
        db.session.delete(entry)
        db.session.commit()

    return redirect(url_for('dashboard'))

@app.route('/delete-selected', methods=['POST'])
def delete_selected():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    ids = request.form.getlist('selected_ids')
    if ids:
        for entry_id in ids:
            entry = TimeEntry.query.get(entry_id)
            if entry:
                db.session.delete(entry)
        db.session.commit()

    return redirect(url_for('dashboard'))

# Initialize database and create default admin
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123')
            admin = Admin(username='admin', password=hashed_pw)
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
