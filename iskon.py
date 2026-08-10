#!/usr/bin/env python3
"""
Script to process Iskon teleoperator invoices from Gmail:
- Fetch emails from Iskon
- Save PDF and PNG attachments to Google Drive
- Send notification
"""

import logging

from google_services import (
    authenticate,
    get_or_create_drive_folder,
    get_attachments,
    search_emails,
    send_notification,
    setup_logging,
    upload_to_drive,
)

# Configuration
SENDER_EMAIL = "e-racun@iskon.hr"
SEARCH_DAYS = 10
DRIVE_FOLDER_NAME = "Iskon"

logger = logging.getLogger(__name__)


def main():
    setup_logging()
    logger.info("Authenticating...")
    gmail_service, drive_service = authenticate()

    logger.info("Getting/creating Drive folder...")
    folder_id = get_or_create_drive_folder(drive_service, DRIVE_FOLDER_NAME)

    logger.info("Searching for Iskon emails from last %d days...", SEARCH_DAYS)
    messages = search_emails(gmail_service, SENDER_EMAIL, SEARCH_DAYS)

    if not messages:
        logger.info("No emails found from Iskon")
        return

    logger.info("Found %d email(s)", len(messages))

    processed_files = []

    for msg in messages:
        logger.info("Processing message %s...", msg["id"])
        attachments = get_attachments(gmail_service, msg["id"])

        for attachment in attachments:
            logger.info("  Processing attachment: %s", attachment["filename"])

            logger.info("  Uploading to Google Drive...")
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
                    }
                )
                logger.info("  Uploaded: %s", uploaded_file.get("webViewLink"))

    # Send notification
    if processed_files:
        notification_body = "Iskon Invoice Processing Summary:\n\n"
        for pf in processed_files:
            notification_body += f'File: {pf["filename"]}\n'
            notification_body += f'Link: {pf["link"]}\n\n'

        logger.info("\n%s", notification_body)
        send_notification(
            gmail_service, "Iskon Invoice Processing Complete", notification_body
        )

    logger.info("Processed %d file(s) successfully", len(processed_files))


if __name__ == "__main__":
    main()
