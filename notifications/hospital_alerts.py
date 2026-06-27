"""
ShadowGate - Hospital Alert System
Confidential email to Head of Department when risks are found.
Slack to doctor only after Head approves.
Unprofessional conduct alert to Head immediately.

Human in the loop at every critical decision point.
"""

import os
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
HEAD_OF_DEPT_EMAIL = os.getenv("HEAD_OF_DEPT_EMAIL", "")
SLACK_WEBHOOK = os.getenv("SLACK_PATIENT_WEBHOOK", os.getenv("SLACK_WEBHOOK_URL", ""))  # Healthcare team channel
HOSPITAL_NAME = os.getenv("HOSPITAL_NAME", "City General Hospital")
APPROVAL_SERVER = os.getenv("APPROVAL_SERVER_URL", "http://localhost:5000")


# ─────────────────────────────────────────
# EMAIL TO HEAD OF DEPARTMENT
# ─────────────────────────────────────────

def send_head_of_dept_alert(patient, aria_result, safe_result=None, guardian_result=None):
    """
    Send confidential email to Head of Department.
    Contains all scenarios and unknown risks.
    Only sent to Head. Team does NOT see this.
    """
    patient_name = patient.get("name", "Unknown")
    patient_id = patient.get("patient_id", "Unknown")
    priority = aria_result.get("priority", "P4")
    unknown_risks = aria_result.get("unknown_risks", [])
    scenarios = aria_result.get("scenarios", {})

    print(f"\n   Sending confidential alert to Head of Department...")
    print(f"   Patient: {patient_name} | Priority: {priority}")
    print(f"   Unknown risks: {len(unknown_risks)}")

    subject = f"[CONFIDENTIAL] ShadowGate Patient Alert - {patient_name} - Priority {priority}"

    # Register with approval server including doctor assignment
    assignment = guardian_result or {}
    doctor_name = assignment.get("doctor_name", "Not yet assigned")
    try:
        import requests as req
        reg_data = {
            "patient_id": patient_id,
            "patient": patient,
            "priority": priority,
            "scenarios": scenarios,
            "assignment": assignment,
            "doctor_name": doctor_name,
            "approved": False
        }
        req.post(f"{APPROVAL_SERVER}/register", json=reg_data, timeout=2)
        print(f"   Registered with approval server")
        print(f"   Doctor: {doctor_name}")
    except Exception as e:
        print(f"   Approval server not running: {e}")

    # Build HTML email with approval buttons
    html_body = build_head_email_html(
        patient, priority, scenarios, unknown_risks, safe_result
    )
    text_body = build_head_email_body(
        patient, priority, scenarios, unknown_risks, safe_result
    )

    success = send_email_html(HEAD_OF_DEPT_EMAIL, subject, text_body, html_body)

    if success:
        print(f"   Confidential email sent to Head of Department")
        print(f"   This message has NOT been shared with the team")
    else:
        print(f"   Email simulation - would send to Head of Department")
        print(f"   Subject: {subject}")

    return {
        "type": "head_of_dept_alert",
        "patient_id": patient_id,
        "patient_name": patient_name,
        "priority": priority,
        "unknown_risks_count": len(unknown_risks),
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recipient": "Head of Department only",
        "team_notified": False
    }


