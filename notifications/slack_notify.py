"""
ShadowGate - Slack Notifications
Sends formatted deployment and alert notifications to Slack.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def send_deployment_notification(deployment_report, guardian_reports):
    """Send deployment readiness notification to Slack."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url or webhook_url == "your_slack_webhook_url_here":
        print(f"   📲 Slack: No webhook configured — skipping notification")
        print(f"   💡 Add SLACK_WEBHOOK_URL to .env to enable Slack notifications")
        return False

    signal = deployment_report.get("signal", "UNKNOWN")
    score = deployment_report.get("overall_confidence", 0)
    blockers = deployment_report.get("blockers", [])

    # Build message
    if signal == "GREEN":
        emoji = "✅"
        color = "#36a64f"
        title = "ShadowGate — Deployment Approved"
    else:
        emoji = "🚨"
        color = "#ff0000"
        title = "ShadowGate — Deployment Blocked"

    # Individual scores text
    scores_text = "\n".join([
        f"• {name.replace('_', ' ').title()}: {score}/100"
        for name, score in deployment_report.get("individual_scores", {}).items()
    ])

    # Blockers text
    blockers_text = "\n".join([
        f"• {b['automation'].replace('_', ' ').title()}: {b['score']}/100"
        for b in blockers
    ]) if blockers else "None"

    payload = {
        "attachments": [
            {
                "color": color,
                "title": f"{emoji} {title}",
                "fields": [
                    {
                        "title": "Overall Confidence",
                        "value": f"{score}/100",
                        "short": True
                    },
                    {
                        "title": "Signal",
                        "value": signal,
                        "short": True
                    },
                    {
                        "title": "Automation Scores",
                        "value": scores_text,
                        "short": False
                    },
                    {
                        "title": "Blockers",
                        "value": blockers_text,
                        "short": False
                    },
                    {
                        "title": "AI Summary",
                        "value": deployment_report.get("ai_summary", "")[:200],
                        "short": False
                    }
                ],
                "footer": f"ShadowGate | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png"
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"   📲 Slack notification sent successfully!")
            return True
        else:
            print(f"   ⚠️  Slack notification failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ⚠️  Slack notification error: {e}")
        return False


def send_chaos_alert(automation_name, chaos_report):
    """Send chaos injection alert to Slack."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url or webhook_url == "your_slack_webhook_url_here":
        return False

    injections = chaos_report.get("successful_injections", 0)
    payload = {
        "text": f"💥 *ShadowGate Chaos Alert* — {automation_name.replace('_', ' ').title()}\n"
                f"Injected {injections} failure(s) into automation for testing.\n"
                f"Monitor results carefully."
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


if __name__ == "__main__":
    print("Testing Slack notification...")
    test_report = {
        "signal": "GREEN",
        "overall_confidence": 94.5,
        "blockers": [],
        "warnings": [],
        "individual_scores": {
            "loan_processing": 96,
            "fraud_detection": 94,
            "account_onboarding": 93
        },
        "ai_summary": "All automations passed with high confidence. Safe to deploy."
    }
    send_deployment_notification(test_report, {})
