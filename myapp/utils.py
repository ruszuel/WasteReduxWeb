import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
PLASTIC_FOLDER_ID = os.getenv('PLASTIC_FOLDER_ID')
METAL_FOLDER_ID = os.getenv('METAL_FOLDER_ID')
GLASS_FOLDER_ID = os.getenv('GLASS_FOLDER_ID')

def authenticate_drive():
    """Authenticate and return Google Drive service."""
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_image_to_drive(file_path, file_name, category):
    """Upload a file to Google Drive in the specified category folder."""
    service = authenticate_drive()
    
    folder_id = None
    if category.lower() == 'plastic':
        folder_id = PLASTIC_FOLDER_ID
    elif category.lower() == 'metal':
        folder_id = METAL_FOLDER_ID
    elif category.lower() == 'glass':
        folder_id = GLASS_FOLDER_ID
    else:
        print(f"Unknown category: {category}")
        return None

    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='image/jpeg')

    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        print(f"Uploaded file with ID: {file_id}")
        return file_id 
    except Exception as e:
        print(f"Failed to upload: {e}")
        return None
    
def get_images_by_category(model, category=None, college=None, date_filter=None):
    """
    A reusable function to fetch images by category, college, and optional date filters.
    """
    query = model.objects.filter(isArchived=False, email_address__isArchived=False)
    if category:
        query = query.filter(category=category)
    if college:
        query = query.filter(email_address__college_department=college)
    if date_filter:
        query = query.filter(date_filter)
    return query