def build_head_email_body(patient, priority, scenarios, unknown_risks, safe_result):
    """Build the confidential email body for Head of Department."""
    patient_name = patient.get("name", "Unknown")
    patient_age = patient.get("age", "Unknown")
    symptoms = patient.get("symptoms", "Unknown")
    medications = patient.get("current_medications", [])
    allergies = patient.get("allergies", [])
    history = patient.get("medical_history", [])

    priority_labels = {
        "P1": "CRITICAL - Immediate attention required",
        "P2": "URGENT - Within 30 minutes",
        "P3": "MODERATE - Within 2 hours",
        "P4": "NON-URGENT - Within 4 hours"
    }

    # Build scenarios section
    scenarios_text = ""
    for scenario_key in ["best_case", "moderate_case", "worst_case"]:
        scenario = scenarios.get(scenario_key, {})
        if scenario:
            label = scenario_key.replace("_", " ").title()
            risk_level = scenario.get("risk_level", "UNKNOWN")
            diagnosis = scenario.get("diagnosis", "Unknown")
            treatment = scenario.get("recommended_treatment", "Unknown")
            medications_list = scenario.get("medications", [])
            recovery = scenario.get("estimated_recovery", "Unknown")
            probability = scenario.get("probability", "Unknown")

            scenarios_text += f"""
{label} ({probability}):
  Diagnosis: {diagnosis}
  Treatment: {treatment}
  Medications: {", ".join(medications_list) if medications_list else "None"}
  Recovery: {recovery}
  Risk Level: {risk_level}
"""

    # Build unknown risks section
    risks_text = ""
    if unknown_risks:
        risks_text = "\nUNKNOWN RISKS DISCOVERED BY SHADOWGATE:\n"
        risks_text += "These risks were NOT in the standard test suite.\n"
        risks_text += "-" * 50 + "\n"
        for i, risk in enumerate(unknown_risks, 1):
            severity = risk.get("severity", "UNKNOWN")
            risks_text += f"""
Risk {i} [{severity}]: {risk.get("risk", "Unknown")}
  Why dangerous: {risk.get("why_dangerous", "Unknown")}
  Recommendation: {risk.get("recommendation", "Unknown")}
"""
    else:
        risks_text = "\nNo unknown risks detected.\n"

    # Build safety section
    safety_text = ""
    if safe_result:
        blocked = []
        warnings = []
        for scenario_key, report in safe_result.get("safety_reports", {}).items():
            for issue in report.get("issues", []):
                blocked.append(f"  BLOCKED [{scenario_key}]: {issue['detail']}")
            for warning in report.get("warnings", []):
                warnings.append(f"  WARNING [{scenario_key}]: {warning['detail']}")

        if blocked:
            safety_text = "\nSAFETY BLOCKS:\n" + "\n".join(blocked) + "\n"
        if warnings:
            safety_text += "\nSAFETY WARNINGS:\n" + "\n".join(warnings) + "\n"
        if not blocked and not warnings:
            safety_text = "\nAll treatment scenarios passed safety validation.\n"

    body = f"""
Dear Head of Department,

This is a CONFIDENTIAL alert from ShadowGate AI Testing System at {HOSPITAL_NAME}.

This message has been sent ONLY to you before any team notification.
Please review and take action before the care team is notified.

PATIENT SUMMARY:
{"=" * 50}
Patient Name:    {patient_name}
Age:             {patient_age}
Priority:        {priority} - {priority_labels.get(priority, "Unknown")}
Symptoms:        {symptoms}
Medical History: {", ".join(history) if history else "None"}
Current Meds:    {", ".join(medications) if medications else "None"}
Allergies:       {", ".join(allergies) if allergies else "None"}
Admitted:        {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

TREATMENT SCENARIOS:
{"=" * 50}
{scenarios_text}

{risks_text}

{safety_text}

YOUR DECISION:
{"=" * 50}
Please review the above scenarios and unknown risks.
Reply to this email with one of the following:

  APPROVE BEST CASE     - Patient likely has minor condition
  APPROVE MODERATE      - Patient needs standard treatment
  APPROVE WORST CASE    - Patient needs immediate intervention
  REQUEST MORE TESTS    - Need additional diagnostic information
  ESCALATE              - Forward to senior specialist

Once you approve, the assigned doctor will be notified via Slack
with the approved treatment plan only.

The team has NOT been notified yet.

{"=" * 50}
This alert was generated by ShadowGate AI Testing System.
Unknown risks were discovered that were not in the standard test suite.
Immediate review recommended.

ShadowGate | {HOSPITAL_NAME}
Confidential Patient Safety System
{"=" * 50}
"""
    return body


# ─────────────────────────────────────────
# SLACK TO DOCTOR (AFTER APPROVAL)
# ─────────────────────────────────────────

