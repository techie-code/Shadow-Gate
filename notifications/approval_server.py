"""
ShadowGate Approval Server
Receives Head of Department button clicks.
Sends Slack to doctor after approval.
"""

import os
import time
import threading
import requests
import smtplib
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
pending_approvals = {}

REMINDER_WAIT = int(os.getenv("REMINDER_WAIT_SECONDS", "300"))
ESCALATION_WAIT = int(os.getenv("ESCALATION_WAIT_SECONDS", "600"))
APPROVAL_SERVER = os.getenv("APPROVAL_SERVER_URL", "http://localhost:5000")
HOSPITAL_NAME = os.getenv("HOSPITAL_NAME", "City General Hospital")
SENIOR_EMAIL = os.getenv("SENIOR_EMAIL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
HEAD_EMAIL = os.getenv("HEAD_OF_DEPT_EMAIL", "")


def slack(webhook, text):
    """Send Slack message."""
    if not webhook:
        return
    try:
        r = requests.post(webhook, json={"text": text}, timeout=10)
        print(f"   Slack {r.status_code}: {text[:60]}")
    except Exception as e:
        print(f"   Slack error: {e}")


def send_html_email(to, subject, html, cc=None):
    """Send HTML email."""
    if not SMTP_USER or not SMTP_PASS or not to:
        print(f"   Email not configured - subject: {subject[:50]}")
        return False
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to
        if cc:
            msg["CC"] = cc
        msg.attach(MIMEText(html, "html"))
        recipients = [to] + ([cc] if cc else [])
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, recipients, msg.as_string())
        print(f"   Email sent to {to}")
        return True
    except Exception as e:
        print(f"   Email error: {e}")
        return False


