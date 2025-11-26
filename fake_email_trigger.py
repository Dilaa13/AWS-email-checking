from __future__ import annotations
import json
import boto3

AWS_REGION = "eu-north-1"
LAMBDA_NAME = "email-router-entry"

lambda_client = boto3.client("lambda", region_name=AWS_REGION)

def send_fake_email():
    fake_event = {
        "from": "client@example.com",
        "subject": "Need help with AI project",
        "body": "Hi, I want to know the current status of the AI model."
    }

    print("Sending this event to Lambda:")
    print(json.dumps(fake_event, indent=2))

    response = lambda_client.invoke(
        FunctionName=LAMBDA_NAME,
        InvocationType="Event",  # async
        Payload=json.dumps(fake_event)
    )

    print("Invoke response:")
    print(response)

if __name__ == "__main__":
    send_fake_email()
