"""
ShadowGate - LangChain Orchestrator
Coordinates all 10 ShadowGate agents to test hospital automations.
Tests ARIA, SAFE, GUARDIAN and CARA.
Discovers unknown risks. Governs decisions. Deploys with confidence.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from datetime import datetime
from database import create_all_tables
from hospital.pipeline import HospitalPipeline, SAMPLE_PATIENTS
from agents.environment_simulator import EnvironmentSimulatorAgent
from agents.validator import ValidatorAgent
from agents.chaos_agent import ChaosAgent
from agents.test_health import TestHealthAgent
from agents.release_guardian import ReleaseGuardianAgent
from agents.deployment_readiness import DeploymentReadinessAgent
from agents.coverage_intelligence import CoverageIntelligenceAgent
from agents.change_watcher import ChangeWatcherAgent
from agents.ai_behavior_validator import AIBehaviorValidatorAgent
from agents.governance_logger import GovernanceLogger
from notifications.slack_notify import send_deployment_notification
from dotenv import load_dotenv

load_dotenv()

AUTOMATIONS = ["ARIA", "SAFE", "GUARDIAN", "CARA"]


def run_shadowgate_pipeline(automation_name, hospital_result):
    """Run all 10 ShadowGate agents to test one hospital automation."""
    print(f"\n{'='*55}")
    print(f" SHADOWGATE PIPELINE: {automation_name}")
    print(f"{'='*55}")

    start_time = time.time()
    governance = GovernanceLogger()

    # Stage 1: Change Detection
    print(f"\n Stage 1/8: Change Detection")
    watcher = ChangeWatcherAgent()
    change_result = watcher.check(automation_name)

    # Stage 2: Environment Simulation
    print(f"\n Stage 2/8: Environment Simulation")
    simulator = EnvironmentSimulatorAgent()
    scenarios = simulator.generate_test_scenarios(automation_name, get_requirements(automation_name))

    # Fallback scenarios if AI unavailable
    if not scenarios:
        scenarios = get_fallback_scenarios(automation_name)
        print(f"   Using fallback scenarios for {automation_name}")

    # Stage 3: Coverage Intelligence
    print(f"\n Stage 3/8: Coverage Intelligence")
    coverage = CoverageIntelligenceAgent()
    safe_scenarios = scenarios if scenarios else {"scenarios": [], "summary": {}}
    coverage_result = coverage.analyse(automation_name, get_requirements(automation_name), safe_scenarios)

    # Stage 4: Chaos Injection
    chaos_mode = os.getenv("SHADOWGATE_CHAOS", "false").lower() == "true"
    print(f"\n Stage 4/8: Chaos Injection {'ACTIVE' if chaos_mode else 'SKIPPED'}")
    chaos_result = {}
    if chaos_mode:
        chaos = ChaosAgent()
        chaos_result = chaos.inject(automation_name)

    # Stage 5: Run Automation
    print(f"\n Stage 5/8: Running {automation_name}")
    automation_result = run_automation(automation_name, hospital_result)

    # Stage 6: Validation
    print(f"\n Stage 6/8: Validation")
    validator = ValidatorAgent()
    validation_result = validator.validate(automation_name, safe_scenarios, automation_result)

    # Stage 7: Test Health
    print(f"\n Stage 7/8: Test Health Scan")
    health = TestHealthAgent()
    health_result = health.scan(automation_name)

    # Stage 8: Release Guardian
    print(f"\n Stage 8/8: Release Guardian Analysis")
    guardian = ReleaseGuardianAgent()

    # Build pipeline report for guardian in correct format
    pipeline_report = {
        "stages": {
            "validation": validation_result,
            "test_health": health_result,
            "automation_run": automation_result,
            "chaos_injection": chaos_result if chaos_result else {"status": "skipped"}
        }
    }
    guardian_result = guardian.analyse(automation_name, pipeline_report)

    # AI Behavior Validation
    print(f"\n AI Behavior Validation")
    ai_validator = AIBehaviorValidatorAgent()
    # Count scenarios for AI behavior validator
    scenario_count = len(safe_scenarios.get("scenarios", []))
    ai_pipeline = {
        "stages": {
            "environment_simulation": {
                "scenarios_generated": scenario_count,
                "scenarios": safe_scenarios.get("scenarios", []),
                "total": scenario_count
            },
            "release_guardian": guardian_result,
            "test_health": health_result
        }
    }
    ai_result = ai_validator.validate(automation_name, ai_pipeline)

    duration = time.time() - start_time

    pass_rate = validation_result.get("pass_rate", 0)
    health_score = health_result.get("health_score", 0)
    confidence = guardian_result.get("confidence_score", 0)
    coverage_score = coverage_result.get("coverage_score", 0)
    ai_score = (ai_result.get("ai_behavior_score") or ai_result.get("behavior_score") or 0)

    report = {
        "automation": automation_name,
        "pass_rate": pass_rate,
        "health_score": health_score,
        "confidence_score": confidence,
        "coverage_score": coverage_score,
        "ai_behavior_score": ai_score,
        "chaos_mode": chaos_mode,
        "errors": automation_result.get("result", {}).get("errors", []),
        "stages": {
            "change_detection": change_result,
            "scenarios": scenarios,
            "coverage": coverage_result,
            "automation_run": automation_result,
            "validation": validation_result,
            "test_health": health_result,
            "release_guardian": guardian_result,
            "ai_behavior": ai_result
        },
        "duration_seconds": round(duration, 2),
        "status": "HEALTHY" if confidence >= 85 else "NEEDS_ATTENTION"
    }

    print(f"\n{'='*55}")
    print(f" Pipeline Complete: {automation_name}")
    print(f"{'='*55}")
    print(f"   Duration:          {duration:.2f}s")
    print(f"   Pass Rate:         {pass_rate}%")
    print(f"   Health Score:      {health_score}/100")
    print(f"   Confidence Score:  {confidence}/100")
    print(f"   Coverage Score:    {coverage_score}/100")
    print(f"   AI Behavior Score: {ai_score}/100")
    print(f"   Status:            {report['status']}")
    print(f"{'='*55}")

    return report


def run_automation(automation_name, hospital_result):
    """Extract results for each automation from hospital pipeline."""
    mapping = {
        "ARIA": "aria",
        "SAFE": "safe",
        "GUARDIAN": "guardian",
        "CARA": "cara"
    }
    key = mapping.get(automation_name, "aria")
    data = hospital_result.get(key, {})
    return {
        "processed": data.get("processed", 3),
        "success_rate": data.get("success_rate", 100),
        "errors": data.get("errors", []),
        "result": {
            "errors": data.get("errors", []),
            "data": data
        }
    }


def get_fallback_scenarios(automation_name):
    """Fallback scenarios when AI is unavailable."""
    base = [
        {"id": "1", "name": f"{automation_name} Happy Path", "type": "happy_path", "priority": "HIGH"},
        {"id": "2", "name": f"{automation_name} Normal Case", "type": "happy_path", "priority": "MEDIUM"},
        {"id": "3", "name": f"{automation_name} Valid Input", "type": "happy_path", "priority": "LOW"},
        {"id": "4", "name": f"{automation_name} Edge Case 1", "type": "edge_case", "priority": "HIGH"},
        {"id": "5", "name": f"{automation_name} Edge Case 2", "type": "edge_case", "priority": "MEDIUM"},
        {"id": "6", "name": f"{automation_name} Boundary Value", "type": "edge_case", "priority": "LOW"},
        {"id": "7", "name": f"{automation_name} Edge Case 4", "type": "edge_case", "priority": "LOW"},
        {"id": "8", "name": f"{automation_name} Missing Fields", "type": "failure", "priority": "HIGH"},
        {"id": "9", "name": f"{automation_name} Invalid Input", "type": "failure", "priority": "MEDIUM"},
        {"id": "10", "name": f"{automation_name} Null Values", "type": "failure", "priority": "LOW"},
    ]
    return {
        "automation": automation_name,
        "scenarios": base,
        "summary": {"happy_path": 3, "edge_case": 4, "failure": 3}
    }


def get_requirements(automation_name):
    """Get plain English requirements for each automation."""
    from hospital.automations.aria import REQUIREMENTS as ARIA_REQ
    from hospital.automations.safe import REQUIREMENTS as SAFE_REQ
    from hospital.automations.guardian import REQUIREMENTS as GUARDIAN_REQ
    from hospital.automations.cara import REQUIREMENTS as CARA_REQ
    reqs = {
        "ARIA": ARIA_REQ,
        "SAFE": SAFE_REQ,
        "GUARDIAN": GUARDIAN_REQ,
        "CARA": CARA_REQ
    }
    return reqs.get(automation_name, "")


def run_all_automations():
    """Run complete ShadowGate hospital testing pipeline."""
    print(f"\n{'='*55}")
    print(f" SHADOWGATE - HOSPITAL AUTOMATION TESTING")
    print(f" Testing: ARIA, SAFE, GUARDIAN, CARA")
    print(f"{'='*55}")

    # Run hospital pipeline first
    print(f"\n Running Hospital Pipeline...")
    pipeline = HospitalPipeline()
    hospital_result = pipeline.run(SAMPLE_PATIENTS)

    # Test each automation with ShadowGate
    all_reports = {}
    for automation_name in AUTOMATIONS:
        report = run_shadowgate_pipeline(automation_name, hospital_result)
        all_reports[automation_name] = report

    # Deployment Readiness
    print(f"\n{'='*55}")
    print(f" SHADOWGATE - FINAL DEPLOYMENT ASSESSMENT")
    print(f"{'='*55}")
    readiness = DeploymentReadinessAgent()
    deployment = readiness.assess(all_reports)

    # Slack Notification
    print(f"\n Sending Slack notification...")
    try:
        send_deployment_notification(deployment, all_reports)
    except Exception as e:
        print(f"   Slack notification: {e}")

    # Governance Report
    print(f"\n{'='*55}")
    print(f" SHADOWGATE - GOVERNANCE REPORT")
    print(f"{'='*55}")
    governance = GovernanceLogger()
    governance.generate_report()

    # Dashboard Export
    export_dashboard(all_reports, deployment, hospital_result)

    # Final Summary
    print(f"\n{'='*55}")
    print(f" SHADOWGATE - ALL AUTOMATIONS SUMMARY")
    print(f"{'='*55}")
    for name, report in all_reports.items():
        status = "HEALTHY" if report['confidence_score'] >= 85 else "NEEDS ATTENTION"
        print(f"   {status}: {name}")
        print(f"      Confidence: {report['confidence_score']}/100 | Pass: {report['pass_rate']}% | Coverage: {report['coverage_score']}/100")

    signal = deployment.get("signal", deployment.get("deployment_signal", "RED"))
    confidence = deployment.get("overall_confidence", 0)
    print(f"\n   DEPLOYMENT SIGNAL: {signal} ({confidence}/100)")
    print(f"{'='*55}")

    # UiPath Integration
    try:
        from uipath.integration import run_uipath_integration
        run_uipath_integration(all_reports)
    except Exception as e:
        print(f"   UiPath integration: {e}")

    # Test Manager Integration
    try:
        from uipath.test_manager import run_test_manager_integration
        run_test_manager_integration(all_reports)
    except Exception as e:
        print(f"   Test Manager: {e}")

    return all_reports, deployment


def export_dashboard(all_reports, deployment, hospital_result):
    """Export dashboard data."""
    os.makedirs("dashboard", exist_ok=True)
    summary = hospital_result.get("summary", {})
    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "deployment_signal": deployment.get("signal", deployment.get("deployment_signal", "RED")),
        "overall_confidence": deployment.get("overall_confidence", 0),
        "automations": {},
        "hospital_summary": summary
    }
    for name, report in all_reports.items():
        data["automations"][name] = {
            "confidence_score": report.get("confidence_score", 0),
            "pass_rate": report.get("pass_rate", 0),
            "health_score": report.get("health_score", 0),
            "coverage_score": report.get("coverage_score", 0),
            "status": report.get("status", "UNKNOWN")
        }
    with open("dashboard/dashboard_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"   Dashboard exported to dashboard/dashboard_data.json")


if __name__ == "__main__":
    create_all_tables()
    run_all_automations()
