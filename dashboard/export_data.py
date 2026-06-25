"""
ShadowGate - Dashboard Data Exporter
Reads latest data from database and writes
dashboard_data.json for the HTML dashboard to consume.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime
from database import get_connection


def export_dashboard_data(pipeline_reports=None):
    """
    Export latest data to dashboard/dashboard_data.json
    Called automatically after each pipeline run.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get latest simulation runs per automation
    cursor.execute("""
        SELECT automation_name, confidence_score, scenarios_passed,
               scenarios_total, deployment_ready, run_at
        FROM simulation_runs
        WHERE run_id IN (
            SELECT MAX(run_id) FROM simulation_runs
            GROUP BY automation_name
        )
    """)
    sim_runs = {row["automation_name"]: dict(row) for row in cursor.fetchall()}

    # Get latest test results per automation
    cursor.execute("""
        SELECT automation_name,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed
        FROM test_results
        WHERE result_id IN (
            SELECT MAX(result_id) FROM test_results
            GROUP BY automation_name, test_name
        )
        GROUP BY automation_name
    """)
    test_results = {row["automation_name"]: dict(row) for row in cursor.fetchall()}

    # Get audit trail
    cursor.execute("""
        SELECT agent_name, automation_name, action, status, timestamp, output_summary
        FROM audit_log
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    audit_entries = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # Build automation data
    automation_names = {
        "loan_processing": {"name": "Loan Processing", "subtitle": "Credit & DTI Validation"},
        "fraud_detection": {"name": "Fraud Detection", "subtitle": "Transaction Monitoring"},
        "account_onboarding": {"name": "Account Onboarding", "subtitle": "KYC & Compliance"}
    }

    automations = []
    for key, info in automation_names.items():
        # Get data from pipeline reports if available
        if pipeline_reports and key in pipeline_reports:
            report = pipeline_reports[key]
            auto_data = {
                "name": info["name"],
                "subtitle": info["subtitle"],
                "confidence_score": report.get("confidence_score", 0),
                "pass_rate": report.get("pass_rate", 0),
                "health_score": report.get("health_score", 0),
                "coverage_score": report.get("coverage_score", 0),
                "ai_behavior_score": report.get("ai_behavior_score", 0),
                "chaos_mode": report.get("chaos_mode", False),
                "duration": report.get("duration_seconds", 0)
            }
        else:
            # Fall back to DB data
            sim = sim_runs.get(key, {})
            results = test_results.get(key, {})
            total = results.get("total", 10)
            passed = results.get("passed", 10)
            pass_rate = round(passed / max(total, 1) * 100, 1)

            auto_data = {
                "name": info["name"],
                "subtitle": info["subtitle"],
                "confidence_score": sim.get("confidence_score", 0),
                "pass_rate": pass_rate,
                "health_score": 100 if pass_rate >= 80 else 60,
                "coverage_score": 100,
                "ai_behavior_score": 100,
                "chaos_mode": False,
                "duration": 0
            }

        automations.append(auto_data)

    # Overall deployment signal
    avg_confidence = sum(a["confidence_score"] for a in automations) / max(len(automations), 1)
    signal = "GREEN" if avg_confidence >= 85 else "RED"

    # Coverage gaps from pipeline reports
    gaps = []
    if pipeline_reports:
        for auto_name, report in pipeline_reports.items():
            coverage = report.get("stages", {}).get("coverage_intelligence", {})
            for gap in coverage.get("gaps_found", []):
                gaps.append({
                    "automation": auto_name.replace("_", " ").title(),
                    "area": gap.get("area", ""),
                    "description": gap.get("description", ""),
                    "risk": gap.get("risk", "medium")
                })

    dashboard_data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "deployment": {
            "signal": signal,
            "overall_confidence": round(avg_confidence, 1)
        },
        "automations": automations,
        "audit": audit_entries,
        "gaps": gaps
    }

    # Save to dashboard folder
    output_path = "dashboard/dashboard_data.json"
    os.makedirs("dashboard", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dashboard_data, f, indent=2)

    print(f"   📊 Dashboard data exported → {output_path}")
    return dashboard_data


if __name__ == "__main__":
    data = export_dashboard_data()
    print(f"\n✅ Dashboard data ready!")
    print(f"   Signal: {data['deployment']['signal']}")
    print(f"   Confidence: {data['deployment']['overall_confidence']}/100")
    print(f"\n   Open dashboard/index.html in your browser to view!")
