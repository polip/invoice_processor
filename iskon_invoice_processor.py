#!/usr/bin/env python3
"""
Script to process Iskon teleoperator invoices from Gmail:
- Fetch emails from Iskon
- Save PDF and PNG attachments to Google Drive
- Send notification
"""

import os
import base64
import io
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.file',
]

# Configuration
SENDER_EMAIL = 'e-racun@iskon.hr'  # Email address to filter for Iskon invoices
SEARCH_DAYS = 10 # How many days back to search
DRIVE_FOLDER_NAME = 'Iskon'


def authenticate():
    """Authenticate and return Gmail and Drive service objects."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'iskon_token.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    gmail_service = build('gmail', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    return gmail_service, drive_service


def get_or_create_drive_folder(drive_service, folder_name):
    """Get or create a folder in Google Drive."""
    # Search for existing folder
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = results.get('files', [])

    if folders:
        return folders[0]['id']

    # Create folder if it doesn't exist
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return folder['id']


def search_iskon_emails(gmail_service, days_back=30):
    """Search for emails from Iskon within the specified time period."""
    # Calculate date for search query
    date_filter = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
    query = f'from:{SENDER_EMAIL} after:{date_filter} has:attachment'

    try:
        results = gmail_service.users().messages().list(
            userId='me', q=query).execute()
        messages = results.get('messages', [])

        return messages
    except Exception as e:
        print(f'Error searching emails: {e}')
        return []


def get_attachments(gmail_service, message_id):
    """Get all PDF and PNG attachments from an email."""
    attachments = []

    try:
        message = gmail_service.users().messages().get(
            userId='me', id=message_id).execute()

        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                filename_lower = part['filename'].lower() if part['filename'] else ''
                if filename_lower.endswith(('.pdf', '.png')):
                    if 'attachmentId' in part['body']:
                        attachment = gmail_service.users().messages().attachments().get(
                            userId='me', messageId=message_id, id=part['body']['attachmentId']
                        ).execute()

                        data = base64.urlsafe_b64decode(attachment['data'])
                        attachments.append({
                            'filename': part['filename'],
                            'data': data
                        })

        return attachments
    except Exception as e:
        print(f'Error getting attachments from message {message_id}: {e}')
        return []


def upload_to_drive(drive_service, folder_id, filename, file_data):
    """Upload file to Google Drive."""
    # Determine mimetype based on file extension
    if filename.lower().endswith('.png'):
        mimetype = 'image/png'
    else:
        mimetype = 'application/pdf'
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_data),
        mimetype=mimetype,
        resumable=True
    )

    try:
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        return file
    except Exception as e:
        print(f'Error uploading file to Drive: {e}')
        return None


def send_notification(gmail_service, subject, body):
    """Send an email notification to yourself."""
    try:
        from email.mime.text import MIMEText
        
        # Get user's email address
        profile = gmail_service.users().getProfile(userId='me').execute()
        sender_email = profile['emailAddress']
        
        # Create message
        message = MIMEText(body)
        message['to'] = sender_email
        message['from'] = sender_email
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        print('Notification sent successfully')
    except Exception as e:
        print(f'Error sending notification: {e}')


def main():
    print('Authenticating...')
    gmail_service, drive_service = authenticate()

    print('Getting/creating Drive folder...')
    folder_id = get_or_create_drive_folder(drive_service, DRIVE_FOLDER_NAME)

    print(f'Searching for Iskon emails from last {SEARCH_DAYS} days...')
    messages = search_iskon_emails(gmail_service, SEARCH_DAYS)

    if not messages:
        print('No emails found from Iskon')
        return

    print(f'Found {len(messages)} email(s)')

    processed_files = []

    for msg in messages:
        print(f'\nProcessing message {msg["id"]}...')
        attachments = get_attachments(gmail_service, msg['id'])

        for attachment in attachments:
            print(f'  Processing attachment: {attachment["filename"]}')

            # Upload to Drive
            print('  Uploading to Google Drive...')
            uploaded_file = upload_to_drive(
                drive_service, folder_id, attachment['filename'],
                attachment['data']
            )

            if uploaded_file:
                processed_files.append({
                    'filename': attachment['filename'],
                    'link': uploaded_file.get('webViewLink')
                })
                print(f'  Uploaded: {uploaded_file.get("webViewLink")}')

    # Send notification
    if processed_files:
        notification_body = 'Iskon Invoice Processing Summary:\n\n'
        for pf in processed_files:
            notification_body += f'File: {pf["filename"]}\n'
            notification_body += f'Link: {pf["link"]}\n\n'

        print('\n' + notification_body)
        send_notification(gmail_service, 'Iskon Invoice Processing Complete', notification_body)

    print(f'\nProcessed {len(processed_files)} file(s) successfully')


if __name__ == '__main__':
    main()
