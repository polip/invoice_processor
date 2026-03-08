# E-mail Processor

Email invoice processor for Croatian telecom providers (Iskon and Tomato). Automatically fetches invoices from Gmail, processes attachments, and uploads them to Google Drive with optional automated scheduling.

## Features

- **Automated Email Fetching**: Searches Gmail for invoices from Iskon and Tomato
- **Attachment Processing**: Extracts PDF and PNG attachments from emails
- **Barcode Extraction**: Scans and extracts barcodes from invoice images
- **Google Drive Integration**: Uploads processed invoices to organized folders
- **Smart Scheduling**: Run automatically on the 10th working day of each month
- **Email Notifications**: Sends summary notifications after processing

## Prerequisites

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install poppler-utils libzbar0
```

**macOS:**
```bash
brew install poppler zbar
```

### Python Requirements

- Python 3.12 or higher
- Virtual environment (recommended)

## Installation

1. **Clone or download the repository**
   ```bash
   cd /path/to/e-mail_processor
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate  # Windows
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### 1. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable required APIs:
   - **Gmail API**: For reading emails
   - **Google Drive API**: For uploading files
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Choose "Desktop app" as application type
   - Download the credentials JSON file
   - Save it in the project directory (file already present: `client_secret_544079871095-7eo15ghsvks1u43urcft84afblheu732.apps.googleusercontent.com.json`)

### 2. First-Time Authentication

On first run, the script will:
1. Open a browser for OAuth authentication
2. Ask for Gmail and Drive permissions
3. Create `token.json` for future authentication

### 3. Script Configuration

**Iskon Processor** (`iskon.py`):
```python
SENDER_EMAIL = 'e-racun@iskon.hr'
SEARCH_DAYS = 10
DRIVE_FOLDER_NAME = 'Iskon'
```

**Tomato Processor** (`tomato.py`):
```python
SENDER_EMAIL = 'moj.racun@tomato.com.hr'
SEARCH_DAYS = 10
DRIVE_FOLDER_NAME = 'Tomato'
```

## Usage

### Manual Execution

**Process Iskon invoices:**
```bash
python3 iskon.py
```

**Process Tomato invoices:**
```bash
python3 tomato.py
```

**Check if today is the 10th working day:**
```bash
python3 check_10th_workday.py
```

### Automated Scheduling

The project includes automation to run on the 10th working day of each month.

**Set up with cron:**
```bash
# Edit crontab
crontab -e

# Add this line to run daily at 9 AM
0 9 * * * /home/ivan/Documents/e-mail_processor/run_on_10th_workday.sh >> /tmp/iskon_cron.log 2>&1
```

The script will:
1. Check if today is the 10th working day
2. Run the invoice processor if true
3. Skip execution otherwise

## Project Structure

```
e-mail_processor/
├── iskon.py                     # Iskon invoice processor
├── tomato.py                    # Tomato invoice processor
├── check_10th_workday.py        # Working day calculator
├── run_on_10th_workday.sh       # Automation script
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
├── client_secret_*.json        # Google OAuth credentials
├── token.json                  # Generated auth token (after first run)
├── README.md                   # This file
└── README_setup.txt            # Original setup notes
```

## How It Works

### Iskon Processor
1. Searches Gmail for emails from `e-racun@iskon.hr`
2. Extracts PDF and PNG attachments
3. Uploads files to "Iskon" folder in Google Drive
4. Sends notification email with summary

### Tomato Processor
1. Searches Gmail for emails from `moj.racun@tomato.com.hr`
2. Extracts inline images and barcodes from HTML email
3. Saves PDF attachments
4. Uploads to "Tomato" folder in Google Drive
5. Sends notification with extracted barcode information

### Working Day Scheduler
- Counts only Monday-Friday as working days
- Excludes weekends (Saturday/Sunday)
- Note: Does not account for public holidays

## Troubleshooting

### Authentication Issues
- If you get authentication errors, delete `token.json` and re-authenticate
- Ensure OAuth credentials are for "Desktop app" type

### Missing Dependencies
```bash
# Reinstall all dependencies
pip install --upgrade -r requirements.txt
```

### No Emails Found
- Check `SENDER_EMAIL` matches exactly
- Increase `SEARCH_DAYS` value
- Verify emails exist in Gmail with attachments

### Drive Upload Fails
- Verify Google Drive API is enabled
- Check OAuth scopes include Drive access
- Ensure sufficient Drive storage space

## Dependencies

- `google-auth-oauthlib` - Google OAuth authentication
- `google-auth-httplib2` - HTTP library for Google APIs
- `google-api-python-client` - Google API client
- `PyPDF2` - PDF processing
- `pdf2image` - Convert PDF to images
- `pyzbar` - Barcode scanning
- `Pillow` - Image processing
- `beautifulsoup4` - HTML parsing

## Security Notes

- Keep `client_secret_*.json` and `token.json` secure and private
- Never commit these files to public repositories
- OAuth tokens expire and auto-refresh when needed
- Scopes requested: Gmail (read), Gmail (send), Drive (file)

## License

Private project - All rights reserved

## Author

Ivan

---

*Last updated: March 2026*
