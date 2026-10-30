# ==============================================================================
# PythonAnywhere WSGI Configuration for CampusVoice
# File location on PythonAnywhere: /var/www/<username>_pythonanywhere_com_wsgi.py
# (Or paste this into the Web tab -> WSGI configuration file editor)
# ==============================================================================

import os
import sys

# ------------------------------------------------------------------------------
# 1. ACCOUNT PATH CONFIGURATION
# Replace '<your-username>' with your actual PythonAnywhere account username.
# Example: If your username is 'rohit', path is '/home/rohit/CampusVoice'
# ------------------------------------------------------------------------------
USERNAME = '<your-username>'
PROJECT_DIR = f'/home/{USERNAME}/CampusVoice'

# Add project root directory to Python search path
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# ------------------------------------------------------------------------------
# 2. PERSISTENCE & ENVIRONMENT CONFIGURATION
# Point database and uploads to private locations OUTSIDE the web/static dir.
# ------------------------------------------------------------------------------
DATA_DIR = f'/home/{USERNAME}/data'
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(f'{DATA_DIR}/uploads', exist_ok=True)

# Set runtime environment variables
os.environ.setdefault('SQLITE_PATH', f'{DATA_DIR}/campusvoice.db')
os.environ.setdefault('UPLOAD_FOLDER', f'{DATA_DIR}/uploads')
os.environ.setdefault('SECRET_KEY', 'replace-with-a-strong-random-key-for-pythonanywhere')
os.environ.setdefault('WTF_CSRF_SECRET_KEY', 'replace-with-a-strong-csrf-key-for-pythonanywhere')
os.environ.setdefault('PUBLIC_BASE_URL', f'https://{USERNAME}.pythonanywhere.com')
os.environ.setdefault('COLLEGE_EMAIL_DOMAINS', 'campus.edu,university.ac.in,student.college.edu')
os.environ.setdefault('SESSION_COOKIE_SECURE', 'false')  # Set to 'true' if custom HTTPS domain is active

# ------------------------------------------------------------------------------
# 3. APPLICATION FACTORY INITIALIZATION
# PythonAnywhere WSGI server expects a top-level callable named 'application'.
# ------------------------------------------------------------------------------
from app import create_app
from app.extensions import db

application = create_app()

# Initialize database schema safely if not already created (never drops or reseeds data)
with application.app_context():
    db.create_all()

