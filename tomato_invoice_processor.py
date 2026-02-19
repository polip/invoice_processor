#!/usr/bin/env python3
"""
Script to process Tomato teleoperator invoices from Gmail:
- Fetch emails from Tomato
- Extract barcode from HTML email message
- Save PDF attachments to Google Drive
- Send notification
"""

import os
import base64
import io
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PIL import Image
from pyzbar.pyzbar import decode

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.file',
]

# Configuration
SENDER_EMAIL = 'moj.racun@tomato.com.hr'  # Email address to filter for Iskon invoices
SEARCH_DAYS = 120 # How many days back to search
DRIVE_FOLDER_NAME = 'Tomato'


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


def search_tomato_emails(gmail_service, days_back=30):
    """Search for emails from Tomato within the specified time period."""
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


def get_inline_images(gmail_service, message_id):
    """Get all inline images (embedded in email body) from an email."""
    inline_images = {}

    try:
        message = gmail_service.users().messages().get(
            userId='me', id=message_id).execute()

        def extract_inline_parts(parts):
            for part in parts:
                # Check for nested parts
                if 'parts' in part:
                    extract_inline_parts(part['parts'])
                
                # Look for inline images
                headers = part.get('headers', [])
                content_id = None
                for header in headers:
                    if header['name'].lower() == 'content-id':
                        # Remove < and > from Content-ID
                        content_id = header['value'].strip('<>')
                        break
                
                mime_type = part.get('mimeType', '')
                if content_id and mime_type.startswith('image/'):
                    # Get image data
                    if 'attachmentId' in part.get('body', {}):
                        attachment = gmail_service.users().messages().attachments().get(
                            userId='me', messageId=message_id, id=part['body']['attachmentId']
                        ).execute()
                        data = base64.urlsafe_b64decode(attachment['data'])
                    elif 'data' in part.get('body', {}):
                        data = base64.urlsafe_b64decode(part['body']['data'])
                    else:
                        continue
                    
                    inline_images[content_id] = {
                        'data': data,
                        'mime_type': mime_type
                    }

        if 'parts' in message['payload']:
            extract_inline_parts(message['payload']['parts'])

        return inline_images
    except Exception as e:
        print(f'Error getting inline images from message {message_id}: {e}')
        return {}


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


def get_email_body(gmail_service, message_id):
    """Extract HTML body from email message."""
    try:
        message = gmail_service.users().messages().get(
            userId='me', id=message_id, format='full').execute()
        
        payload = message['payload']
        html_body = None
        
        def find_html_part(part):
            """Recursively find HTML part in message."""
            if part.get('mimeType') == 'text/html':
                if 'data' in part.get('body', {}):
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            
            # Check nested parts recursively
            if 'parts' in part:
                for subpart in part['parts']:
                    result = find_html_part(subpart)
                    if result:
                        return result
            
            return None
        
        # Check if payload has parts (multipart message)
        if 'parts' in payload:
            html_body = find_html_part(payload)
        # Single part message
        elif payload.get('mimeType') == 'text/html':
            if 'data' in payload.get('body', {}):
                html_body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return html_body
    except Exception as e:
        print(f'  Error extracting HTML body: {e}')
        return None