def build_head_email_html(patient, priority, scenarios, unknown_risks, safe_result):
    """Build beautiful HTML email with approval buttons for Head of Department."""
    patient_name = patient.get("name", "Unknown")
    patient_age = patient.get("age", "Unknown")
    patient_id = patient.get("patient_id", "Unknown")
    symptoms = patient.get("symptoms", "Unknown")
    medications = patient.get("current_medications", [])
    allergies = patient.get("allergies", [])
    history = patient.get("medical_history", [])

    priority_colors = {
        "P1": "#E53E3E",
        "P2": "#DD6B20",
        "P3": "#38A169",
        "P4": "#3182CE"
    }
    priority_color = priority_colors.get(priority, "#3182CE")

    priority_labels = {
        "P1": "CRITICAL - Immediate attention required",
        "P2": "URGENT - Within 30 minutes",
        "P3": "MODERATE - Within 2 hours",
        "P4": "NON-URGENT - Within 4 hours"
    }

    # Build scenarios rows
    scenario_rows = ""
    for key, label, color in [
        ("best_case", "BEST CASE", "#38A169"),
        ("moderate_case", "MODERATE CASE", "#DD6B20"),
        ("worst_case", "WORST CASE", "#E53E3E")
    ]:
        s = scenarios.get(key, {})
        if s:
            meds = ", ".join(s.get("medications", [])) or "None"
            scenario_rows += f"""
            <tr>
                <td style="padding:12px;border-bottom:1px solid #2d2d2d;">
                    <span style="background:{color};color:#fff;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{label}</span>
                </td>
                <td style="padding:12px;border-bottom:1px solid #2d2d2d;color:#ffffff;">{s.get("diagnosis","Unknown")}</td>
                <td style="padding:12px;border-bottom:1px solid #2d2d2d;color:#cccccc;">{meds}</td>
                <td style="padding:12px;border-bottom:1px solid #2d2d2d;color:#cccccc;">{s.get("estimated_recovery","Unknown")}</td>
            </tr>"""

    # Build unknown risks
    risks_html = ""
    if unknown_risks:
        for risk in unknown_risks:
            sev = risk.get("severity","UNKNOWN")
            sev_color = "#E53E3E" if sev == "HIGH" else "#DD6B20" if sev == "MEDIUM" else "#38A169"
            risks_html += f"""
            <div style="background:#1a1a1a;border-left:4px solid {sev_color};padding:12px;margin:8px 0;border-radius:0 6px 6px 0;">
                <div style="color:{sev_color};font-weight:bold;font-size:12px;margin-bottom:4px;">[{sev}] {risk.get("risk","")}</div>
                <div style="color:#cccccc;font-size:13px;margin-bottom:4px;">{risk.get("why_dangerous","")}</div>
                <div style="color:#888;font-size:12px;">Recommendation: {risk.get("recommendation","")}</div>
            </div>"""
    else:
        risks_html = '<p style="color:#38A169;">No unknown risks detected.</p>'

    # Approval buttons
    approve_url_best = f"{APPROVAL_SERVER}/approve/{patient_id}/best_case"
    approve_url_moderate = f"{APPROVAL_SERVER}/approve/{patient_id}/moderate_case"
    approve_url_worst = f"{APPROVAL_SERVER}/approve/{patient_id}/worst_case"
    approve_url_tests = f"{APPROVAL_SERVER}/approve/{patient_id}/request_tests"

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:20px;">

    <!-- Header -->
    <div style="background:#111111;border-radius:12px 12px 0 0;padding:24px;border-bottom:3px solid {priority_color};">
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <div>
                <div style="color:#888;font-size:11px;letter-spacing:1px;text-transform:uppercase;">ShadowGate | {HOSPITAL_NAME}</div>
                <div style="color:#ffffff;font-size:20px;font-weight:bold;margin-top:4px;">Confidential Patient Alert</div>
            </div>
            <div style="background:{priority_color};color:#fff;padding:6px 14px;border-radius:6px;font-weight:bold;font-size:14px;">{priority}</div>
        </div>
    </div>

    <!-- Confidential Banner -->
    <div style="background:#2d1b1b;border:1px solid #E53E3E;padding:10px 24px;text-align:center;">
        <span style="color:#E53E3E;font-size:12px;font-weight:bold;">CONFIDENTIAL - This message has not been shared with anyone. Only you have received this alert.</span>
    </div>

    <!-- Patient Info -->
    <div style="background:#111111;padding:24px;margin-top:2px;">
        <div style="color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">Patient Details</div>
        <table style="width:100%;border-collapse:collapse;">
            <tr>
                <td style="padding:6px 0;color:#888;width:140px;">Name</td>
                <td style="padding:6px 0;color:#ffffff;font-weight:bold;">{patient_name}</td>
                <td style="padding:6px 0;color:#888;width:140px;">Age</td>
                <td style="padding:6px 0;color:#ffffff;">{patient_age}</td>
            </tr>
            <tr>
                <td style="padding:6px 0;color:#888;">Priority</td>
                <td style="padding:6px 0;color:{priority_color};font-weight:bold;">{priority_labels.get(priority,"")}</td>
                <td style="padding:6px 0;color:#888;">Admitted</td>
                <td style="padding:6px 0;color:#ffffff;">{datetime.now().strftime("%Y-%m-%d %H:%M")}</td>
            </tr>
            <tr>
                <td style="padding:6px 0;color:#888;vertical-align:top;">Symptoms</td>
                <td colspan="3" style="padding:6px 0;color:#ffffff;">{symptoms}</td>
            </tr>
            <tr>
                <td style="padding:6px 0;color:#888;vertical-align:top;">History</td>
                <td colspan="3" style="padding:6px 0;color:#cccccc;">{", ".join(history) if history else "None"}</td>
            </tr>
            <tr>
                <td style="padding:6px 0;color:#888;vertical-align:top;">Medications</td>
                <td colspan="3" style="padding:6px 0;color:#cccccc;">{", ".join(medications) if medications else "None"}</td>
            </tr>
            <tr>
                <td style="padding:6px 0;color:#888;vertical-align:top;">Allergies</td>
                <td colspan="3" style="padding:6px 0;color:#E53E3E;font-weight:bold;">{", ".join(allergies) if allergies else "None"}</td>
            </tr>
        </table>
    </div>

    <!-- Unknown Risks -->
    <div style="background:#111111;padding:24px;margin-top:2px;">
        <div style="color:#E53E3E;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">
            Unknown Risks Discovered by ShadowGate ({len(unknown_risks)} found)
        </div>
        <div style="color:#888;font-size:12px;margin-bottom:10px;">These risks were NOT in the standard test suite. ShadowGate discovered them automatically.</div>
        {risks_html}
    </div>

    <!-- Treatment Scenarios -->
    <div style="background:#111111;padding:24px;margin-top:2px;">
        <div style="color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">Treatment Scenarios</div>
        <table style="width:100%;border-collapse:collapse;">
            <tr style="background:#1a1a1a;">
                <th style="padding:10px 12px;text-align:left;color:#888;font-size:11px;">Scenario</th>
                <th style="padding:10px 12px;text-align:left;color:#888;font-size:11px;">Diagnosis</th>
                <th style="padding:10px 12px;text-align:left;color:#888;font-size:11px;">Medications</th>
                <th style="padding:10px 12px;text-align:left;color:#888;font-size:11px;">Recovery</th>
            </tr>
            {scenario_rows}
        </table>
    </div>

    <!-- Approval Buttons -->
    <div style="background:#111111;padding:24px;margin-top:2px;border-radius:0 0 12px 12px;">
        <div style="color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:16px;">Your Decision</div>
        <div style="color:#cccccc;font-size:13px;margin-bottom:20px;">
            Please review the scenarios and unknown risks above, then approve a treatment plan.
            The assigned doctor will be notified via Slack only after your approval.
        </div>

        <table style="width:100%;border-collapse:collapse;">
            <tr>
                <td style="padding:6px;">
                    <a href="{approve_url_best}" style="display:block;background:#38A169;color:#ffffff;text-decoration:none;padding:14px 10px;border-radius:8px;text-align:center;font-weight:bold;font-size:13px;">
                        APPROVE<br>BEST CASE
                    </a>
                </td>
                <td style="padding:6px;">
                    <a href="{approve_url_moderate}" style="display:block;background:#DD6B20;color:#ffffff;text-decoration:none;padding:14px 10px;border-radius:8px;text-align:center;font-weight:bold;font-size:13px;">
                        APPROVE<br>MODERATE CASE
                    </a>
                </td>
                <td style="padding:6px;">
                    <a href="{approve_url_worst}" style="display:block;background:#E53E3E;color:#ffffff;text-decoration:none;padding:14px 10px;border-radius:8px;text-align:center;font-weight:bold;font-size:13px;">
                        APPROVE<br>WORST CASE
                    </a>
                </td>
                <td style="padding:6px;">
                    <a href="{approve_url_tests}" style="display:block;background:#2d2d2d;color:#cccccc;text-decoration:none;padding:14px 10px;border-radius:8px;text-align:center;font-weight:bold;font-size:13px;">
                        REQUEST<br>MORE TESTS
                    </a>
                </td>
            </tr>
        </table>

        <div style="margin-top:20px;padding-top:16px;border-top:1px solid #2d2d2d;color:#555;font-size:11px;text-align:center;">
            ShadowGate AI Testing System | {HOSPITAL_NAME} | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>

