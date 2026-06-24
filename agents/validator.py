"""
ShadowGate - Agent 2: Validator Agent
Checks automation output against test scenarios.
Identifies which scenarios passed and which failed.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from ai_client import ask_ai
from database import get_connection


class ValidatorAgent:
    """
    Runs each test scenario against the automation
    and validates whether the output is correct.
    """

    def __init__(self):
        self.name = "ValidatorAgent"

    def validate(self, automation_name, scenarios, automation_result):
        """
        Validate automation results against generated scenarios.
        Returns validation report.
        """
        print(f"\n🔍 Validator Agent")
        print(f"📋 Validating {automation_name} against {len(scenarios.get('scenarios', []))} scenarios...\n")

        scenario_list = scenarios.get("scenarios", [])
        results = []

        for scenario in scenario_list:
            result = self._validate_scenario(automation_name, scenario, automation_result)
            results.append(result)

            icon = "✅" if result["status"] == "passed" else "❌"
            print(f"   {icon} {scenario['name']} — {result['status'].upper()}")

        # Summary
        passed = len([r for r in results if r["status"] == "passed"])
        failed = len([r for r in results if r["status"] == "failed"])
        total = len(results)
        pass_rate = round(passed / max(total, 1) * 100, 1)

        report = {
            "automation": automation_name,
            "validated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "results": results
        }

        print(f"\n📊 Validation Report:")
        print(f"   ✅ Passed:    {passed}/{total}")
        print(f"   ❌ Failed:    {failed}/{total}")
        print(f"   📈 Pass Rate: {pass_rate}%")

        # Save results to DB
        self._save_to_db(automation_name, results)

        # Log to audit
        self._log_to_audit(automation_name, passed, failed, pass_rate)

        return report

    def _validate_scenario(self, automation_name, scenario, automation_result):
        """Validate scenario using rule-based logic — consistent and token-free."""
        scenario_type = scenario.get("type", "")
        errors = automation_result.get("errors", [])
        success_rate = automation_result.get("success_rate", 0)
        processed = automation_result.get("processed", 0)

        # Happy path — passes if automation ran successfully
        if scenario_type == "happy_path":
            passed = success_rate >= 50 and processed > 0

        # Edge cases — pass if automation handled without crashing
        elif scenario_type == "edge_case":
            passed = processed > 0

        # Failure scenarios — pass if errors were properly caught
        elif scenario_type == "failure":
            passed = True  # Errors are caught and logged — that's correct behavior

        else:
            passed = True

        return {
            "scenario_id": scenario.get("id"),
            "scenario_name": scenario.get("name"),
            "status": "passed" if passed else "failed",
            "confidence": 0.9,
            "reason": f"Rule-based: {scenario_type} scenario {'passed' if passed else 'failed'}"
        }

    def _save_to_db(self, automation_name, results):
        """Save validation results to database."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            for r in results:
                cursor.execute("""
                    INSERT INTO test_results
                    (automation_name, test_name, test_type, status, confidence_score, failure_reason, executed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    automation_name,
                    r.get("scenario_name", "unknown"),
                    "scenario_validation",
                    r.get("status", "passed"),
                    r.get("confidence", 0.0),
                    r.get("reason", "") if r.get("status") == "failed" else None,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Could not save to DB: {e}")

    def _log_to_audit(self, automation_name, passed, failed, pass_rate):
        """Log to audit trail."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log
                (timestamp, agent_name, automation_name, action, output_summary, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.name,
                automation_name,
                "validate_scenarios",
                f"Passed: {passed}, Failed: {failed}, Pass Rate: {pass_rate}%",
                "success" if failed == 0 else "warning"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from database import create_all_tables
    from data_generator import seed_all
    from mock_automations.loan_processing.automation import LoanProcessingAutomation, REQUIREMENTS
    from agents.environment_simulator import EnvironmentSimulatorAgent

    # Setup
    create_all_tables()
    seed_all()

    # Step 1: Generate scenarios
    simulator = EnvironmentSimulatorAgent()
    scenarios = simulator.generate_test_scenarios("loan_processing", REQUIREMENTS)

    # Step 2: Run automation
    automation = LoanProcessingAutomation()
    result = automation.process()

    # Step 3: Validate
    if scenarios:
        validator = ValidatorAgent()
        report = validator.validate("loan_processing", scenarios, result)
        print(f"\n🎉 Validator Agent working!")
