import json
from imap_tools import MailBox, AND
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib
from fastapi import UploadFile
import io
from app.core.config import get_settings
from .packing_list_service import PackingListService
import ssl


class EmailService:
    def __init__(self):
        settings = get_settings()
        self.email = settings.EMAIL_ADDRESS
        self.password = settings.EMAIL_PASSWORD.get_secret_value()
        self.imap_server = settings.IMAP_SERVER
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.packing_list_service = PackingListService()

    async def process_attachments(self, msg) -> dict:
        """Categorizes email attachments into required files."""
        files = {"partie_files": [], "wahrheit_file": None, "template_file": None}

        print("\n=== Processing Attachments ===")
        print(f"Number of attachments found: {len(msg.attachments)}")

        for att in msg.attachments:
            print(f"\nProcessing attachment: {att.filename}")
            # Convert attachment to UploadFile
            file = UploadFile(filename=att.filename, file=io.BytesIO(att.payload))

            if att.filename.startswith("Partie"):
                files["partie_files"].append(file)
                print(f"Added as Partie file: {att.filename}")
            elif "Wahrheit" in att.filename:
                files["wahrheit_file"] = file
                print(f"Added as Wahrheit file: {att.filename}")
                # Debug Wahrheit content
                content = att.payload.decode("utf-8")
                print("\nWahrheit file content preview (first 500 chars):")
                print(content[:500])
            elif "template" in att.filename:
                files["template_file"] = file
                print(f"Added as template file: {att.filename}")

        print("\nFinal files status:")
        print(f"Partie files: {len(files['partie_files'])}")
        print(f"Wahrheit file: {'Present' if files['wahrheit_file'] else 'Missing'}")
        print(f"Template file: {'Present' if files['template_file'] else 'Missing'}")

        return files

    async def send_response(self, to_email: str, subject: str, csv_content: str):
        """Sends email with generated CSV as attachment."""
        try:
            print(f"Preparing email to: {to_email}")

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

            print("Starting SMTP operations with SSL...")
            with smtplib.SMTP_SSL(self.smtp_server, 465, context=context) as server:
                print("Connected to SMTP server, logging in...")
                server.login(self.email, self.password)
                print("Sending message...")
                server.send_message(msg)
                print("Message sent successfully!")

        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            raise ValueError(f"Email sending failed: {str(e)}")

    async def process_rohdex_emails(self) -> dict:
        """Main method to process emails and generate packing lists."""
        stats = {"emails_processed": 0, "files_generated": 0, "responses_sent": 0}

        if not self.email or not self.password:
            raise ValueError("Email credentials not configured")

        try:
            with MailBox(self.imap_server).login(self.email, self.password) as mailbox:
                # Fetch last unread email with specific subject
                messages = list(
                    mailbox.fetch(AND(subject="Test - Rohdex 2"), limit=1, reverse=True)
                )

                # Print message subject
                for msg in messages:
                    print(f"Found message with subject: {msg.subject}")

                if not messages:
                    raise ValueError(
                        "No unread emails found with subject 'Test - Rohdex'"
                    )

                for msg in messages:
                    try:
                        # Process attachments
                        print(f"Processing email with subject: {msg.subject}")
                        files = await self.process_attachments(msg)
                        print("Files", files)

                        # Validate required files
                        if not files["partie_files"]:
                            raise ValueError(
                                f"No Partie files found in email {msg.uid}"
                            )
                        if not files["wahrheit_file"]:
                            raise ValueError(
                                f"No Wahrheitsdatei found in email {msg.uid}"
                            )
                        print("Wahrheitsdatei content: ", files["wahrheit_file"])
                        if not files["template_file"]:
                            raise ValueError(
                                f"No template file found in email {msg.uid}"
                            )

                        # Generate packing list
                        print("Generating packing list...")
                        result = await self.packing_list_service.generate(
                            partie_files=files["partie_files"],
                            wahrheit_file=files["wahrheit_file"],
                            template_file=files["template_file"],
                        )
                        print("Packing list generated")

                        # Send response
                        print("Sending response...")
                        await self.send_response(msg.from_, msg.subject, result)
                        print("Response sent")

                        # Update stats
                        stats["files_generated"] += 1
                        stats["responses_sent"] += 1

                        # Mark as processed
                        mailbox.flag(msg.uid, "SEEN", True)
                        stats["emails_processed"] += 1

                    except Exception as e:
                        # Log error but continue processing other emails
                        print(f"Error processing email {msg.uid}: {str(e)}")
                        continue

        except Exception as e:
            raise ValueError(f"Email processing failed: {str(e)}")

        return stats