</div>
</body>
</html>"""
    return html


def send_email_html(to_email, subject, text_body, html_body):
    """Send HTML email via SMTP."""
    if not SMTP_USER or not SMTP_PASS or not to_email:
        return False

    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        print(f"   HTML email sent successfully to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"   Authentication failed - check SMTP_USER and SMTP_PASS")
        return False
    except Exception as e:
        print(f"   Email error: {e}")
        return False


def send_doctor_slack_notification(patient, assignment, approved_scenario=None):
    """
    Send Slack notification to assigned doctor.
    Only called AFTER Head of Department approves.
    Contains approved treatment plan only.
    """
    patient_name = patient.get("name", "Unknown")
    patient_id = patient.get("patient_id", "Unknown")
    doctor_name = assignment.get("doctor_name", "Unknown")
    priority = assignment.get("priority", "P4")
    wait_time = assignment.get("estimated_wait_minutes", 0)

    priority_icons = {
        "P1": "CRITICAL",
        "P2": "URGENT",
        "P3": "MODERATE",
        "P4": "NON-URGENT"
    }

    scenario_text = ""
    if approved_scenario:
        scenario_text = f"""
Approved Treatment Plan:
  Diagnosis: {approved_scenario.get('diagnosis', 'To be determined')}
  Treatment: {approved_scenario.get('recommended_treatment', 'Standard protocol')}
  Medications: {', '.join(approved_scenario.get('medications', []))}
  Recovery: {approved_scenario.get('estimated_recovery', 'Unknown')}"""

    priority_colors = {"P1": "danger", "P2": "warning", "P3": "good", "P4": "good"}

    message = {
        "text": f"Patient Assignment - {patient_name} | {priority_icons.get(priority, priority)}",
        "attachments": [
            {
                "color": priority_colors.get(priority, "good"),
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"Patient Assignment - {priority_icons.get(priority, priority)}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Patient:*\n{patient_name}"},
                            {"type": "mrkdwn", "text": f"*Priority:*\n{priority}"},
                            {"type": "mrkdwn", "text": f"*Assigned Doctor:*\n{doctor_name}"},
                            {"type": "mrkdwn", "text": f"*Estimated Wait:*\n{wait_time} minutes"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Symptoms:* {patient.get('symptoms', 'Unknown')}\n*Treatment plan approved by Head of Department.*{scenario_text}"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"ShadowGate Patient Care | {HOSPITAL_NAME} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    success = send_slack(message)

    if success:
        print(f"   Slack notification sent to {doctor_name}")
    else:
        print(f"   Slack simulation - would notify {doctor_name}")

    return {
        "type": "doctor_notification",
        "patient_id": patient_id,
        "doctor": doctor_name,
        "priority": priority,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "head_approved": True
    }


# ─────────────────────────────────────────
# CONDUCT ALERT TO HEAD
# ─────────────────────────────────────────

def send_conduct_alert(doctor_id, doctor_name, patient_id, action, details):
    """
    Send IMMEDIATE confidential conduct alert to Head of Department.
    Never shared with team. Head decides action.
    """
    print(f"\n   CONDUCT ALERT - Sending to Head of Department")
    print(f"   Doctor: {doctor_name} | Issue: {action}")
    print(f"   This has NOT been shared with the team")

    subject = f"[URGENT CONFIDENTIAL] ShadowGate Conduct Alert - {doctor_name}"

    body = f"""