def extract_barcode_from_html(html_content, inline_images=None):
    """Extract barcode from HTML email by finding embedded images."""
    barcodes = []
    
    if not html_content:
        print('    No HTML content received')
        return barcodes
    
    if inline_images is None:
        inline_images = {}
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all img tags
        img_tags = soup.find_all('img')
        print(f'    Found {len(img_tags)} image(s) in HTML')
        
        for idx, img_tag in enumerate(img_tags):
            src = img_tag.get('src', '')
            alt = img_tag.get('alt', '')
            
            print(f'    Image {idx+1}: src="{src[:100]}..." alt="{alt}"')
            
            # Check if it's a CID (Content-ID) reference
            if src.startswith('cid:'):
                cid = src[4:]  # Remove 'cid:' prefix
                print(f'      Processing CID-referenced image: {cid}')
                
                if cid in inline_images:
                    try:
                        image_data = inline_images[cid]['data']
                        img = Image.open(io.BytesIO(image_data))
                        print(f'      Image size: {img.size}, mode: {img.mode}')
                        decoded_objects = decode(img)
                        
                        if decoded_objects:
                            print(f'      Found {len(decoded_objects)} barcode(s)!')
                            for obj in decoded_objects:
                                barcodes.append({
                                    'type': obj.type,
                                    'data': obj.data.decode('utf-8'),
                                    'method': 'inline_cid_image'
                                })
                        else:
                            print(f'      No barcode detected in this image')
                    except Exception as e:
                        print(f'      Error processing CID image: {e}')
                else:
                    print(f'      CID not found in inline images')
            
            # Check if it's a base64 encoded image
            elif src.startswith('data:image'):
                print(f'      Processing base64 embedded image...')
                # Extract the base64 data
                match = re.match(r'data:image/[^;]+;base64,(.+)', src)
                if match:
                    try:
                        image_data = base64.b64decode(match.group(1))
                        
                        # Try to decode barcode from the image
                        img = Image.open(io.BytesIO(image_data))
                        print(f'      Image size: {img.size}, mode: {img.mode}')
                        decoded_objects = decode(img)
                        
                        if decoded_objects:
                            print(f'      Found {len(decoded_objects)} barcode(s)!')
                            for obj in decoded_objects:
                                barcodes.append({
                                    'type': obj.type,
                                    'data': obj.data.decode('utf-8'),
                                    'method': 'html_embedded_image'
                                })
                        else:
                            print(f'      No barcode detected in this image')
                    except Exception as e:
                        print(f'      Error processing image: {e}')
                        continue
            else:
                print(f'      Skipped (not base64 or CID)')
        
        if barcodes:
            print(f'    Total: Found {len(barcodes)} barcode(s) in HTML')
        else:
            print('    Total: No barcodes found in HTML images')
            
    except Exception as e:
        print(f'    Error extracting barcode from HTML: {e}')
    
    return barcodes


def extract_payment_info_from_html(html_content):
    """Extract payment information from HTML text content."""
    if not html_content:
        return None
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        payment_info = {}
        
        # Extract IBAN (Croatian IBAN starts with HR)
        iban_match = re.search(r'HR\d{19}', text)
        if iban_match:
            payment_info['IBAN'] = iban_match.group(0)
        
        # Extract reference number (MODEL, POZIV NA BROJ)
        ref_match = re.search(r'(HR\d{2}\s+\d+)', text)
        if ref_match:
            payment_info['Reference'] = ref_match.group(1)
        
        # Extract invoice number pattern
        invoice_match = re.search(r'(\d{12}-\w+-\d+)', text)
        if invoice_match:
            payment_info['Invoice'] = invoice_match.group(1)
        
        if payment_info:
            return ', '.join([f'{k}: {v}' for k, v in payment_info.items()])
        
        return None
    except Exception as e:
        print(f'    Error extracting payment info from HTML: {e}')
        return None


def extract_barcode_from_attachment(file_data, filename):
    """Extract barcode from a PNG attachment."""
    barcodes = []
    
    if not filename.lower().endswith('.png'):
        return barcodes
    
    try:
        print(f'    Attempting to decode barcode from PNG attachment: {filename}')
        img = Image.open(io.BytesIO(file_data))
        print(f'    Image size: {img.size}, mode: {img.mode}')
        decoded_objects = decode(img)
        
        if decoded_objects:
            print(f'    Found {len(decoded_objects)} barcode(s)!')
            for obj in decoded_objects:
                barcodes.append({
                    'type': obj.type,
                    'data': obj.data.decode('utf-8'),
                    'method': 'png_attachment'
                })
        else:
            print(f'    No barcode detected in PNG attachment')
    except Exception as e:
        print(f'    Error extracting barcode from PNG: {e}')
    
    return barcodes


def file_exists_in_drive(drive_service, folder_id, filename):
    """Check if a file with the given name already exists in the Drive folder."""
    try:
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        files = results.get('files', [])
        return len(files) > 0
    except Exception as e:
        print(f'    Error checking for existing file: {e}')
        return False


