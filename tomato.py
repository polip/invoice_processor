#!/usr/bin/env python3
"""
Script to process Tomato teleoperator invoices from Gmail:
- Fetch emails from Tomato
- Extract barcode from HTML email message
- Save PDF attachments to Google Drive
- Send notification
"""

import base64
import io
import logging

from bs4 import BeautifulSoup
from PIL import Image
from pyzbar.pyzbar import decode

from google_services import (
    authenticate,
    get_attachments,
    get_or_create_drive_folder,
    search_emails,
    send_notification,
    setup_logging,
    upload_to_drive,
)

# Configuration
SENDER_EMAIL = "moj.racun@tomato.com.hr"
SEARCH_DAYS = 10
DRIVE_FOLDER_NAME = "Tomato"

logger = logging.getLogger(__name__)


def get_inline_images(gmail_service, message_id: str):
    """Get all inline images (embedded in email body) from an email."""
    inline_images = {}

    try:
        message = (
            gmail_service.users().messages().get(userId="me", id=message_id).execute()
        )

        def extract_inline_parts(parts):
            for part in parts:
                if "parts" in part:
                    extract_inline_parts(part["parts"])

                headers = part.get("headers", [])
                content_id = None
                for header in headers:
                    if header["name"].lower() == "content-id":
                        content_id = header["value"].strip("<>")
                        break

                mime_type = part.get("mimeType", "")
                if content_id and mime_type.startswith("image/"):
                    if "attachmentId" in part.get("body", {}):
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
                    elif "data" in part.get("body", {}):
                        data = base64.urlsafe_b64decode(part["body"]["data"])
                    else:
                        continue

                    inline_images[content_id] = {"data": data, "mime_type": mime_type}

        if "parts" in message["payload"]:
            extract_inline_parts(message["payload"]["parts"])

        return inline_images
    except Exception as exc:
        logger.error("Error getting inline images from message %s: %s", message_id, exc)
        return {}


def get_email_body(gmail_service, message_id: str):
    """Extract HTML body from email message."""
    try:
        message = (
            gmail_service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        payload = message["payload"]

        def find_html_part(part):
            if part.get("mimeType") == "text/html":
                if "data" in part.get("body", {}):
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )

            if "parts" in part:
                for subpart in part["parts"]:
                    result = find_html_part(subpart)
                    if result:
                        return result

            return None

        if "parts" in payload:
            return find_html_part(payload)
        elif payload.get("mimeType") == "text/html":
            if "data" in payload.get("body", {}):
                return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        return None
    except Exception as exc:
        logger.error("Error extracting HTML body: %s", exc)
        return None


def main():
    setup_logging()
    logger.info("Authenticating...")
    gmail_service, drive_service = authenticate()

    logger.info("Getting/creating Drive folder...")
    folder_id = get_or_create_drive_folder(drive_service, DRIVE_FOLDER_NAME)

    logger.info("Searching for Tomato emails from last %d days...", SEARCH_DAYS)
    messages = search_emails(gmail_service, SENDER_EMAIL, SEARCH_DAYS)

    if not messages:
        logger.info("No emails found from Tomato")
        return

    logger.info("Found %d email(s)", len(messages))

    processed_files = []

    for msg in messages:
        logger.info("Processing message %s...", msg["id"])

        logger.info("  Extracting inline images...")
        inline_images = get_inline_images(gmail_service, msg["id"])
        logger.info("  Found %d inline image(s)", len(inline_images))

        logger.info("  Extracting HTML body...")
        html_body = get_email_body(gmail_service, msg["id"])

        barcode_cid = None
        if html_body:
            soup = BeautifulSoup(html_body, "html.parser")
            for img in soup.find_all("img"):
                alt = img.get("alt", "").lower()
                if (
                    "kod" in alt
                    or "plaćanje" in alt
                    or "payment" in alt
                    or "barcode" in alt
                ):
                    src = img.get("src", "")
                    if src.startswith("cid:"):
                        barcode_cid = src[4:]
                        logger.info(
                            '  Found payment barcode image: CID=%s, alt="%s"',
                            barcode_cid,
                            img.get("alt", ""),
                        )
                        break

        attachments = get_attachments(gmail_service, msg["id"])
        pdf_filename = None

        for attachment in attachments:
            if attachment["filename"].lower().endswith(".pdf"):
                logger.info("  Processing PDF: %s", attachment["filename"])
                pdf_filename = attachment["filename"]

                uploaded_file = upload_to_drive(
                    drive_service,
                    folder_id,
                    attachment["filename"],
                    attachment["data"],
                    check_duplicate=True,
                )

                if uploaded_file:
                    processed_files.append(
                        {
                            "filename": attachment["filename"],
                            "link": uploaded_file.get("webViewLink"),
                            "type": "PDF",
                            "status": "uploaded",
                        }
                    )
                    logger.info("  Uploaded PDF: %s", uploaded_file.get("webViewLink"))
                else:
                    processed_files.append(
                        {
                            "filename": attachment["filename"],
                            "link": None,
                            "type": "PDF",
                            "status": "skipped",
                        }
                    )

        if barcode_cid and barcode_cid in inline_images:
            if pdf_filename:
                base_name = pdf_filename.rsplit(".", 1)[0]
                barcode_filename = f"{base_name}_barcode.png"
            else:
                barcode_filename = f'Tomato_barcode_{msg["id"]}.png'

            logger.info("  Processing barcode image: %s", barcode_filename)

            uploaded_file = upload_to_drive(
                drive_service,
                folder_id,
                barcode_filename,
                inline_images[barcode_cid]["data"],
                check_duplicate=True,
            )

            if uploaded_file:
                processed_files.append(
                    {
                        "filename": barcode_filename,
                        "link": uploaded_file.get("webViewLink"),
                        "type": "Barcode Image",
                        "status": "uploaded",
                    }
                )
                logger.info("  Uploaded barcode: %s", uploaded_file.get("webViewLink"))
            else:
                processed_files.append(
                    {
                        "filename": barcode_filename,
                        "link": None,
                        "type": "Barcode Image",
                        "status": "skipped",
                    }
                )
        elif barcode_cid:
            logger.warning(
                "  Barcode CID %s not found in inline images", barcode_cid
            )
        else:
            logger.info("  No barcode image found in email")

    if processed_files:
        uploaded_count = sum(1 for pf in processed_files if pf["status"] == "uploaded")
        skipped_count = sum(1 for pf in processed_files if pf["status"] == "skipped")

        notification_body = f"Tomato Invoice Processing Summary:\n"
        notification_body += (
            f"Uploaded: {uploaded_count}, Skipped (already exists): {skipped_count}\n\n"
        )

        for pf in processed_files:
            notification_body += f'File: {pf["filename"]} ({pf["type"]})\n'
            if pf["status"] == "uploaded":
                notification_body += "Status: Uploaded\n"
                notification_body += f'Link: {pf["link"]}\n'
            else:
                notification_body += "Status: Skipped (already exists)\n"
            notification_body += "\n"

        logger.info("\n%s", notification_body)
        send_notification(
            gmail_service, "Tomato Invoice Processing Complete", notification_body
        )

    logger.info("Processed %d file(s) successfully", len(processed_files))


if __name__ == "__main__":
    main()
