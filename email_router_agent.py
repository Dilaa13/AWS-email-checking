from __future__ import annotations

import os
from email.message import EmailMessage

import boto3
from strands import Agent, tool
from excel_lookup import get_supervisor_email  # import the helper

SES_REGION = os.environ.get("SES_REGION", "eu-north-1")
FROM_ADDRESS = os.environ.get("FROM_ADDRESS", "no-reply@your-domain.com")

ses_client = boto3.client("ses", region_name=SES_REGION)


@tool
def notify_supervisor(
    project_sheet: str,
    purpose_summary: str,
    original_sender: str,
    original_subject: str,
) -> str:
    """
    Look up the supervisor email for the given project in the Excel workbook
    and send a notification email using SES.
    """

    supervisor_email = get_supervisor_email(project_sheet)

    if not supervisor_email:
        return (
            f"Could not find supervisor email for sheet '{project_sheet}'. "
            f"No email sent."
        )

    subject = f"[Project: {project_sheet}] New email from {original_sender}"
    body = (
        f"Hello,\n\n"
        f"You have a new email related to project '{project_sheet}'.\n\n"
        f"From: {original_sender}\n"
        f"Original subject: {original_subject}\n\n"
        f"Main purpose of the email:\n"
        f"{purpose_summary}\n\n"
        f"Please check the original email in your inbox.\n\n"
        f"Regards,\n"
        f"Email routing agent"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_ADDRESS
    msg["To"] = supervisor_email
    msg.set_content(body)

    ses_client.send_raw_email(
        Source=FROM_ADDRESS,
        Destinations=[supervisor_email],
        RawMessage={"Data": msg.as_bytes()},
    )

    return f"Notification sent to {supervisor_email} for project {project_sheet}."
