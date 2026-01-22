# GSE App - Inventory Management System

A Flask-based inventory management system with Google Drive integration. testing

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/GSEApp.git
cd GSEApp
``` 

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Google Drive Integration Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials
5. Download the credentials and save as `credentials.json` in the project root
6. The first time you run the app, it will create a `token.json` file

### 4. Environment Variables
Create a `.env` file with:
```
FLASK_SECRET_KEY=your-secret-key-here
GOOGLE_DRIVE_CREDENTIALS_FILE=credentials.json
GOOGLE_DRIVE_TOKEN_FILE=token.json
```

### 5. Run the Application
```bash
flask run
```

## Deployment
For deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)

## Security Notes
- Never commit `credentials.json` or `token.json` to version control
- Keep your `.env` file secure
- Regularly rotate your Google API credentials 
