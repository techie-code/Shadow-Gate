"""
Test Slack webhook directly.
Run: python test_slack.py
"""

import os
import requests
from dotenv import load_dotenv
load_dotenv()

patient_webhook = os.getenv("SLACK_PATIENT_WEBHOOK", "")
it_webhook = os.getenv("SLACK_WEBHOOK_URL", "")

print(f"SLACK_PATIENT_WEBHOOK: {'SET' if patient_webhook else 'NOT SET'}")
print(f"SLACK_WEBHOOK_URL:     {'SET' if it_webhook else 'NOT SET'}")

if not patient_webhook and not it_webhook:
    print("\nERROR: No Slack webhook configured in .env")
    exit(1)

webhook = patient_webhook or it_webhook
print(f"\nTesting webhook: {webhook[:40]}...")

msg = {
    "text": "ShadowGate Test - Meeting Requested",
    "attachments": [{
        "color": "#1a56db",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Test - Meeting Requested"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This is a test message from ShadowGate. If you see this, Slack is working!"
                }
            }
        ]
    }]
}

try:
    response = requests.post(webhook, json=msg, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 200:
        print("\nSUCCESS - Check your Slack channel!")
    else:
        print("\nFAILED - Check webhook URL in .env")
except Exception as e:
    print(f"\nERROR: {e}")
