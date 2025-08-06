from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime, timedelta
import pytz
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Ensure database path exists
os.makedirs('data', exist_ok=True)  # Creates a folder named 'data' in your app directory
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/database.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

MASTER_ADMIN_KEY = "letmein123"

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
    fullname = request.form.get('fullname', '').strip()

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
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid username or password."

    return render_template('admin_login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('can_edit', None)
    return redirect(url_for('admin_login'))

@app.route('/exit_edit_mode', methods=['POST'])
def exit_edit_mode():
    session['can_edit'] = False
    flash('Edit mode disabled.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    can_edit = session.get('can_edit', False)
    show_modal = False

    if request.method == 'POST' and 'master_admin_key' in request.form:
        key = request.form.get('master_admin_key')
        if key and key == MASTER_ADMIN_KEY:
            session['can_edit'] = True
            can_edit = True
            flash('Edit mode enabled!', 'success')
        elif key:
            flash('Incorrect master admin key.', 'danger')
            show_modal = True

    # --- FILTER LOGIC ---
    fullname = request.args.get('fullname', '').strip()
    role = request.args.get('role', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = TimeEntry.query

    if fullname:
        query = query.filter(TimeEntry.fullname.ilike(f"%{fullname}%"))
    if role:
        query = query.filter(TimeEntry.role.ilike(f"%{role}%"))
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(TimeEntry.clock_in >= start_dt)
        except Exception as e:
            print(f"Start date filter error: {e}")
    if end_date:
        try:
            # To include all times on end_date, we filter < end_date + 1 day
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(TimeEntry.clock_in < end_dt)
        except Exception as e:
            print(f"End date filter error: {e}")

    pagination = query.order_by(TimeEntry.clock_in.desc()).paginate(page=page, per_page=per_page)
    entries = pagination.items

    # Calculate total hours per employee for all filtered records (not just paginated)
    # So, re-apply filters (for export/summary), not just paginated entries
    summary_query = query  # This is already filtered

    total_hours_per_employee = {}
    for entry in summary_query:
        duration = (entry.clock_out - entry.clock_in).total_seconds() / 3600 if entry.clock_out else 0
        total_hours_per_employee[entry.fullname] = total_hours_per_employee.get(entry.fullname, 0) + duration

    return render_template('dashboard.html',
                           entries=entries,
                           total_hours_per_employee=total_hours_per_employee,
                           pagination=pagination,
                           fullname=fullname,
                           role=role,
                           start_date=start_date,
                           end_date=end_date,
                           can_edit=can_edit,
                           show_modal=show_modal
    )

@app.route('/edit_entry/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if not session.get('can_edit'):
        flash('Unauthorized: Edit mode not enabled.', 'danger')
        return redirect(url_for('dashboard'))

    entry = TimeEntry.query.get_or_404(entry_id)

    if request.method == 'POST':
        clock_in_str = request.form.get('clock_in')
        clock_out_str = request.form.get('clock_out')
        timezone = request.form.get('timezone')

        try:
            entry.clock_in = datetime.strptime(clock_in_str, '%Y-%m-%d %I:%M %p')
        except Exception:
            flash('Invalid clock-in format. Use YYYY-MM-DD hh:mm AM/PM', 'danger')
            return render_template('edit_entry.html', entry=entry, clock_in_val=clock_in_str, clock_out_val=clock_out_str)

        if clock_out_str:
            try:
                entry.clock_out = datetime.strptime(clock_out_str, '%Y-%m-%d %I:%M %p')
            except Exception:
                flash('Invalid clock-out format. Use YYYY-MM-DD hh:mm AM/PM', 'danger')
                return render_template('edit_entry.html', entry=entry, clock_in_val=clock_in_str, clock_out_val=clock_out_str)
        else:
            entry.clock_out = None

        entry.timezone = timezone
        db.session.commit()
        flash('Entry updated successfully.', 'success')
        return redirect(url_for('dashboard'))

    clock_in_val = entry.clock_in.strftime('%Y-%m-%d %I:%M %p')
    clock_out_val = entry.clock_out.strftime('%Y-%m-%d %I:%M %p') if entry.clock_out else ''
    return render_template('edit_entry.html', entry=entry, clock_in_val=clock_in_val, clock_out_val=clock_out_val)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
