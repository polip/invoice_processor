Setup Instructions for Invoice Processors
=========================================

1. Install system dependencies (for barcode scanning):

   Ubuntu/Debian:
   sudo apt-get update
   sudo apt-get install poppler-utils libzbar0

   macOS:
   brew install poppler zbar

2. Install Python dependencies:
   pip install -r requirements.txt

3. Set up Google Cloud Project:
   a. Go to https://console.cloud.google.com/
   b. Create a new project (or use existing)
   c. Enable required APIs:
      - Go to "APIs & Services" > "Library"
      - Search for "Gmail API" and enable it
      - Search for "Google Drive API" and enable it

   d. Create OAuth 2.0 credentials:
      - Go to "APIs & Services" > "Credentials"
      - Click "Create Credentials" > "OAuth client ID"
      - Choose "Desktop app" as application type
      - Download the credentials JSON file
      - Rename it to match the expected filename in the project root:
        client_secret_544079871095-7eo15ghsvks1u43urcft84afblheu732.apps.googleusercontent.com.json

4. Run a processor:
   python3 main.py iskon
   python3 main.py tomato
   python3 main.py all

   On first run, a browser window will open for OAuth authentication.
   Grant the requested permissions (Gmail read/send, Drive file access).
   A token.json file will be created for future runs.

5. Set up automation (optional):
   The included run_on_10th_workday.sh script checks whether today is the
   10th working day of the month and runs both processors if so.

   Add to crontab to run daily at 9 AM:
   0 9 * * * /home/ivan/Documents/e-mail_processor/run_on_10th_workday.sh

Notes:
- The script creates a "token.json" file after first authentication
- Invoices are saved to Google Drive in the "Iskon" and "Tomato" folders
- You'll receive an email notification with a processing summary
- Both processors now skip duplicate files automatically
