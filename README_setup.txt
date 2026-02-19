Setup Instructions for Iskon Invoice Processor
===============================================

1. Install system dependencies (for barcode scanning):

   Ubuntu/Debian:
   sudo apt-get install poppler-utils libzbar0

   macOS:
   brew install poppler zbar

2. Install Python dependencies:
   pip install -r requirements.txt

3. Set up Google Cloud Project:
   a. Go to https://console.cloud.google.com/
   b. Create a new project (or use existing)
   c. Enable Gmail API and Google Drive API:
      - Go to "APIs & Services" > "Library"
      - Search for "Gmail API" and enable it
      - Search for "Google Drive API" and enable it

   d. Create OAuth 2.0 credentials:
      - Go to "APIs & Services" > "Credentials"
      - Click "Create Credentials" > "OAuth client ID"
      - Choose "Desktop app" as application type
      - Download the credentials JSON file
      - Save it as "credentials.json" in the same directory as the script

4. Configure the script:
   Edit iskon_invoice_processor.py and adjust:
   - SENDER_EMAIL: Set to exact sender email (e.g., 'noreply@iskon.hr')
   - SEARCH_DAYS: How many days back to search
   - DRIVE_FOLDER_NAME: Name of folder in Google Drive

5. Run the script:
   python3 iskon_invoice_processor.py

   On first run, it will open a browser for OAuth authentication.
   Grant the requested permissions (Gmail read, Drive file access).

6. Set up automation (optional):
   Add to crontab to run daily at 9 AM:
   0 9 * * * /usr/bin/python3 /home/ivan/iskon_invoice_processor.py

Notes:
- The script creates a "token.json" file after first authentication
- Invoices are saved to Google Drive in the specified folder
- You'll receive an email notification with extracted barcodes
- Adjust SENDER_EMAIL to match your Iskon sender address
