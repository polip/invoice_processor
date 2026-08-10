"""Shared Google services helpers for invoice processors."""

import base64
import io
import logging
import os
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file",
]

CLIENT_SECRET_FILE = (
    "client_secret_544079871095-7eo15ghsvks1u43urcft84afblheu732"
    ".apps.googleusercontent.com.json"
)

logger = logging.getLogger(__name__)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging for all processors."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def authenticate() -> tuple:
    """Authenticate and return Gmail and Drive service objects."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("OAuth credentials refreshed")
            except Exception as exc:
                logger.error("Failed to refresh credentials: %s", exc)
                raise
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"Client secret file not found: {CLIENT_SECRET_FILE}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("OAuth flow completed interactively")

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    gmail_service = build("gmail", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    return gmail_service, drive_service


def search_emails(gmail_service, sender_email: str, days_back: int = 10):
    """Search for emails from sender within the specified time period with pagination."""
    date_filter = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    query = f"from:{sender_email} after:{date_filter} has:attachment"

    messages = []
    next_page_token = None

    try:
        while True:
            params = {"userId": "me", "q": query}
            if next_page_token:
                params["pageToken"] = next_page_token

            results = gmail_service.users().messages().list(**params).execute()
            batch = results.get("messages", [])
            messages.extend(batch)
            logger.info("Fetched %d messages (batch)", len(batch))

            next_page_token = results.get("nextPageToken")
            if not next_page_token:
                break

        return messages
    except HttpError as exc:
        logger.error("Error searching emails: %s", exc)
        return []


def get_attachments(gmail_service, message_id: str):
    """Get all PDF and PNG attachments from an email."""
    attachments = []

    try:
        message = (
            gmail_service.users().messages().get(userId="me", id=message_id).execute()
        )

        if "parts" in message["payload"]:
            for part in message["payload"]["parts"]:
                filename_lower = part["filename"].lower() if part["filename"] else ""
                if filename_lower.endswith((".pdf", ".png")):
                    if "attachmentId" in part["body"]:
                        attachment = (
                            gmail_service.users()
                            .messages()
                            .attachments()
                            .get(
                                userId="me",
                                messageId=message_id,
                                id=part["body"]["attachmentId"],
                            )
                            .execute()
                        )

                        data = base64.urlsafe_b64decode(attachment["data"])
                        attachments.append({"filename": part["filename"], "data": data})

        return attachments
    except HttpError as exc:
        logger.error("Error getting attachments from message %s: %s", message_id, exc)
        return []


def get_or_create_drive_folder(drive_service, folder_name: str) -> str:
    """Get or create a folder in Google Drive."""
    safe_name = folder_name.replace("'", "\\'")
    query = (
        f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    try:
        results = (
            drive_service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )
        folders = results.get("files", [])

        if folders:
            return folders[0]["id"]

        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = (
            drive_service.files().create(body=folder_metadata, fields="id").execute()
        )
        logger.info("Created Drive folder '%s' (%s)", folder_name, folder["id"])
        return folder["id"]
    except HttpError as exc:
        logger.error("Error managing Drive folder '%s': %s", folder_name, exc)
        raise


def file_exists_in_drive(drive_service, folder_id: str, filename: str) -> bool:
    """Check if a file with the given name already exists in the Drive folder."""
    safe_name = filename.replace("'", "\\'")
    query = f"name='{safe_name}' and '{folder_id}' in parents and trashed=false"
    try:
        results = (
            drive_service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )
        files = results.get("files", [])
        return len(files) > 0
    except HttpError as exc:
        logger.error("Error checking for existing file '%s': %s", filename, exc)
        return False


def upload_to_drive(
    drive_service,
    folder_id: str,
    filename: str,
    file_data: bytes,
    description: str | None = None,
    check_duplicate: bool = True,
):
    """Upload file to Google Drive if it doesn't already exist."""
    if check_duplicate and file_exists_in_drive(drive_service, folder_id, filename):
        logger.info("File already exists in Drive, skipping: %s", filename)
        return None

    if filename.lower().endswith(".png"):
        mimetype = "image/png"
    else:
        mimetype = "application/pdf"

    file_metadata = {"name": filename, "parents": [folder_id]}
    if description:
        file_metadata["description"] = description

    media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype=mimetype, resumable=True)

    try:
        file = (
            drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )
        logger.info("Uploaded '%s' to Drive (%s)", filename, file.get("webViewLink"))
        return file
    except HttpError as exc:
        logger.error("Error uploading file '%s' to Drive: %s", filename, exc)
        return None


def send_notification(gmail_service, subject: str, body: str) -> None:
    """Send an email notification to yourself."""
    from email.mime.text import MIMEText

    try:
        profile = gmail_service.users().getProfile(userId="me").execute()
        sender_email = profile["emailAddress"]

        message = MIMEText(body)
        message["to"] = sender_email
        message["from"] = sender_email
        message["subject"] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        gmail_service.users().messages().send(
            userId="me", body={"raw": raw_message}
        ).execute()
        logger.info("Notification sent: %s", subject)
    except HttpError as exc:
        logger.error("Error sending notification: %s", exc)
