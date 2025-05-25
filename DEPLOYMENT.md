# Deployment Guide for PythonAnywhere

## 1. Initial Setup
1. Sign up for a PythonAnywhere account
2. Go to the Web tab
3. Click "Add a new web app"
4. Choose "Manual configuration"
5. Select Python 3.10 (or latest version)

## 2. Clone Repository
```bash
git clone https://github.com/yourusername/GSEApp.git
cd GSEApp
```

## 3. Set Up Virtual Environment
```bash
mkvirtualenv --python=/usr/bin/python3.10 GSEApp
pip install -r requirements.txt
```

## 4. Configure Web App
1. In the Web tab:
   - Set "Source code" to `/home/yourusername/GSEApp`
   - Set "Working directory" to `/home/yourusername/GSEApp`
   - Set "Virtualenv" to `/home/yourusername/.virtualenvs/GSEApp`

## 5. Set Environment Variables
In the Web tab, add these environment variables:
```
FLASK_SECRET_KEY=your-secret-key-here
GOOGLE_DRIVE_CREDENTIALS_FILE=/home/yourusername/GSEApp/credentials.json
GOOGLE_DRIVE_TOKEN_FILE=/home/yourusername/GSEApp/token.json
```

## 6. Upload Google Drive Credentials
1. Go to the Files tab
2. Upload your `credentials.json` file to the GSEApp directory
3. The first time you use the app, it will create `token.json`

## 7. Configure WSGI File
In the Web tab, update the WSGI file with:
```python
import sys
import os

path = '/home/yourusername/GSEApp'
if path not in sys.path:
    sys.path.append(path)

os.environ['FLASK_SECRET_KEY'] = 'your-secret-key-here'
os.environ['GOOGLE_DRIVE_CREDENTIALS_FILE'] = '/home/yourusername/GSEApp/credentials.json'
os.environ['GOOGLE_DRIVE_TOKEN_FILE'] = '/home/yourusername/GSEApp/token.json'

from app import app as application

with application.app_context():
    from app import db
    db.create_all()
```

## 8. Enable HTTPS
1. In the Web tab, under "Security"
2. Check "Force HTTPS"

## 9. Reload Web App
Click the "Reload" button in the Web tab

## Important Notes
- Replace `yourusername` with your actual PythonAnywhere username
- Keep your credentials secure
- The first time you use Google Drive features, you'll need to authenticate
- Make sure all file permissions are correct 