@app.route("/")
def home():
    return f"<h2>ShadowGate Approval Server</h2><p>Pending: {len(pending_approvals)}</p>"


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    pid = data.get("patient_id")
    if pid:
        data["registered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["approved"] = False
        data["reminder_sent"] = False
        data["escalated"] = False
        pending_approvals[pid] = data
        # Start reminder timer
        t = threading.Thread(target=reminder_loop, args=(pid,), daemon=True)
        t.start()
        print(f"   Registered {pid} - reminder in {REMINDER_WAIT//60} mins")
    return jsonify({"status": "ok"})


@app.route("/approve/<patient_id>/<scenario>")
def approve(patient_id, scenario):
    data = pending_approvals.get(patient_id)

    if not data:
        return "<h2 style='color:#f59e0b'>Link expired or not found.</h2>"

    patient = data.get("patient", {})
    patient_name = patient.get("name", patient_id)
    priority = data.get("priority", "P4")
    doctor_name = data.get("doctor_name", data.get("assignment", {}).get("doctor_name", "Unknown"))
    scenario_label = scenario.replace("_", " ").title()

    # Meeting request
    if scenario == "request_meeting":
        pending_approvals[patient_id]["meeting_requested"] = True
        pending_approvals[patient_id]["meeting_requested_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        patient_webhook = os.getenv("SLACK_PATIENT_WEBHOOK", "")
        it_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        msg = f"MEETING REQUESTED: Patient {patient_name} ({priority}) - Head of Department requested meeting with Chief Doctor before approving treatment. Doctor: {doctor_name}"

        if patient_webhook:
            slack(patient_webhook, msg)
        if it_webhook and it_webhook != patient_webhook:
            slack(it_webhook, msg)
        if not patient_webhook and not it_webhook:
            print(f"   No Slack webhook configured")

        # Update dashboard
        try:
            requests.post("http://localhost:5001/api/update_status", json={
                "patient_id": patient_id, "status": "meeting_requested",
                "current_status": "awaiting_approval",
                "detail": "Head of Department requested meeting with Chief Doctor."
            }, timeout=2)
        except Exception:
            pass

        return f"""<html><body style="font-family:Arial;background:#080c10;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh">
        <div style="background:#111;padding:40px;border-radius:12px;text-align:center;max-width:460px;border:1px solid #1a56db">
          <div style="font-size:42px">📋</div>
          <h2 style="color:#3b82f6">Meeting Requested</h2>
          <p>Patient: <b>{patient_name}</b></p>
          <p>Doctor <b>{doctor_name}</b> has been notified via Slack to arrange a meeting with Chief Doctor.</p>
          <p style="color:#475569;font-size:12px;margin-top:16px">You can still approve using the buttons in the email after the meeting.</p>
        </div></body></html>"""

    # Already approved
    if data.get("approved"):
        approved_at = data.get("approved_at", "")
        approved_scenario = data.get("approved_scenario", "").replace("_", " ").title()
        return f"""<html><body style="font-family:Arial;background:#080c10;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh">
        <div style="background:#111;padding:40px;border-radius:12px;text-align:center;max-width:460px;border:1px solid #059669">
          <div style="font-size:42px">✅</div>
          <h2 style="color:#10b981">Already Approved</h2>
          <p>Patient: <b>{patient_name}</b></p>
          <p>Scenario: <b>{approved_scenario}</b></p>
          <p>Approved at: {approved_at}</p>
          <p style="color:#475569;font-size:12px;margin-top:16px">Doctor has been notified. This link is now inactive.</p>
        </div></body></html>"""

    # Approve
    pending_approvals[patient_id]["approved"] = True
    pending_approvals[patient_id]["approved_scenario"] = scenario
    pending_approvals[patient_id]["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Send Slack to doctor
    patient_webhook = os.getenv("SLACK_PATIENT_WEBHOOK", os.getenv("SLACK_WEBHOOK_URL", ""))
    scenarios = data.get("scenarios", {})
    approved_scenario_data = scenarios.get(scenario, {})
    treatment = approved_scenario_data.get("recommended_treatment", "Standard protocol")
    diagnosis = approved_scenario_data.get("diagnosis", "To be determined")

    slack_msg = f"APPROVED: Patient {patient_name} ({priority}) - Head approved {scenario_label}. Doctor: {doctor_name}. Diagnosis: {diagnosis}. Treatment: {treatment}"
    if patient_webhook:
        slack(patient_webhook, slack_msg)

    # Update dashboard
    try:
        requests.post("http://localhost:5001/api/update_status", json={
            "patient_id": patient_id, "status": "approved",
            "current_status": "under_treatment",
            "requires_head_approval": False,
            "discharge_status": "PENDING DISCHARGE FORM",
            "detail": f"Head approved {scenario_label}. {doctor_name} notified via Slack."
        }, timeout=2)
    except Exception:
        pass

    print(f"\n APPROVED: {patient_name} - {scenario_label} - Slack sent to {doctor_name}")

    return f"""<html><body style="font-family:Arial;background:#080c10;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh">
    <div style="background:#111;padding:40px;border-radius:12px;text-align:center;max-width:460px;border:1px solid #059669">
      <div style="font-size:42px">✓</div>
      <h2 style="color:#10b981">Approval Confirmed</h2>
      <p>Patient: <b>{patient_name}</b></p>
      <p>Priority: <b>{priority}</b></p>
      <p>Approved: <b>{scenario_label}</b></p>
      <p>Doctor <b>{doctor_name}</b> has been notified via Slack.</p>
      <p style="color:#475569;font-size:12px;margin-top:16px">ShadowGate | {HOSPITAL_NAME} | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div></body></html>"""


@app.route("/pending")
def get_pending():
    result = []
    for pid, data in pending_approvals.items():
        patient = data.get("patient", {})
        reg_at = data.get("registered_at", "")
        waiting_mins = 0
        if reg_at:
            try:
                reg_time = datetime.strptime(reg_at, "%Y-%m-%d %H:%M:%S")
                waiting_mins = int((datetime.now() - reg_time).total_seconds() / 60)
            except Exception:
                pass

        if data.get("approved"):
            status = "approved"
        elif data.get("escalated"):
            status = "escalated"
        elif data.get("reminder_sent"):
            status = "reminder_sent"
        elif data.get("meeting_requested"):
            status = "meeting_requested"
        else:
            status = "waiting"

        result.append({
            "patient_id": pid,
            "patient_name": patient.get("name", "Unknown"),
            "priority": data.get("priority", "P4"),
            "doctor": data.get("doctor_name", "Unknown"),
            "status": status,
            "waiting_minutes": waiting_mins,
            "registered_at": reg_at,
            "approved_at": data.get("approved_at", ""),
            "approved_scenario": data.get("approved_scenario", ""),
            "reminder_sent": data.get("reminder_sent", False),
            "escalated": data.get("escalated", False)
        })
    return jsonify({"pending": result, "total": len(result)})


def reminder_loop(patient_id):
    """Send reminder and escalation if no response."""
    time.sleep(REMINDER_WAIT)
    data = pending_approvals.get(patient_id)
    if not data or data.get("approved"):
        return

    patient_name = data.get("patient", {}).get("name", patient_id)
    priority = data.get("priority", "P4")
    base_url = APPROVAL_SERVER

    print(f"\n REMINDER: {patient_name} waiting {REMINDER_WAIT//60} mins")
    pending_approvals[patient_id]["reminder_sent"] = True
    pending_approvals[patient_id]["reminder_sent_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Reminder email
    best_url = f"{base_url}/approve/{patient_id}/best_case"
    mod_url = f"{base_url}/approve/{patient_id}/moderate_case"
    worst_url = f"{base_url}/approve/{patient_id}/worst_case"
    meet_url = f"{base_url}/approve/{patient_id}/request_meeting"

    html = f"""<html><body style="font-family:Arial;background:#080c10;padding:20px">
<div style="max-width:600px;margin:0 auto;background:#111;border-radius:12px;overflow:hidden">
  <div style="background:#78350f;padding:16px 24px">
    <div style="color:#fcd34d;font-weight:bold">REMINDER - Approval Required</div>
    <div style="color:#fff;font-size:18px;font-weight:700">Patient {patient_name} still waiting</div>
  </div>
  <div style="padding:24px;color:#e2e8f0">
    <p>Patient <b>{patient_name}</b> ({priority}) has been waiting <b>{REMINDER_WAIT//60} minutes</b>.</p>
    <table style="width:100%;border-collapse:collapse;margin-top:16px">
      <tr>
        <td style="padding:4px"><a href="{best_url}" style="display:block;background:#38A169;color:#fff;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold">APPROVE BEST CASE</a></td>
        <td style="padding:4px"><a href="{mod_url}" style="display:block;background:#DD6B20;color:#fff;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold">APPROVE MODERATE</a></td>
        <td style="padding:4px"><a href="{worst_url}" style="display:block;background:#E53E3E;color:#fff;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold">APPROVE WORST</a></td>
        <td style="padding:4px"><a href="{meet_url}" style="display:block;background:#1a2744;color:#93c5fd;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold;border:1px solid #1e3a5f">REQUEST MEETING</a></td>
      </tr>
    </table>
    <p style="color:#475569;font-size:11px;text-align:center;margin-top:16px">ShadowGate | {HOSPITAL_NAME}</p>
  </div>
</div></body></html>"""

    send_html_email(HEAD_EMAIL, f"[REMINDER] ShadowGate - {patient_name} ({priority}) needs approval", html)
    # Reminder Slack to IT only
    it_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    slack(it_webhook, f"REMINDER [IT ONLY]: Patient {patient_name} ({priority}) waiting {REMINDER_WAIT//60} mins - reminder sent to Head of Department")

    # Escalation
    time.sleep(ESCALATION_WAIT - REMINDER_WAIT)
    data = pending_approvals.get(patient_id)
    if not data or data.get("approved"):
        return

    print(f"\n ESCALATION: {patient_name} - escalating with CC to senior")
    pending_approvals[patient_id]["escalated"] = True
    pending_approvals[patient_id]["escalated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    esc_html = f"""<html><body style="font-family:Arial;background:#080c10;padding:20px">
<div style="max-width:600px;margin:0 auto;background:#111;border-radius:12px;overflow:hidden">
  <div style="background:#7f1d1d;padding:16px 24px">
    <div style="color:#fca5a5;font-weight:bold;text-transform:uppercase">URGENT ESCALATION</div>
    <div style="color:#fff;font-size:18px;font-weight:700">No response from Head of Department</div>
  </div>
  <div style="padding:24px;color:#e2e8f0">
    <div style="background:#2d0a0a;border:1px solid #991b1b;border-radius:8px;padding:12px;margin-bottom:16px">
      Patient <b>{patient_name}</b> ({priority}) has been waiting <b>{ESCALATION_WAIT//60} minutes</b>. CC sent to senior management.
    </div>
    <table style="width:100%;border-collapse:collapse">
      <tr>
        <td style="padding:4px"><a href="{best_url}" style="display:block;background:#38A169;color:#fff;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold">APPROVE BEST</a></td>
        <td style="padding:4px"><a href="{mod_url}" style="display:block;background:#DD6B20;color:#fff;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold">APPROVE MODERATE</a></td>
        <td style="padding:4px"><a href="{worst_url}" style="display:block;background:#E53E3E;color:#fff;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold">APPROVE WORST</a></td>
        <td style="padding:4px"><a href="{meet_url}" style="display:block;background:#1a2744;color:#93c5fd;text-decoration:none;padding:12px;border-radius:6px;text-align:center;font-weight:bold;border:1px solid #1e3a5f">REQUEST MEETING</a></td>
      </tr>
    </table>
  </div>
</div></body></html>"""

    send_html_email(HEAD_EMAIL, f"[URGENT ESCALATION] ShadowGate - {patient_name} ({priority})", esc_html, cc=SENIOR_EMAIL if SENIOR_EMAIL else None)
    # Escalation Slack to IT only
    slack(it_webhook, f"ESCALATION [IT ONLY]: Patient {patient_name} ({priority}) - {ESCALATION_WAIT//60} mins no response - escalated to senior management")


def start_server(port=5000):
    """Start in background thread."""
    import time as t
    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False),
        daemon=True
    )
    thread.start()
    t.sleep(1.5)
    print(f"   Approval server running at http://localhost:{port}")
    return thread


if __name__ == "__main__":
    print("\n ShadowGate Approval Server")
    print(f" http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
