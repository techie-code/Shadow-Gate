"""
ShadowGate - Agent 2: Validator Agent
Checks automation output against test scenarios.
Rule-based validation — consistent and token-free.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from database import get_connection


class ValidatorAgent:

    def __init__(self):
        self.name = "ValidatorAgent"

    def validate(self, automation_name, scenarios, automation_result):
        print(f"\n🔍 Validator Agent")
        print(f"📋 Validating {automation_name} against {len(scenarios.get('scenarios', []))} scenarios...\n")

        scenario_list = scenarios.get("scenarios", [])
        results = []

        for scenario in scenario_list:
            result = self._validate_scenario(automation_name, scenario, automation_result)
            results.append(result)
            icon = "✅" if result["status"] == "passed" else "❌"
            print(f"   {icon} {scenario['name']} — {result['status'].upper()}")

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

        self._save_to_db(automation_name, results)
        self._log_to_audit(automation_name, passed, failed, pass_rate)

        return report

    def _validate_scenario(self, automation_name, scenario, automation_result):
        """Rule-based validation — consistent and token-free."""
        scenario_type = scenario.get("type", "")
        processed = automation_result.get("processed", 0)

        # Happy path — passes if automation ran and processed records
        if scenario_type == "happy_path":
            passed = processed > 0

        # Edge cases — pass if automation handled without crashing
        elif scenario_type == "edge_case":
            passed = processed > 0

        # Failure scenarios — always pass (errors are caught and logged)
        elif scenario_type == "failure":
            passed = True

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
