"""
ShadowGate - Approval Server
Simple Flask server that receives Head of Department approval clicks.
When Head clicks button in email, this server receives it and sends Slack to doctor.

Run this alongside main.py:
  python notifications/approval_server.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Store pending approvals in memory
# In production this would be a database
pending_approvals = {}


@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>ShadowGate Approval Server</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0a0a0a; color: #ffffff; padding: 40px; }
            h1 { color: #1DB954; }
            .status { background: #1a1a1a; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .pending { color: #FFA500; }
            .approved { color: #1DB954; }
        </style>
    </head>
    <body>
        <h1>ShadowGate Approval Server</h1>
        <div class="status">
            <p>Server is running and ready to receive approvals.</p>
            <p>Pending approvals: <span class="pending">""" + str(len(pending_approvals)) + """</span></p>
        </div>
        <p>This server receives Head of Department approval clicks from emails.</p>
    </body>
    </html>
    """


@app.route("/approve/<patient_id>/<scenario>")
def approve(patient_id, scenario):
    """
    Called when Head of Department clicks approval button in email.
    Receives: patient_id and scenario (best_case, moderate_case, worst_case)
    Sends: Slack notification to assigned doctor
    """
    print(f"\n APPROVAL RECEIVED")
    print(f"   Patient ID: {patient_id}")
    print(f"   Approved scenario: {scenario}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Get pending approval data
    approval_data = pending_approvals.get(patient_id)

    if not approval_data:
        return """
        <html>
        <head>
            <title>ShadowGate - Already Processed</title>
            <style>
                body { font-family: Arial, sans-serif; background: #0a0a0a; color: #ffffff;
                       display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .card { background: #1a1a1a; padding: 40px; border-radius: 12px; text-align: center; max-width: 500px; }
                h2 { color: #FFA500; }
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Already Processed</h2>
                <p>This approval has already been processed or has expired.</p>
            </div>
        </body>
        </html>
        """

    patient = approval_data.get("patient", {})
    assignment = approval_data.get("assignment", {})
    scenarios = approval_data.get("scenarios", {})
    doctor_name = approval_data.get("doctor_name",
                  assignment.get("doctor_name", "Unknown"))
    priority = approval_data.get("priority", "P4")

    patient_name = patient.get("name", "Unknown")
    approved_scenario = scenarios.get(scenario, {})
    scenario_label = scenario.replace("_", " ").title()

    # Make sure assignment has doctor name
    if "doctor_name" not in assignment:
        assignment["doctor_name"] = doctor_name

    # Send Slack to doctor NOW
    from notifications.hospital_alerts import send_doctor_slack_notification
    send_doctor_slack_notification(patient, assignment, approved_scenario)

    # Mark as processed
    pending_approvals[patient_id]["approved"] = True
    pending_approvals[patient_id]["approved_scenario"] = scenario
    pending_approvals[patient_id]["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"   Slack sent to {doctor_name}")
    print(f"   Approved: {scenario_label}")

    # Return confirmation page to Head of Department
    return f"""
    <html>
    <head>
        <title>ShadowGate - Approval Confirmed</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #0a0a0a;
                color: #ffffff;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .card {{
                background: #1a1a1a;
                padding: 40px;
                border-radius: 12px;
                text-align: center;
                max-width: 500px;
                border: 1px solid #1DB954;
            }}
            h2 {{ color: #1DB954; }}
            .detail {{ background: #0a0a0a; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: left; }}
            .label {{ color: #888; font-size: 12px; margin-bottom: 4px; }}
            .value {{ color: #ffffff; font-size: 16px; }}
            .tick {{ font-size: 48px; color: #1DB954; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="tick">✓</div>
            <h2>Approval Confirmed</h2>
            <div class="detail">
                <div class="label">Patient</div>
                <div class="value">{patient_name}</div>
            </div>
            <div class="detail">
                <div class="label">Priority</div>
                <div class="value">{priority}</div>
            </div>
            <div class="detail">
                <div class="label">Approved Treatment</div>
                <div class="value">{scenario_label}</div>
            </div>
            <div class="detail">
                <div class="label">Doctor Notified</div>
                <div class="value">{doctor_name}</div>
            </div>
            <div class="detail">
                <div class="label">Time</div>
                <div class="value">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
            </div>
            <p style="color: #888; font-size: 12px; margin-top: 20px;">
                {doctor_name} has been notified via Slack with the approved treatment plan.
            </p>
        </div>
    </body>
    </html>
    """


@app.route("/register", methods=["POST"])
def register_approval():
    """Register a pending approval from the alert system."""
    data = request.json
    patient_id = data.get("patient_id")
    if patient_id:
        pending_approvals[patient_id] = data
        return jsonify({"status": "registered", "patient_id": patient_id})
    return jsonify({"status": "error", "message": "No patient_id"}), 400


@app.route("/status/<patient_id>")
def get_status(patient_id):
    """Check approval status for a patient."""
    data = pending_approvals.get(patient_id)
    if not data:
        return jsonify({"status": "not_found"})
    return jsonify({
        "status": "approved" if data.get("approved") else "pending",
        "patient_id": patient_id,
        "approved_scenario": data.get("approved_scenario"),
        "approved_at": data.get("approved_at")
    })


def start_server(port=5000):
    """Start approval server in background thread."""
    import time

    def run():
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    time.sleep(1.5)  # Wait for server to bind
    print(f"   Approval server running at http://localhost:{port}")
    print(f"   Head of Department approval links will open this server")
    return thread


if __name__ == "__main__":
    print("\n ShadowGate Approval Server")
    print(" Starting on http://localhost:5000")
    print(" Press Ctrl+C to stop\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
