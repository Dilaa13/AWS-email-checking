from __future__ import annotations

import email
import imaplib
import json
import os
import time
from email.message import Message
from typing import List

import boto3


# ------------- Configuration -------------

# Gmail IMAP settings
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# Read these from environment variables for safety
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")  # App password, not your normal one

# AWS settings
AWS_REGION = os.environ.get("AWS_REGION", "eu-north-1")
LAMBDA_FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION_NAME", "email-router-entry")

# How often to check for new mail (seconds)
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "15"))

lambda_client = boto3.client("lambda", region_name=AWS_REGION)


# ------------- Helper functions -------------

def connect_to_gmail():
    """Connect to Gmail via IMAP and select the INBOX."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set as environment variables.")

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    mail.select("INBOX")
    return mail


def fetch_unseen_messages(mail) -> List[Message]:
    """
    Return a list of email.message.Message objects for all UNSEEN emails.
    After this, they will still be marked as unseen in Gmail; we just read them.
    """

    status, data = mail.search(None, "UNSEEN")
    if status != "OK":
        print("Failed to search UNSEEN messages:", status, data)
        return []

    msg_ids = data[0].split()
    messages: List[Message] = []

    for msg_id in msg_ids:
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK":
            print(f"Failed to fetch message {msg_id}: {status}")
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        messages.append(msg)

    return messages


def extract_email_contents(msg: Message):
    """Return a dict with from, subject, and plain-text body."""
    from_addr = msg.get("From", "")
    subject = msg.get("Subject", "")

    # Try to get a plain text body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                charset = part.get_content_charset() or "utf-8"
                body_bytes = part.get_payload(decode=True) or b""
                body = body_bytes.decode(charset, errors="ignore")
                break
    else:
        charset = msg.get_content_charset() or "utf-8"
        body_bytes = msg.get_payload(decode=True) or b""
        body = body_bytes.decode(charset, errors="ignore")

    return {
        "from": from_addr,
        "subject": subject,
        "body": body,
    }


def notify_aws(email_payload: dict):
    """
    Inform AWS by calling a Lambda function.
    The Lambda will later use the Strands framework to classify the email.
    """

    print("Sending email payload to AWS Lambda...")

    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType="Event",  # async
        Payload=json.dumps(email_payload).encode("utf-8"),
    )

    # We just log the response metadata
    print("Invoke response:", response.get("StatusCode"), response.get("RequestId", ""))


# ------------- Main loop -------------

def main():
    print("Connecting to Gmail...")
    mail = connect_to_gmail()
    print("Connected. Listening for new emails...")

    try:
        while True:
            messages = fetch_unseen_messages(mail)

            if messages:
                print(f"Found {len(messages)} new message(s).")
            for msg in messages:
                email_data = extract_email_contents(msg)
                print("New email from:", email_data["from"], "| Subject:", email_data["subject"])

                # Inform AWS
                notify_aws(email_data)

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("Stopping listener (Ctrl+C pressed).")
    finally:
        mail.close()
        mail.logout()


if __name__ == "__main__":
    main()
