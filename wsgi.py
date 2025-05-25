import sys
import os

# Add your project directory to the sys.path
path = '/home/yourusername/GSEApp'  # Replace with your PythonAnywhere username
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['FLASK_SECRET_KEY'] = 'your-secret-key-here'  # Replace with your secret key
os.environ['GOOGLE_DRIVE_CREDENTIALS_FILE'] = '/home/yourusername/GSEApp/credentials.json'  # Replace with your username
os.environ['GOOGLE_DRIVE_TOKEN_FILE'] = '/home/yourusername/GSEApp/token.json'  # Replace with your username

# Import your Flask app
from app import app as application

# Initialize the database
with application.app_context():
    from app import db
    db.create_all() 