"""
ShadowGate - Patient Intake API
Receives patient data from dashboard form.
Triggers hospital pipeline.
Returns results to dashboard.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Store recent pipeline results
pipeline_results = {}
patient_queue = []
patient_history = []  # Full history with status changes

def update_patient_status(patient_id, status, detail=""):
    """Update patient status and log to history."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update in results
    if patient_id in pipeline_results:
        pipeline_results[patient_id]["current_status"] = status
        pipeline_results[patient_id]["last_updated"] = now

        if "timeline" not in pipeline_results[patient_id]:
            pipeline_results[patient_id]["timeline"] = []

        pipeline_results[patient_id]["timeline"].append({
            "status": status,
            "detail": detail,
            "time": now
        })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


@app.route("/api/patients", methods=["POST"])
def add_patient():
    """Receive patient data from form and run pipeline."""
    try:
        data = request.json

        # Build patient record
        patient = {
            "patient_id": f"P{len(patient_queue)+1:03d}",
            "name": data.get("name", "Unknown"),
            "age": int(data.get("age", 0)),
            "gender": data.get("gender", "Unknown"),
            "symptoms": data.get("symptoms", ""),
            "vital_signs": {
                "heart_rate": int(data.get("heart_rate", 80)),
                "blood_pressure": data.get("blood_pressure", "120/80"),
                "temperature_f": float(data.get("temperature_f", 98.6)),
                "oxygen_saturation": int(data.get("oxygen_saturation", 98))
            },
            "medical_history": [h.strip() for h in data.get("medical_history", "").split(",") if h.strip()],
            "current_medications": [m.strip() for m in data.get("current_medications", "").split(",") if m.strip()],
            "allergies": [a.strip() for a in data.get("allergies", "").split(",") if a.strip()],
            "weight_kg": float(data.get("weight_kg", 70)),
            "symptom_duration": data.get("symptom_duration", "Unknown"),
            "pain_scale": int(data.get("pain_scale", 5)),
            "lives_alone": data.get("lives_alone", False),
            "emergency_contacts": [data.get("emergency_contact", "")] if data.get("emergency_contact") else [],
            "insurance_status": data.get("insurance_status", "active")
        }

        patient_queue.append(patient)

        # Run pipeline in background thread
        thread = threading.Thread(
            target=run_pipeline_for_patient,
            args=(patient,),
            daemon=True
        )
        thread.start()

        return jsonify({
            "status": "accepted",
            "patient_id": patient["patient_id"],
            "message": f"Patient {patient['name']} admitted. ShadowGate is analysing..."
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/results/<patient_id>")
def get_results(patient_id):
    """Get pipeline results for a patient."""
    result = pipeline_results.get(patient_id)
    if not result:
        return jsonify({"status": "processing"})
    return jsonify(result)


@app.route("/api/results")
def get_all_results():
    """Get all pipeline results."""
    return jsonify({
        "results": list(pipeline_results.values()),
        "queue_length": len(patient_queue)
    })


@app.route("/api/discharge", methods=["POST"])
def discharge_patient():
    """
    Doctor submits discharge readiness form.
    CARA validates all criteria.
    If approved, Head of Dept gets notification.
    """
    try:
        data = request.json
        patient_id = data.get("patient_id")

        if patient_id not in pipeline_results:
            return jsonify({"status": "error", "message": "Patient not found"}), 404

        patient_data = pipeline_results[patient_id]
        patient = None

        # Find patient in queue
        for p in patient_queue:
            if p["patient_id"] == patient_id:
                patient = p
                break

        if not patient:
            return jsonify({"status": "error", "message": "Patient data not found"}), 404

        # Build treatment data from doctor form
        treatment_data = {
            "vitals_stable": data.get("vitals_stable", False),
            "current_pain_scale": int(data.get("pain_scale", 10)),
            "medication_prescribed": data.get("medication_prescribed", False),
            "follow_up_scheduled": data.get("follow_up_scheduled", False),
            "discharge_summary_complete": data.get("discharge_summary_complete", False),
            "patient_education_done": data.get("patient_education_done", False),
            "new_symptoms": [data.get("new_symptoms")] if data.get("new_symptoms") else []
        }

        # Run CARA validation
        from hospital.automations.aria import ARIA
        aria = ARIA()
        aria_output = aria.process([patient])
        aria_results = aria_output.get("results", [])

        from hospital.automations.cara import CARA
        cara = CARA()
        cara_output = cara.process([patient], aria_results, [treatment_data])
        cara_results = cara_output.get("results", [])
        cara_result = cara_results[0] if cara_results else {}

        discharge_status = cara_result.get("discharge_check", {}).get("status", "BLOCKED")
        blockers = cara_result.get("discharge_check", {}).get("blockers", [])
        warnings = cara_result.get("discharge_check", {}).get("warnings", [])
        patient_message = cara_result.get("patient_message", "")
        follow_up = cara_result.get("follow_up", {})

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if discharge_status == "APPROVED":
            # Update patient status
            pipeline_results[patient_id]["discharge_status"] = "APPROVED"
            pipeline_results[patient_id]["current_status"] = "discharged"
            pipeline_results[patient_id]["patient_message"] = patient_message
            pipeline_results[patient_id]["follow_up"] = follow_up
            pipeline_results[patient_id]["last_updated"] = now

            if "timeline" not in pipeline_results[patient_id]:
                pipeline_results[patient_id]["timeline"] = []

            pipeline_results[patient_id]["timeline"].append({
                "status": "Discharge Approved by CARA",
                "detail": "All discharge criteria met. Head of Department notified.",
                "time": now
            })

            # Notify Head of Department
            thread = threading.Thread(
                target=notify_head_discharge,
                args=(patient, pipeline_results[patient_id], follow_up),
                daemon=True
            )
            thread.start()

            return jsonify({
                "status": "approved",
                "message": f"Discharge approved for {patient.get('name')}",
                "patient_message": patient_message,
                "follow_up": follow_up
            })

        else:
            # Discharge blocked
            pipeline_results[patient_id]["discharge_status"] = "BLOCKED"
            pipeline_results[patient_id]["last_updated"] = now

            if "timeline" not in pipeline_results[patient_id]:
                pipeline_results[patient_id]["timeline"] = []

            blocker_details = ", ".join([b.get("detail", "") for b in blockers])
            pipeline_results[patient_id]["timeline"].append({
                "status": "Discharge Blocked by CARA",
                "detail": f"Criteria not met: {blocker_details}",
                "time": now
            })

            return jsonify({
                "status": "blocked",
                "message": "Discharge criteria not met",
                "blockers": blockers,
                "warnings": warnings
            })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


def notify_head_discharge(patient, patient_data, follow_up):
    """Notify Head of Department that patient is ready for discharge."""
    try:
        from notifications.hospital_alerts import (
            SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS,
            HEAD_OF_DEPT_EMAIL, HOSPITAL_NAME, SLACK_WEBHOOK
        )
        import smtplib
        import requests as req
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        patient_name = patient.get("name", "Unknown")
        doctor = patient_data.get("doctor_assigned", "Unknown")
        priority = patient_data.get("priority", "P4")
        follow_up_date = follow_up.get("scheduled_date", "TBD") if follow_up else "TBD"
        follow_up_type = follow_up.get("type", "In-person") if follow_up else "In-person"

        # Email to Head
        subject = f"ShadowGate - Patient Ready for Discharge - {patient_name}"

        html = f"""<html><body style="font-family:Arial,sans-serif;background:#080c10;padding:20px;">
<div style="max-width:600px;margin:0 auto;background:#111;border-radius:12px;overflow:hidden;">
  <div style="background:#052e16;padding:16px 24px;border-bottom:2px solid #059669;">
    <div style="color:#6ee7b7;font-weight:bold;font-size:12px;text-transform:uppercase;">Patient Discharge Ready</div>
    <div style="color:#fff;font-size:18px;font-weight:700;margin-top:4px;">{patient_name} is ready to go home</div>
  </div>
  <div style="padding:24px;color:#e2e8f0;">
    <table style="width:100%;background:#0d1117;border-radius:8px;border-collapse:collapse;margin-bottom:20px;">
      <tr><td style="color:#888;padding:10px 14px;">Patient</td><td style="color:#fff;font-weight:bold;padding:10px 14px;">{patient_name}</td></tr>
      <tr><td style="color:#888;padding:10px 14px;">Priority</td><td style="color:#3b82f6;padding:10px 14px;">{priority}</td></tr>
      <tr><td style="color:#888;padding:10px 14px;">Treating Doctor</td><td style="color:#fff;padding:10px 14px;">{doctor}</td></tr>
      <tr><td style="color:#888;padding:10px 14px;">Follow-up</td><td style="color:#10b981;padding:10px 14px;">{follow_up_date} ({follow_up_type})</td></tr>
    </table>
    <div style="background:#052e16;border:1px solid #059669;border-radius:8px;padding:14px;margin-bottom:20px;">
      <div style="color:#6ee7b7;font-weight:bold;margin-bottom:6px;">All discharge criteria met</div>
      <div style="color:#94a3b8;font-size:13px;">Vitals stable, pain controlled, medications prescribed, follow-up scheduled, discharge summary complete.</div>
    </div>
    <p style="color:#64748b;font-size:12px;text-align:center;">
      ShadowGate | {HOSPITAL_NAME}
    </p>
  </div>
</div></body></html>"""

        if SMTP_USER and SMTP_PASS and HEAD_OF_DEPT_EMAIL:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = HEAD_OF_DEPT_EMAIL
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, HEAD_OF_DEPT_EMAIL, msg.as_string())
            print(f"   Discharge notification sent to Head of Department")

        # Slack to healthcare team
        if SLACK_WEBHOOK:
            msg = {
                "text": f"Patient {patient_name} discharged",
                "attachments": [{
                    "color": "good",
                    "blocks": [
                        {"type": "header", "text": {"type": "plain_text", "text": f"Patient Discharged Safely"}},
                        {"type": "section", "fields": [
                            {"type": "mrkdwn", "text": f"*Patient:* {patient_name}"},
                            {"type": "mrkdwn", "text": f"*Doctor:* {doctor}"},
                            {"type": "mrkdwn", "text": f"*Priority:* {priority}"},
                            {"type": "mrkdwn", "text": f"*Follow-up:* {follow_up_date}"}
                        ]},
                        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"ShadowGate | {HOSPITAL_NAME} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}]}
                    ]
                }]
            }
            req.post(SLACK_WEBHOOK, json=msg, timeout=10)
            print(f"   Discharge Slack notification sent")

    except Exception as e:
        print(f"   Discharge notification error: {e}")


@app.route("/api/update_status", methods=["POST"])
def update_status():
    """Update patient status from approval server."""
    data = request.json
    patient_id = data.get("patient_id")
    status = data.get("status")
    detail = data.get("detail", "")

    if patient_id and patient_id in pipeline_results:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update all provided fields
        pipeline_results[patient_id]["current_status"] = data.get("current_status", status)
        pipeline_results[patient_id]["last_updated"] = now

        if "requires_head_approval" in data:
            pipeline_results[patient_id]["requires_head_approval"] = data["requires_head_approval"]

        if "discharge_status" in data:
            pipeline_results[patient_id]["discharge_status"] = data["discharge_status"]

        # Update patient message based on new status
        new_status = data.get("current_status", status)
        if new_status == "under_treatment":
            pipeline_results[patient_id]["patient_message"] = "Your treatment plan has been approved by the Head of Department. Your doctor has been notified and will see you shortly."
        elif new_status == "discharged":
            pass  # Keep CARA message

        if "timeline" not in pipeline_results[patient_id]:
            pipeline_results[patient_id]["timeline"] = []

        status_labels = {
            "approved": "Head of Department Approved",
            "meeting_requested": "Meeting Requested with Chief Doctor",
            "discharged": "Discharged Safely",
            "under_treatment": "Under Treatment"
        }

        pipeline_results[patient_id]["timeline"].append({
            "status": status_labels.get(status, status.title()),
            "detail": detail,
            "time": now
        })

        print(f"   Status updated for {pipeline_results[patient_id].get('patient_name')}: {status}")
        return jsonify({"status": "updated"})
    return jsonify({"status": "not_found"}), 404


@app.route("/api/dashboard")
def get_dashboard_data():
    """Get current dashboard data."""
    try:
        with open("dashboard/dashboard_data.json") as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify({"status": "no_data"})


def run_pipeline_for_patient(patient):
    """Run ShadowGate pipeline for a single patient."""
    try:
        from hospital.automations.aria import ARIA
        from hospital.automations.safe import SAFE
        from hospital.automations.guardian import GUARDIAN
        from hospital.automations.cara import CARA
        from notifications.hospital_alerts import run_hospital_alerts

        # Run ARIA, SAFE, GUARDIAN first
        aria = ARIA()
        aria_output = aria.process([patient])
        aria_results = aria_output.get("results", [])

        safe = SAFE()
        safe_output = safe.process([patient], aria_results)
        safe_results = safe_output.get("results", [])

        guardian = GUARDIAN()
        guardian_output = guardian.process([patient], aria_results, safe_results)
        guardian_results = guardian_output.get("results", [])

        # Get results
        aria_result = aria_results[0] if aria_results else {}
        guardian_result = guardian_results[0] if guardian_results else {}
        safe_result = safe_results[0] if safe_results else {}

        priority = aria_result.get("priority", "P4")
        unknown_risks = aria_result.get("unknown_risks", [])
        requires_approval = aria_result.get("requires_head_approval", False)

        # CARA does NOT run on admission for ANY patient
        # Doctor must fill discharge form after treatment
        # This is realistic - you cannot discharge a patient the moment they arrive
        if requires_approval:
            cara_result = {
                "discharge_check": {"status": "PENDING APPROVAL"},
                "patient_message": "Your treatment plan is being reviewed by the Head of Department. You will be notified shortly.",
                "follow_up": None
            }
        else:
            cara_result = {
                "discharge_check": {"status": "UNDER TREATMENT"},
                "patient_message": "You have been assigned to a doctor. Treatment will begin shortly.",
                "follow_up": None
            }
        cara_output = {"results": [cara_result], "processed": 1}

        # Send alerts
        hospital_result = {
            "aria": aria_output,
            "safe": safe_output,
            "guardian": guardian_output,
            "cara": cara_output if not requires_approval else {"results": [], "processed": 0}
        }
        run_hospital_alerts([patient], hospital_result)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doctor = guardian_result.get("doctor_name", "Unknown")
        # Discharge is always PENDING on admission - doctor must fill discharge form
        discharge = "PENDING DISCHARGE FORM"
        requires_approval = aria_result.get("requires_head_approval", False)

        # Build timeline
        timeline = [
            {"status": "Admitted", "detail": "Patient admitted to hospital", "time": now},
            {"status": "Analysed by ARIA", "detail": f"Generated best to worst case scenarios. {len(unknown_risks)} unknown risk(s) found.", "time": now},
            {"status": "Safety Checked by SAFE", "detail": "All treatment scenarios validated for drug interactions and allergies", "time": now},
            {"status": "Doctor Assigned by GUARDIAN", "detail": f"{doctor} assigned based on experience and availability", "time": now},
        ]

        if requires_approval:
            timeline.append({
                "status": "Awaiting Head Approval",
                "detail": "Confidential email sent to Head of Department. Doctor will be notified after approval.",
                "time": now
            })
            current_status = "awaiting_approval"
        else:
            timeline.append({
                "status": "Doctor Notified",
                "detail": f"Slack notification sent to {doctor}. Treatment can begin.",
                "time": now
            })
            current_status = "under_treatment"
        # Note: Discharge only happens after doctor fills discharge form

        pipeline_results[patient["patient_id"]] = {
            "patient_id": patient["patient_id"],
            "patient_name": patient["name"],
            "age": patient["age"],
            "symptoms": patient.get("symptoms", ""),
            "status": "complete",
            "current_status": current_status,
            "priority": priority,
            "unknown_risks": unknown_risks,
            "unknown_risks_count": len(unknown_risks),
            "doctor_assigned": doctor,
            "wait_minutes": guardian_result.get("estimated_wait_minutes", guardian_result.get("wait_minutes", 0)),
            "discharge_status": discharge,
            "patient_message": cara_result.get("patient_message", ""),
            "requires_head_approval": requires_approval,
            "follow_up": cara_result.get("follow_up", {}),
            "timeline": timeline,
            "completed_at": now,
            "last_updated": now
        }

        print(f"\n Pipeline complete for {patient['name']}")
        print(f"   Priority: {priority}")
        print(f"   Unknown risks: {len(unknown_risks)}")
        print(f"   Doctor: {doctor}")
        print(f"   Discharge: {discharge}")
        print(f"   Status: {current_status}")

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        pipeline_results[patient["patient_id"]] = {
            "patient_id": patient["patient_id"],
            "patient_name": patient["name"],
            "status": "error",
            "error": str(e),
            "priority": "ERROR",
            "unknown_risks_count": 0,
            "doctor_assigned": "Error",
            "wait_minutes": 0,
            "discharge_status": "ERROR",
            "requires_head_approval": False,
            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        print(f"\n Pipeline error for {patient['name']}: {e}")
        print(error_detail)


if __name__ == "__main__":
    print("\n ShadowGate Patient Intake API")
    print(" Running on http://localhost:5001")
    print(" Dashboard: open dashboard/index.html\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
