from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import pickle
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """Get or create Google Drive service."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            # Set the access type to offline and include the prompt for consent
            creds = flow.run_local_server(
                port=0,
                prompt='consent',
                authorization_prompt_message='Please authorize the application to access your Google Drive.'
            )
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def get_gse_folder_id(service):
    """Get the ID of the GSE folder in Google Drive."""
    # Search for the GSE folder
    results = service.files().list(
        q="name='GSE' and mimeType='application/vnd.google-apps.folder'",
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    
    items = results.get('files', [])
    
    if items:
        # GSE folder exists, return its ID
        return items[0]['id']
    else:
        # Create GSE folder
        return create_folder(service, 'GSE')

def create_folder(service, folder_name, parent_id=None):
    """Create a folder in Google Drive."""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    file = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    
    logger.debug(f"Created folder {folder_name} with ID: {file.get('id')}")
    return file.get('id')

def upload_file(service, file_path, folder_id=None):
    """Upload a file to Google Drive."""
    file_name = os.path.basename(file_path)
    file_metadata = {'name': file_name}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(
        file_path,
        resumable=True
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    
    logger.debug(f"Uploaded file {file_name} with ID: {file.get('id')}")
    return file.get('id'), file.get('webViewLink')

def get_or_create_folder_structure(service, path_parts):
    """Create a folder structure in Google Drive and return the final folder ID."""
    # Get the GSE folder ID as the root
    current_parent_id = get_gse_folder_id(service)
    
    for folder_name in path_parts:
        # Search for the folder in the current parent
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        if current_parent_id:
            query += f" and '{current_parent_id}' in parents"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        
        if items:
            # Folder exists, use its ID
            current_parent_id = items[0]['id']
        else:
            # Create new folder
            current_parent_id = create_folder(service, folder_name, current_parent_id)
    
    return current_parent_id

def save_to_drive(local_path, drive_path):
    """Save a file to Google Drive maintaining the same folder structure."""
    try:
        service = get_drive_service()
        
        # Split the path into parts
        path_parts = drive_path.split(os.sep)
        file_name = path_parts[-1]
        folder_parts = path_parts[:-1]
        
        # Create folder structure and get the parent folder ID
        parent_id = get_or_create_folder_structure(service, folder_parts)
        
        # Upload the file
        file_id, web_link = upload_file(service, local_path, parent_id)
        
        logger.debug(f"File saved to Drive: {web_link}")
        return web_link
        
    except Exception as e:
        logger.error(f"Error saving to Drive: {str(e)}")
        raise 