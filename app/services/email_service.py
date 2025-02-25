import json
import threading
import time
import asyncio
from functools import wraps
from imap_tools import MailBox, AND
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib
from fastapi import UploadFile
import io
from app.core.config import get_settings
from app.core.logger import LoggerSingleton
from .packing_list_service import PackingListService
import ssl
from typing import Optional, Dict, List, Callable, Any

# Get logger from singleton
logger = LoggerSingleton.get_logger()


def run_async(async_func):
    """Decorator to run async functions in sync context"""

    @wraps(async_func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(async_func(*args, **kwargs))
            return result
        finally:
            loop.close()

    return wrapper


class EmailService:
    def __init__(self):
        settings = get_settings()
        self.email = settings.EMAIL_ADDRESS
        self.password = settings.EMAIL_PASSWORD.get_secret_value()
        self.imap_server = settings.IMAP_SERVER
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.packing_list_service = PackingListService()

        # Template configuration
        self.template_path = settings.TEMPLATE_PACKING_LIST_PATH
        self.template_file = None
        self._load_template()  # Load template at initialization

        # Polling configuration
        self.polling_enabled = settings.EMAIL_POLLING_ENABLED
        self.poll_interval = settings.EMAIL_POLLING_INTERVAL
        self.label_filter = settings.EMAIL_LABEL_FILTER
        self.max_fetch = settings.EMAIL_MAX_FETCH

        # Polling control
        self.polling = False
        self.poll_thread: Optional[threading.Thread] = None

    def _load_template(self):
        """Load the template file from local path"""
        try:
            with open(self.template_path, "r") as f:
                content = f.read()
                # Convert to UploadFile format for compatibility
                self.template_file = UploadFile(
                    filename="template_packing_list.csv",
                    file=io.BytesIO(content.encode()),
                )
            logger.info(f"Template loaded from {self.template_path}")
        except Exception as e:
            logger.error(f"Failed to load template: {str(e)}")
            raise ValueError(f"Template loading failed: {str(e)}")

    def start_polling(self):
        """Start the background polling for emails"""
        if self.polling or not self.polling_enabled:
            return False

        self.polling = True
        self.poll_thread = threading.Thread(target=self._polling_worker, daemon=True)
        self.poll_thread.start()

        logger.info(
            f"Email polling started with {self.poll_interval}s interval for label '{self.label_filter}'"
        )
        return True

    def stop_polling(self):
        """Stop the background polling for emails"""
        if not self.polling:
            return False

        self.polling = False
        if self.poll_thread:
            self.poll_thread.join(timeout=10)
            self.poll_thread = None

        logger.info("Email polling stopped")
        return True

    def _polling_worker(self):
        """Worker function that runs in background thread"""
        logger.info(
            f"Email polling worker started - checking for emails with label '{self.label_filter}'"
        )

        while self.polling:
            try:
                # Process emails with the specified label
                result = self.process_labeled_emails()
                logger.debug(
                    f"Poll cycle: Processed {result['emails_processed']} emails"
                )

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error in email polling: {error_msg}")

            # Sleep until next check
            time.sleep(self.poll_interval)

    def _get_mailbox_connection(self):
        """Returns a context manager for mailbox connection"""
        if not self.email or not self.password:
            raise ValueError("Email credentials not configured")
        return MailBox(self.imap_server).login(self.email, self.password)

    def _fetch_messages(self, mailbox, criteria=None, limit=None):
        """Fetch messages from mailbox with given criteria"""
        if criteria is None:
            criteria = AND(seen=False, subject="ROHDEX")
        if limit is None:
            limit = self.max_fetch
        return list(mailbox.fetch(criteria, limit=limit))

    def _mark_as_read(self, mailbox, msg):
        """Mark a message as read"""
        mailbox.flag(msg.uid, "SEEN", True)

    def process_labeled_emails(self) -> Dict[str, int]:
        """Process all unread emails with the specified Gmail label"""
        stats = {"emails_processed": 0, "files_generated": 0}

        try:
            with self._get_mailbox_connection() as mailbox:
                messages = self._fetch_messages(mailbox)
                logger.info(
                    f"Found {len(messages)} unread messages with subject 'ROHDEX'"
                )

                for msg in messages:
                    try:
                        result = self._process_single_message(mailbox, msg)
                        if result:
                            stats["emails_processed"] += 1
                            stats["files_generated"] += 1
                    except Exception as e:
                        logger.error(f"Error processing email {msg.uid}: {str(e)}")
                        self._mark_as_read(mailbox, msg)
        except Exception as e:
            raise ValueError(f"Email processing failed: {str(e)}")

        return stats

    def _process_single_message(self, mailbox, msg):
        """Process a single email message"""
        logger.info(f"Processing email from: {msg.from_}, subject: {msg.subject}")

        # Process attachments
        files = self.process_attachments(msg)

        # Skip emails without required attachments (template no longer required)
        if not files.get("partie_files") or not files.get("wahrheit_file"):
            logger.warning(f"Skipping email with missing attachments, marking as read")
            self._mark_as_read(mailbox, msg)
            return False

        # Generate packing list using local template
        logger.info(f"Generating packing list for message {msg.uid}...")
        result = self._generate_packing_list_sync(
            partie_files=files["partie_files"],
            wahrheit_file=files["wahrheit_file"],
            template_file=self.template_file,  # Use local template
        )

        # Send response
        logger.info("Sending response...")
        self._send_response_sync(msg.from_, msg.subject, result)
        logger.info("Response sent")

        # Mark as processed
        self._mark_as_read(mailbox, msg)
        return True

    def process_attachments(self, msg) -> dict:
        """Process attachments from an email message"""
        files = {"partie_files": [], "wahrheit_file": None, "template_file": None}

        logger.debug(f"Processing {len(msg.attachments)} attachments")

        for att in msg.attachments:
            # Convert attachment to UploadFile
            file = UploadFile(filename=att.filename, file=io.BytesIO(att.payload))

            if att.filename.startswith("Partie"):
                files["partie_files"].append(file)
                logger.debug(f"Added as Partie file: {att.filename}")
            elif "Wahrheit" in att.filename:
                files["wahrheit_file"] = file
                logger.debug(f"Added as Wahrheit file: {att.filename}")
            elif "template" in att.filename:
                files["template_file"] = file
                logger.debug(f"Added as template file: {att.filename}")

        # Log summary of processed files
        logger.debug(
            f"Processed attachments: {len(files['partie_files'])} Partie files, "
            f"Wahrheit: {'Present' if files['wahrheit_file'] else 'Missing'}, "
            f"Template: {'Present' if files['template_file'] else 'Missing'}"
        )

        return files

    @run_async
    async def _generate_packing_list_async(
        self, partie_files, wahrheit_file, template_file
    ):
        """Generate packing list using the packing list service"""
        return await self.packing_list_service.generate(
            partie_files=partie_files,
            wahrheit_file=wahrheit_file,
            template_file=template_file,
        )

    def _generate_packing_list_sync(self, partie_files, wahrheit_file, template_file):
        """Synchronous wrapper for packing_list_service.generate"""
        return self._generate_packing_list_async(
            partie_files, wahrheit_file, template_file
        )

    @run_async
    async def _send_response_async(self, to_email, subject, csv_content):
        """Send email with generated CSV as attachment"""
        try:
            logger.debug(f"Preparing email to: {to_email}")

            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = to_email
            msg["Subject"] = f"Re: {subject}"

            # Add body
            msg.attach(
                MIMEText("Please find the generated packing list attached.", "plain")
            )

            # Attach CSV
            attachment = MIMEApplication(csv_content.encode("utf-8"))
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename="generated_packing_list.csv",
            )
            msg.attach(attachment)

            # Create a secure SSL/TLS context
            context = ssl.create_default_context()

            logger.debug("Starting SMTP operations with SSL...")
            with smtplib.SMTP_SSL(self.smtp_server, 465, context=context) as server:
                server.login(self.email, self.password)
                server.send_message(msg)
                logger.debug("Message sent successfully")

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise ValueError(f"Email sending failed: {str(e)}")

    def _send_response_sync(self, to_email, subject, csv_content):
        """Synchronous wrapper for send_response"""
        return self._send_response_async(to_email, subject, csv_content)

    async def process_rohdex_emails(self) -> dict:
        """Process emails with specific subject for Rohdex"""
        stats = {"emails_processed": 0, "files_generated": 0, "responses_sent": 0}

        try:
            with self._get_mailbox_connection() as mailbox:
                # Fetch emails with specific subject
                messages = self._fetch_messages(
                    mailbox, criteria=AND(subject="Test - Rohdex 2"), limit=1
                )

                if not messages:
                    raise ValueError(
                        "No unread emails found with subject 'Test - Rohdex'"
                    )

                for msg in messages:
                    logger.info(f"Found message with subject: {msg.subject}")
                    try:
                        # Process message
                        files = await self.process_attachments_async(msg)

                        # Validate required files (template no longer required)
                        if not files["partie_files"]:
                            raise ValueError(
                                f"No Partie files found in email {msg.uid}"
                            )
                        if not files["wahrheit_file"]:
                            raise ValueError(
                                f"No Wahrheitsdatei found in email {msg.uid}"
                            )

                        # Generate packing list using local template
                        logger.info("Generating packing list...")
                        result = await self.packing_list_service.generate(
                            partie_files=files["partie_files"],
                            wahrheit_file=files["wahrheit_file"],
                            template_file=self.template_file,  # Use local template
                        )
                        logger.info("Packing list generated")

                        # Send response
                        logger.info("Sending response...")
                        await self._send_response_async(msg.from_, msg.subject, result)
                        logger.info("Response sent")

                        # Update stats
                        stats["files_generated"] += 1
                        stats["responses_sent"] += 1
                        stats["emails_processed"] += 1

                        # Mark as processed
                        self._mark_as_read(mailbox, msg)

                    except Exception as e:
                        logger.error(f"Error processing email {msg.uid}: {str(e)}")
                        continue

        except Exception as e:
            raise ValueError(f"Email processing failed: {str(e)}")

        return stats

    @run_async
    async def process_attachments_async(self, msg):
        """Async version of process_attachments"""
        return self.process_attachments(msg)