def upload_to_drive(drive_service, folder_id, filename, file_data, description=None):
    """Upload file to Google Drive if it doesn't already exist."""
    # Check if file already exists
    if file_exists_in_drive(drive_service, folder_id, filename):
        print(f'    File already exists in Drive, skipping: {filename}')
        return None
    
    # Determine mimetype based on file extension
    if filename.lower().endswith('.png'):
        mimetype = 'image/png'
    else:
        mimetype = 'application/pdf'
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    if description:
        file_metadata['description'] = description

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

    print(f'Searching for Tomato emails from last {SEARCH_DAYS} days...')
    messages = search_tomato_emails(gmail_service, SEARCH_DAYS)

    if not messages:
        print('No emails found from Tomato')
        return

    print(f'Found {len(messages)} email(s)')

    processed_files = []

    for msg in messages:
        print(f'\nProcessing message {msg["id"]}...')
        
        # Get inline images (contains barcode images)
        print('  Extracting inline images...')
        inline_images = get_inline_images(gmail_service, msg['id'])
        print(f'  Found {len(inline_images)} inline image(s)')
        
        # Extract HTML body to identify barcode image
        print('  Extracting HTML body...')
        html_body = get_email_body(gmail_service, msg['id'])
        
        # Find the barcode image CID from HTML
        barcode_cid = None
        if html_body:
            soup = BeautifulSoup(html_body, 'html.parser')
            for img in soup.find_all('img'):
                alt = img.get('alt', '').lower()
                if 'kod' in alt or 'plaćanje' in alt or 'payment' in alt or 'barcode' in alt:
                    src = img.get('src', '')
                    if src.startswith('cid:'):
                        barcode_cid = src[4:]  # Remove 'cid:' prefix
                        print(f'  Found payment barcode image: CID={barcode_cid}, alt="{img.get("alt", "")}"')
                        break
        
        # Get PDF attachments
        attachments = get_attachments(gmail_service, msg['id'])
        pdf_filename = None
        
        # Upload PDF attachments
        for attachment in attachments:
            if attachment['filename'].lower().endswith('.pdf'):
                print(f'  Processing PDF: {attachment["filename"]}')
                pdf_filename = attachment['filename']
                
                uploaded_file = upload_to_drive(
                    drive_service, folder_id, attachment['filename'],
                    attachment['data'], None
                )
                
                if uploaded_file:
                    processed_files.append({
                        'filename': attachment['filename'],
                        'link': uploaded_file.get('webViewLink'),
                        'type': 'PDF',
                        'status': 'uploaded'
                    })
                    print(f'  Uploaded PDF: {uploaded_file.get("webViewLink")}')
                else:
                    processed_files.append({
                        'filename': attachment['filename'],
                        'link': None,
                        'type': 'PDF',
                        'status': 'skipped'
                    })
        
        # Upload the barcode image if found
        if barcode_cid and barcode_cid in inline_images:
            # Create filename based on PDF name
            if pdf_filename:
                base_name = pdf_filename.rsplit('.', 1)[0]
                barcode_filename = f'{base_name}_barcode.png'
            else:
                barcode_filename = f'Tomato_barcode_{msg["id"]}.png'
            
            print(f'  Processing barcode image: {barcode_filename}')
            
            uploaded_file = upload_to_drive(
                drive_service, folder_id, barcode_filename,
                inline_images[barcode_cid]['data'], None
            )
            
            if uploaded_file:
                processed_files.append({
                    'filename': barcode_filename,
                    'link': uploaded_file.get('webViewLink'),
                    'type': 'Barcode Image',
                    'status': 'uploaded'
                })
                print(f'  Uploaded barcode: {uploaded_file.get("webViewLink")}')
            else:
                processed_files.append({
                    'filename': barcode_filename,
                    'link': None,
                    'type': 'Barcode Image',
                    'status': 'skipped'
                })
        elif barcode_cid:
            print(f'  Warning: Barcode CID {barcode_cid} not found in inline images')
        else:
            print(f'  No barcode image found in email')

    # Send notification
    if processed_files:
        uploaded_count = sum(1 for pf in processed_files if pf['status'] == 'uploaded')
        skipped_count = sum(1 for pf in processed_files if pf['status'] == 'skipped')
        
        notification_body = f'Tomato Invoice Processing Summary:\n'
        notification_body += f'Uploaded: {uploaded_count}, Skipped (already exists): {skipped_count}\n\n'
        
        for pf in processed_files:
            notification_body += f'File: {pf["filename"]} ({pf["type"]})\n'
            if pf['status'] == 'uploaded':
                notification_body += f'Status: Uploaded\n'
                notification_body += f'Link: {pf["link"]}\n'
            else:
                notification_body += f'Status: Skipped (already exists)\n'
            notification_body += '\n'

        print('\n' + notification_body)
        send_notification(gmail_service, 'Tomato Invoice Processing Complete', notification_body)

    print(f'\nProcessed {len(processed_files)} file(s) successfully')


if __name__ == '__main__':
    main()
