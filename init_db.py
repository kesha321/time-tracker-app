from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from flask import Flask
import os

# === Initialize Flask app ===
app = Flask(__name__)

# Ensure mount path exists (safe for local and Render)
os.makedirs('/mnt/data', exist_ok=True)

# Persistent database path
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////mnt/data/database.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'

db = SQLAlchemy(app)

# === Database Models ===
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

# === Create tables and update/create admin user ===
with app.app_context():
    db.create_all()

    # REMOVE ALL ADMIN USERS
    deleted = Admin.query.delete()
    db.session.commit()
    if deleted:
        print(f"🗑️ Deleted {deleted} old admin user(s).")

    # Add the only admin you want
    NEW_USERNAME = 'absadmin'
    NEW_PASSWORD = 'admin12345'
    admin = Admin(
        username=NEW_USERNAME,
        password=generate_password_hash(NEW_PASSWORD)
    )
    db.session.add(admin)
    db.session.commit()
    print(f"✅ Created new admin: {NEW_USERNAME}")

