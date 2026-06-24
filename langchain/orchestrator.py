"""
ShadowGate - LangChain Orchestration Layer v3
Week 4: Now includes Release Guardian + Deployment Readiness + Slack.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from agents.environment_simulator import EnvironmentSimulatorAgent
from agents.validator import ValidatorAgent
from agents.chaos_agent import ChaosAgent
from agents.test_health import TestHealthAgent
from agents.release_guardian import ReleaseGuardianAgent
from agents.deployment_readiness import DeploymentReadinessAgent
from notifications.slack_notify import send_deployment_notification, send_chaos_alert
from database import get_connection


class ShadowGateOrchestrator:
    """
    Orchestrates all ShadowGate agents.
    Week 4: 6-stage pipeline with Release Guardian + Deployment Readiness.
    """

    def __init__(self):
        self.name = "ShadowGateOrchestrator"
        self.simulator = EnvironmentSimulatorAgent()
        self.validator = ValidatorAgent()
        self.chaos = ChaosAgent()
        self.health = TestHealthAgent()
        self.guardian = ReleaseGuardianAgent()
        self.deployment = DeploymentReadinessAgent()

    def run_pipeline(self, automation_name, requirements, automation_class, inject_chaos=False):
        """
        Full ShadowGate pipeline — 6 stages:
        1. Environment Simulation
        2. Chaos Injection (optional)
        3. Run Automation
        4. Validation
        5. Test Health Scan
        6. Release Guardian Analysis
        """
        print(f"\n{'='*55}")
        print(f"🌑 ShadowGate Pipeline: {automation_name.upper()}")
        if inject_chaos:
            print(f"   💥 CHAOS MODE ENABLED")
        print(f"{'='*55}")

        start_time = datetime.now()
        # Clear old test results for this automation
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM test_results WHERE automation_name = ?", (automation_name,))
            conn.commit()
            conn.close()
        except Exception:
            pass
        pipeline_report = {
            "automation": automation_name,
            "chaos_mode": inject_chaos,
            "started_at": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "stages": {}
        }

        # Stage 1: Environment Simulation
        print(f"\n📍 Stage 1/6: Environment Simulation")
        scenarios = self.simulator.generate_test_scenarios(automation_name, requirements)
        if not scenarios:
            pipeline_report["status"] = "failed"
            return pipeline_report
        pipeline_report["stages"]["environment_simulation"] = {
            "status": "completed",
            "scenarios_generated": len(scenarios.get("scenarios", []))
        }

        # Stage 2: Chaos Injection
        if inject_chaos:
            print(f"\n📍 Stage 2/6: Chaos Injection")
            chaos_report = self.chaos.inject_chaos(automation_name)
            pipeline_report["stages"]["chaos_injection"] = chaos_report
            send_chaos_alert(automation_name, chaos_report)
        else:
            print(f"\n📍 Stage 2/6: Chaos Injection — SKIPPED (normal mode)")
            pipeline_report["stages"]["chaos_injection"] = {"status": "skipped"}

        # Stage 3: Run Automation
        print(f"\n📍 Stage 3/6: Running Automation")
        automation = automation_class()
        automation_result = automation.process()
        pipeline_report["stages"]["automation_run"] = {
            "status": "completed",
            "result": automation_result
        }

        # Stage 4: Validation
        print(f"\n📍 Stage 4/6: Validation")
        validation_report = self.validator.validate(
            automation_name, scenarios, automation_result
        )
        pipeline_report["stages"]["validation"] = validation_report

        # Stage 5: Test Health Scan
        print(f"\n📍 Stage 5/6: Test Health Scan")
        health_report = self.health.scan(automation_name)
        pipeline_report["stages"]["test_health"] = health_report

        # Stage 6: Release Guardian
        print(f"\n📍 Stage 6/6: Release Guardian Analysis")
        guardian_report = self.guardian.analyse(automation_name, pipeline_report)
        pipeline_report["stages"]["release_guardian"] = guardian_report

        # Final metrics
        duration = (datetime.now() - start_time).total_seconds()
        pipeline_report["status"] = "completed"
        pipeline_report["pass_rate"] = validation_report.get("pass_rate", 0)
        pipeline_report["health_score"] = health_report.get("health_score", 0)
        pipeline_report["confidence_score"] = guardian_report.get("confidence_score", 0)
        pipeline_report["duration_seconds"] = round(duration, 2)
        pipeline_report["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._print_pipeline_summary(pipeline_report)
        self._log_to_audit(automation_name, pipeline_report)

        return pipeline_report

    def _print_pipeline_summary(self, report):
        print(f"\n{'='*55}")
        print(f"🏁 Pipeline Complete: {report['automation'].upper()}")
        print(f"{'='*55}")
        print(f"   ⏱️  Duration:         {report.get('duration_seconds', 0)}s")
        print(f"   📈 Pass Rate:        {report.get('pass_rate', 0)}%")
        print(f"   🏥 Health Score:     {report.get('health_score', 0)}/100")
        print(f"   🛡️  Confidence Score: {report.get('confidence_score', 0)}/100")
        chaos = "💥 YES" if report.get("chaos_mode") else "✅ NO"
        print(f"   💥 Chaos Mode:       {chaos}")
        status = "✅ HEALTHY" if report.get("confidence_score", 0) >= 85 else "⚠️  NEEDS ATTENTION"
        print(f"   🎯 Status:           {status}")
        print(f"{'='*55}\n")

    def _log_to_audit(self, automation_name, report):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log
                (timestamp, agent_name, automation_name, action, output_summary, duration_ms, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.name,
                automation_name,
                "run_full_pipeline",
                f"Confidence: {report.get('confidence_score', 0)}/100, Pass: {report.get('pass_rate', 0)}%",
                int(report.get("duration_seconds", 0) * 1000),
                "success" if report.get("confidence_score", 0) >= 85 else "warning"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


def run_all_automations(chaos_mode=False):
    """Run ShadowGate pipeline on all 3 automations + deployment assessment."""
    from data_generator import seed_all
    from database import create_all_tables
    from mock_automations.loan_processing.automation import LoanProcessingAutomation, REQUIREMENTS as LOAN_REQ
    from mock_automations.fraud_detection.automation import FraudDetectionAutomation, REQUIREMENTS as FRAUD_REQ
    from mock_automations.account_onboarding.automation import AccountOnboardingAutomation, REQUIREMENTS as ONBOARD_REQ

    create_all_tables()
    seed_all()

    orchestrator = ShadowGateOrchestrator()
    all_reports = {}
    all_guardian_reports = {}

    automations = [
        ("loan_processing", LOAN_REQ, LoanProcessingAutomation),
        ("fraud_detection", FRAUD_REQ, FraudDetectionAutomation),
        ("account_onboarding", ONBOARD_REQ, AccountOnboardingAutomation),
    ]

    for name, requirements, cls in automations:
        report = orchestrator.run_pipeline(
            name, requirements, cls, inject_chaos=chaos_mode
        )
        all_reports[name] = report
        all_guardian_reports[name] = report.get("stages", {}).get("release_guardian", {})

    # Final deployment readiness assessment
    print(f"\n{'='*55}")
    print(f"🌑 SHADOWGATE — FINAL DEPLOYMENT ASSESSMENT")
    print(f"{'='*55}")

    deployment_report = orchestrator.deployment.assess(all_guardian_reports)

    # Send Slack notification
    print(f"\n📲 Sending Slack notification...")
    send_deployment_notification(deployment_report, all_guardian_reports)

    # Final summary
    print(f"\n{'='*55}")
    print(f"🌑 SHADOWGATE — ALL AUTOMATIONS SUMMARY")
    print(f"{'='*55}")
    for name, report in all_reports.items():
        confidence = report.get("confidence_score", 0)
        icon = "✅" if confidence >= 85 else "⚠️"
        print(f"   {icon} {name.replace('_', ' ').title()}")
        print(f"      Confidence: {confidence}/100 | Pass: {report.get('pass_rate', 0)}%")

    signal = deployment_report.get("signal", "UNKNOWN")
    overall = deployment_report.get("overall_confidence", 0)
    signal_icon = "✅" if signal == "GREEN" else "❌"
    print(f"\n   {signal_icon} DEPLOYMENT SIGNAL: {signal} ({overall}/100)")
    print(f"{'='*55}\n")

    return all_reports, deployment_report


if __name__ == "__main__":
    import sys
    chaos = "--chaos" in sys.argv
    run_all_automations(chaos_mode=chaos)