Dear Head of Department,

ShadowGate has detected a potential patient safety concern
requiring your IMMEDIATE and CONFIDENTIAL review.

INCIDENT DETAILS:
{"=" * 50}
Doctor:    {doctor_name} (ID: {doctor_id})
Patient:   {patient_id}
Issue:     {action}
Time:      {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Severity:  HIGH

WHAT HAPPENED:
{details}

EVIDENCE LOGGED:
  Full audit trail saved in ShadowGate governance system.
  All actions timestamped and recorded.

YOUR OPTIONS:
{"=" * 50}
  INTERVENE IMMEDIATELY - Assign new doctor to patient
  MONITOR SITUATION     - Add supervision, continue monitoring
  INVESTIGATE FURTHER   - Initiate formal review process
  NO ACTION REQUIRED    - False positive, dismiss alert

This alert has NOT been shared with anyone else.
Only you have received this notification.

ShadowGate | {HOSPITAL_NAME}
Confidential Governance System
{"=" * 50}
"""

    success = send_email(HEAD_OF_DEPT_EMAIL, subject, body)

    if success:
        print(f"   Confidential conduct alert sent to Head of Department")
    else:
        print(f"   Conduct alert simulation - would send to Head of Department")
        print(f"   Issue: {action}")
        print(f"   Doctor: {doctor_name}")

    return {
        "type": "conduct_alert",
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "patient_id": patient_id,
        "action": action,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recipient": "Head of Department only",
        "team_notified": False
    }


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def send_email(to_email, subject, body):
    """Send email via SMTP."""
    if not SMTP_USER or not SMTP_PASS or not to_email:
        print(f"   Email not configured. Missing:")
        if not SMTP_USER:
            print(f"     SMTP_USER not set")
        if not SMTP_PASS:
            print(f"     SMTP_PASS not set")
        if not to_email:
            print(f"     Recipient email not set")
        return False

    try:
        print(f"   Connecting to {SMTP_HOST}:{SMTP_PORT}...")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        print(f"   Email sent successfully to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"   Authentication failed: {e}")
        print(f"   Check SMTP_USER and SMTP_PASS in .env")
        print(f"   Make sure you are using Gmail App Password not regular password")
        return False
    except smtplib.SMTPException as e:
        print(f"   SMTP error: {e}")
        return False
    except Exception as e:
        print(f"   Email error: {e}")
        return False


def send_slack(message):
    """Send Slack notification via webhook."""
    if not SLACK_WEBHOOK:
        return False

    try:
        response = requests.post(
            SLACK_WEBHOOK,
            json=message,
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False


# ─────────────────────────────────────────
# MAIN ALERT ORCHESTRATOR
# ─────────────────────────────────────────

def run_hospital_alerts(patients, hospital_result):
    """
    Main function. Run complete alert system for all patients.
    Called after hospital pipeline completes.
    """
    print(f"\n{'='*55}")
    print(f" SHADOWGATE - HOSPITAL ALERT SYSTEM")
    print(f"{'='*55}")

    aria_results = hospital_result.get("aria", {}).get("results", [])
    safe_results = hospital_result.get("safe", {}).get("results", [])
    guardian_results = hospital_result.get("guardian", {}).get("results", [])

    alerts_sent = []

    for i, patient in enumerate(patients):
        aria_result = aria_results[i] if i < len(aria_results) else {}
        safe_result = safe_results[i] if i < len(safe_results) else {}
        guardian_result = guardian_results[i] if i < len(guardian_results) else {}

        if not aria_result:
            continue

        priority = aria_result.get("priority", "P4")
        unknown_risks = aria_result.get("unknown_risks", [])
        requires_approval = aria_result.get("requires_head_approval", False)

        print(f"\n Patient: {patient.get('name')} | Priority: {priority}")

        # P1/P2 or any unknown risks = Head approval required first
        needs_head_approval = priority in ["P1", "P2"] or len(unknown_risks) > 0

        if needs_head_approval:
            print(f"   Requires Head of Department approval")
            alert = send_head_of_dept_alert(patient, aria_result, safe_result, guardian_result)
            alerts_sent.append(alert)
            print(f"   Waiting for Head of Department approval...")
            print(f"   Doctor will be notified via Slack only after approval")

        else:
            # P3/P4 with no unknown risks - notify doctor directly
            print(f"   Priority {priority} - notifying doctor directly (no Head approval needed)")
            if guardian_result and guardian_result.get("status") == "ASSIGNED":
                doctor = guardian_result.get("doctor_name", "Unknown")
                print(f"   Sending Slack to {doctor}...")
                slack_alert = send_doctor_slack_notification(
                    patient, guardian_result
                )
                alerts_sent.append(slack_alert)
                print(f"   Doctor notified automatically")

    print(f"\n{'='*55}")
    print(f" ALERT SUMMARY")
    print(f"{'='*55}")
    print(f" Total alerts sent: {len(alerts_sent)}")

    head_alerts = [a for a in alerts_sent if a["type"] == "head_of_dept_alert"]
    doctor_alerts = [a for a in alerts_sent if a["type"] == "doctor_notification"]
    conduct_alerts = [a for a in alerts_sent if a["type"] == "conduct_alert"]

    print(f" Head of Department (confidential): {len(head_alerts)}")
    print(f" Doctor notifications (post approval): {len(doctor_alerts)}")
    print(f" Conduct alerts: {len(conduct_alerts)}")
    print(f"{'='*55}")

    return alerts_sent


if __name__ == "__main__":
    # Test with sample patients
    from hospital.pipeline import SAMPLE_PATIENTS, HospitalPipeline

    pipeline = HospitalPipeline()
    result = pipeline.run(SAMPLE_PATIENTS)

    alerts = run_hospital_alerts(SAMPLE_PATIENTS, result)
    print(f"\n Alert system working correctly!")
    print(f" Total alerts: {len(alerts)}")
