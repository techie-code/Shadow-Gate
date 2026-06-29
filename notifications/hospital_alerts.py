"""
ShadowGate Hospital Alert System
- P1/P2: Confidential email to Head + Slack to doctor after approval
- P3/P4: Direct Slack to doctor
- Meeting: Slack to both channels
- Conduct: Email to Head only
"""

import os
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
HEAD_OF_DEPT_EMAIL = os.getenv("HEAD_OF_DEPT_EMAIL", "")
SENIOR_EMAIL = os.getenv("SENIOR_EMAIL", "")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_PATIENT = os.getenv("SLACK_PATIENT_WEBHOOK", os.getenv("SLACK_WEBHOOK_URL", ""))
HOSPITAL_NAME = os.getenv("HOSPITAL_NAME", "City General Hospital")
APPROVAL_SERVER = os.getenv("APPROVAL_SERVER_URL", "http://localhost:5000")


def send_slack(webhook, text):
    """Send simple Slack message."""
    if not webhook:
        print(f"   Slack: no webhook configured")
        return False
    try:
        r = requests.post(webhook, json={"text": text}, timeout=10)
        print(f"   Slack sent: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"   Slack error: {e}")
        return False


def send_email(to_email, subject, html_body, cc=None):
    """Send HTML email."""
    if not SMTP_USER or not SMTP_PASS or not to_email:
        print(f"   Email: not configured (missing credentials)")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        if cc:
            msg["CC"] = cc
        msg.attach(MIMEText(html_body, "html"))
        recipients = [to_email] + ([cc] if cc else [])
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, recipients, msg.as_string())
        print(f"   Email sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"   Email: authentication failed - check app password")
        return False
    except Exception as e:
        print(f"   Email error: {e}")
        return False


def send_head_of_dept_alert(patient, aria_result, safe_result=None, guardian_result=None):
    """Send confidential email to Head with approval buttons."""
    patient_id = patient.get("patient_id", "unknown")
    patient_name = patient.get("name", "Unknown")
    priority = aria_result.get("priority", "P4")
    unknown_risks = aria_result.get("unknown_risks", [])
    doctor_name = guardian_result.get("doctor_name", "Not yet assigned") if guardian_result else "Not yet assigned"

    print(f"   Sending confidential email to Head of Department...")

    # Register with approval server
    try:
        requests.post(f"{APPROVAL_SERVER}/register", json={
            "patient_id": patient_id,
            "patient": patient,
            "priority": priority,
            "scenarios": aria_result.get("scenarios", {}),
            "assignment": guardian_result or {},
            "doctor_name": doctor_name,
            "approved": False
        }, timeout=2)
    except Exception:
        pass

    # Build approval buttons
    best_url = f"{APPROVAL_SERVER}/approve/{patient_id}/best_case"
    mod_url = f"{APPROVAL_SERVER}/approve/{patient_id}/moderate_case"
    worst_url = f"{APPROVAL_SERVER}/approve/{patient_id}/worst_case"
    meet_url = f"{APPROVAL_SERVER}/approve/{patient_id}/request_meeting"

    # Build risks HTML
    risks_html = ""
    for r in unknown_risks:
        sev = r.get("severity", "MEDIUM")
        color = "#ef4444" if sev == "HIGH" else "#f59e0b" if sev == "MEDIUM" else "#10b981"
        risks_html += f'<div style="padding:8px;background:#1a0a0a;border-left:3px solid {color};margin-bottom:6px;border-radius:0 4px 4px 0"><b style="color:{color}">[{sev}]</b> {r.get("risk","")}<br><small style="color:#64748b">{r.get("why_dangerous","")}</small></div>'

    html = f"""<html><body style="font-family:Arial,sans-serif;background:#080c10;padding:20px">
<div style="max-width:620px;margin:0 auto;background:#111;border-radius:12px;overflow:hidden">
<div style="background:#7f1d1d;padding:16px 24px">
  <div style="color:#fca5a5;font-size:11px;font-weight:bold;text-transform:uppercase">CONFIDENTIAL - ShadowGate Alert</div>
  <div style="color:#fff;font-size:18px;font-weight:700;margin-top:4px">Patient Requires Your Approval</div>
</div>
<div style="padding:24px;color:#e2e8f0">
  <table style="width:100%;background:#0d1117;border-radius:8px;border-collapse:collapse;margin-bottom:16px">
    <tr><td style="color:#888;padding:8px 12px">Patient</td><td style="color:#fff;font-weight:bold;padding:8px 12px">{patient_name}</td></tr>
    <tr><td style="color:#888;padding:8px 12px">Age</td><td style="color:#fff;padding:8px 12px">{patient.get("age")}</td></tr>
    <tr><td style="color:#888;padding:8px 12px">Priority</td><td style="color:#ef4444;font-weight:bold;padding:8px 12px">{priority}</td></tr>
    <tr><td style="color:#888;padding:8px 12px">Symptoms</td><td style="color:#fff;padding:8px 12px">{patient.get("symptoms")}</td></tr>
    <tr><td style="color:#888;padding:8px 12px">Doctor</td><td style="color:#fff;padding:8px 12px">{doctor_name}</td></tr>
    <tr><td style="color:#888;padding:8px 12px">Unknown Risks</td><td style="color:#ef4444;font-weight:bold;padding:8px 12px">{len(unknown_risks)} found</td></tr>
  </table>
  {"<div style='margin-bottom:16px'>" + risks_html + "</div>" if risks_html else ""}
  <p style="color:#94a3b8;font-size:13px;margin-bottom:16px">Please review and approve a treatment plan. Doctor will be notified only after your approval.</p>
  <table style="width:100%;border-collapse:collapse">
    <tr>
      <td style="padding:4px"><a href="{best_url}" style="display:block;background:#38A169;color:#fff;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold;font-size:12px">APPROVE<br>BEST CASE</a></td>
      <td style="padding:4px"><a href="{mod_url}" style="display:block;background:#DD6B20;color:#fff;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold;font-size:12px">APPROVE<br>MODERATE</a></td>
      <td style="padding:4px"><a href="{worst_url}" style="display:block;background:#E53E3E;color:#fff;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold;font-size:12px">APPROVE<br>WORST CASE</a></td>
      <td style="padding:4px"><a href="{meet_url}" style="display:block;background:#1a2744;color:#93c5fd;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold;font-size:12px;border:1px solid #1e3a5f">REQUEST<br>MEETING</a></td>
    </tr>
  </table>
  <p style="color:#475569;font-size:11px;text-align:center;margin-top:16px">ShadowGate | {HOSPITAL_NAME} | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
</div>
</div></body></html>"""

    subject = f"[CONFIDENTIAL] ShadowGate - {patient_name} - Priority {priority} - Approval Required"
    success = send_email(HEAD_OF_DEPT_EMAIL, subject, html)

    if not success:
        print(f"   Email simulation - subject: {subject}")

    return {
        "type": "head_alert",
        "patient_id": patient_id,
        "patient_name": patient_name,
        "priority": priority,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def send_doctor_slack_notification(patient, assignment, approved_scenario=None):
    """Send Slack to doctor after Head approves."""
    patient_name = patient.get("name", "Unknown")
    patient_id = patient.get("patient_id", "unknown")
    doctor_name = assignment.get("doctor_name", "Unknown") if assignment else "Unknown"
    priority = assignment.get("priority", "P4") if assignment else "P4"
    wait = assignment.get("estimated_wait_minutes", assignment.get("wait_minutes", 0)) if assignment else 0

    scenario_text = ""
    if approved_scenario:
        scenario_text = f" | Treatment: {approved_scenario.get('recommended_treatment', 'Standard protocol')}"

    text = f"PATIENT ASSIGNMENT: {patient_name} ({priority}) assigned to {doctor_name} | Wait: {wait} mins | Symptoms: {patient.get('symptoms', 'Unknown')}{scenario_text} | Treatment approved by Head of Department."

    print(f"   Sending Slack to doctor: {doctor_name}")
    send_slack(SLACK_PATIENT, text)

    return {
        "type": "doctor_notification",
        "patient_id": patient_id,
        "doctor": doctor_name,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def run_hospital_alerts(patients, hospital_result):
    """Main alert function."""
    print(f"\n{'='*55}")
    print(f" SHADOWGATE - HOSPITAL ALERT SYSTEM")
    print(f"{'='*55}")

    aria_results = hospital_result.get("aria", {}).get("results", [])
    safe_results = hospital_result.get("safe", {}).get("results", [])
    guardian_results = hospital_result.get("guardian", {}).get("results", [])

    alerts = []

    for i, patient in enumerate(patients):
        aria_result = aria_results[i] if i < len(aria_results) and aria_results[i] else {}
        safe_result = safe_results[i] if i < len(safe_results) and safe_results[i] else {}
        guardian_result = guardian_results[i] if i < len(guardian_results) and guardian_results[i] else {}

        if not aria_result:
            print(f"\n   Skipping {patient.get('name')} - no ARIA result")
            continue

        priority = aria_result.get("priority", "P4")
        unknown_risks = aria_result.get("unknown_risks", [])
        doctor = guardian_result.get("doctor_name", "Unknown") if guardian_result else "Unknown"

        print(f"\n Patient: {patient.get('name')} | Priority: {priority} | Doctor: {doctor}")

        if priority in ["P1", "P2"]:
            # Send email to Head, wait for approval
            print(f"   P1/P2 - sending to Head of Department")
            alert = send_head_of_dept_alert(patient, aria_result, safe_result, guardian_result)
            alerts.append(alert)
            print(f"   Doctor will be notified after Head approves")

        else:
            # P3/P4 - notify doctor directly via Slack
            print(f"   {priority} - notifying doctor directly via Slack")
            if guardian_result and doctor != "Unknown":
                slack_alert = send_doctor_slack_notification(patient, guardian_result)
                alerts.append(slack_alert)
            else:
                print(f"   No doctor assigned yet")

    print(f"\n Alerts sent: {len(alerts)}")
    print(f" P1/P2 emails: {sum(1 for a in alerts if a.get('type')=='head_alert')}")
    print(f" Doctor Slacks: {sum(1 for a in alerts if a.get('type')=='doctor_notification')}")

    return alerts
