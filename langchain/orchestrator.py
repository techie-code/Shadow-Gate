"""
ShadowGate - LangChain Orchestration Layer v2
Now includes Chaos Agent + Test Health Agent.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from agents.environment_simulator import EnvironmentSimulatorAgent
from agents.validator import ValidatorAgent
from agents.chaos_agent import ChaosAgent
from agents.test_health import TestHealthAgent
from database import get_connection


class ShadowGateOrchestrator:
    """
    Orchestrates all ShadowGate agents in the right order.
    Week 3: Now includes Chaos + Test Health agents.
    """

    def __init__(self):
        self.name = "ShadowGateOrchestrator"
        self.simulator = EnvironmentSimulatorAgent()
        self.validator = ValidatorAgent()
        self.chaos = ChaosAgent()
        self.health = TestHealthAgent()

    def run_pipeline(self, automation_name, requirements, automation_class, inject_chaos=False):
        """
        Full ShadowGate pipeline:
        1. Generate test scenarios
        2. (Optional) Inject chaos
        3. Run automation
        4. Validate results
        5. Scan test health
        """
        print(f"\n{'='*55}")
        print(f"🌑 ShadowGate Pipeline: {automation_name.upper()}")
        if inject_chaos:
            print(f"   💥 CHAOS MODE ENABLED")
        print(f"{'='*55}")

        start_time = datetime.now()
        pipeline_report = {
            "automation": automation_name,
            "chaos_mode": inject_chaos,
            "started_at": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "stages": {}
        }

        # ── Stage 1: Generate Test Scenarios ──
        print(f"\n📍 Stage 1/5: Environment Simulation")
        scenarios = self.simulator.generate_test_scenarios(automation_name, requirements)
        if not scenarios:
            pipeline_report["status"] = "failed"
            return pipeline_report
        pipeline_report["stages"]["environment_simulation"] = {
            "status": "completed",
            "scenarios_generated": len(scenarios.get("scenarios", []))
        }

        # ── Stage 2: Inject Chaos (optional) ──
        if inject_chaos:
            print(f"\n📍 Stage 2/5: Chaos Injection")
            chaos_report = self.chaos.inject_chaos(automation_name)
            pipeline_report["stages"]["chaos_injection"] = chaos_report
        else:
            print(f"\n📍 Stage 2/5: Chaos Injection — SKIPPED (normal mode)")
            pipeline_report["stages"]["chaos_injection"] = {"status": "skipped"}

        # ── Stage 3: Run Automation ──
        print(f"\n📍 Stage 3/5: Running Automation")
        automation = automation_class()
        automation_result = automation.process()
        pipeline_report["stages"]["automation_run"] = {
            "status": "completed",
            "result": automation_result
        }

        # ── Stage 4: Validate Results ──
        print(f"\n📍 Stage 4/5: Validation")
        validation_report = self.validator.validate(
            automation_name, scenarios, automation_result
        )
        pipeline_report["stages"]["validation"] = validation_report

        # ── Stage 5: Test Health Scan ──
        print(f"\n📍 Stage 5/5: Test Health Scan")
        health_report = self.health.scan(automation_name)
        pipeline_report["stages"]["test_health"] = health_report

        # ── Final Summary ──
        duration = (datetime.now() - start_time).total_seconds()
        pass_rate = validation_report.get("pass_rate", 0)
        health_score = health_report.get("health_score", 0)

        pipeline_report["status"] = "completed"
        pipeline_report["pass_rate"] = pass_rate
        pipeline_report["health_score"] = health_score
        pipeline_report["duration_seconds"] = round(duration, 2)
        pipeline_report["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._print_pipeline_summary(pipeline_report)
        self._log_to_audit(automation_name, pass_rate, health_score, duration)

        return pipeline_report

    def _print_pipeline_summary(self, report):
        """Print final pipeline summary."""
        print(f"\n{'='*55}")
        print(f"🏁 Pipeline Complete: {report['automation'].upper()}")
        print(f"{'='*55}")
        print(f"   ⏱️  Duration:      {report.get('duration_seconds', 0)}s")
        print(f"   📈 Pass Rate:     {report.get('pass_rate', 0)}%")
        print(f"   🏥 Health Score:  {report.get('health_score', 0)}/100")
        chaos = "💥 YES" if report.get("chaos_mode") else "✅ NO"
        print(f"   💥 Chaos Mode:    {chaos}")
        status = "✅ HEALTHY" if report.get('pass_rate', 0) >= 80 else "⚠️  NEEDS ATTENTION"
        print(f"   🎯 Status:        {status}")
        print(f"{'='*55}\n")

    def _log_to_audit(self, automation_name, pass_rate, health_score, duration):
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
                f"Pass rate: {pass_rate}%, Health score: {health_score}/100",
                int(duration * 1000),
                "success" if pass_rate >= 80 else "warning"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


def run_all_automations(chaos_mode=False):
    """Run ShadowGate pipeline on all 3 automations."""
    from data_generator import seed_all
    from database import create_all_tables
    from mock_automations.loan_processing.automation import LoanProcessingAutomation, REQUIREMENTS as LOAN_REQ
    from mock_automations.fraud_detection.automation import FraudDetectionAutomation, REQUIREMENTS as FRAUD_REQ
    from mock_automations.account_onboarding.automation import AccountOnboardingAutomation, REQUIREMENTS as ONBOARD_REQ

    create_all_tables()
    seed_all()

    orchestrator = ShadowGateOrchestrator()
    all_reports = {}

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

    # Final summary
    print(f"\n{'='*55}")
    print(f"🌑 SHADOWGATE — ALL AUTOMATIONS SUMMARY")
    print(f"{'='*55}")
    for name, report in all_reports.items():
        pass_rate = report.get("pass_rate", 0)
        health = report.get("health_score", 0)
        icon = "✅" if pass_rate >= 80 else "⚠️"
        print(f"   {icon} {name.replace('_', ' ').title()}")
        print(f"      Pass Rate: {pass_rate}% | Health: {health}/100")
    print(f"{'='*55}\n")

    return all_reports


if __name__ == "__main__":
    import sys
    chaos = "--chaos" in sys.argv
    run_all_automations(chaos_mode=chaos)
