"""
ShadowGate - Agent 4: Test Health Agent
Scans existing test results and flags:
- Fragile tests (failed 3+ times recently)
- Outdated tests (no longer relevant to current automation)
- Redundant tests (duplicate coverage)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from ai_client import ask_ai
from database import get_connection


class TestHealthAgent:
    """
    Analyses test history to find fragile, outdated,
    and redundant tests before they slow down a release.
    """

    def __init__(self):
        self.name = "TestHealthAgent"

    def scan(self, automation_name):
        """
        Scan test results for an automation.
        Returns health report with flagged tests.
        """
        print(f"\n🏥 Test Health Agent — {automation_name.upper()}")
        print(f"🔍 Scanning test suite for issues...\n")

        # Get test history from DB
        test_history = self._get_test_history(automation_name)

        if not test_history:
            print(f"   ℹ️  No test history found for {automation_name}")
            return self._empty_report(automation_name)

        # Analyse health
        fragile = self._find_fragile_tests(test_history)
        outdated = self._find_outdated_tests(automation_name, test_history)
        redundant = self._find_redundant_tests(test_history)

        # Generate AI health summary
        health_summary = self._generate_health_summary(
            automation_name, test_history, fragile, outdated, redundant
        )

        report = {
            "automation": automation_name,
            "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(test_history),
            "fragile_tests": fragile,
            "outdated_tests": outdated,
            "redundant_tests": redundant,
            "health_score": self._calculate_health_score(test_history, fragile, outdated),
            "ai_summary": health_summary
        }

        self._print_report(report)
        self._save_report(automation_name, report)
        self._log_to_audit(automation_name, report)

        return report

    def _get_test_history(self, automation_name):
        """Get test results from database."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT test_name, status, confidence_score, failure_reason, executed_at
                FROM test_results
                WHERE automation_name = ?
                ORDER BY executed_at DESC
            """, (automation_name,))
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception:
            return []

    def _find_fragile_tests(self, test_history):
        """Find tests that fail frequently."""
        from collections import defaultdict
        test_failures = defaultdict(int)
        test_total = defaultdict(int)

        for test in test_history:
            test_total[test["test_name"]] += 1
            if test["status"] == "failed":
                test_failures[test["test_name"]] += 1

        fragile = []
        for test_name, failures in test_failures.items():
            total = test_total[test_name]
            failure_rate = failures / max(total, 1)
            if failure_rate >= 0.5:  # Fails 50%+ of the time
                fragile.append({
                    "test_name": test_name,
                    "failure_rate": round(failure_rate * 100, 1),
                    "failures": failures,
                    "total_runs": total,
                    "recommendation": "Review and fix or remove this test"
                })

        return fragile

    def _find_outdated_tests(self, automation_name, test_history):
        """Find tests that may no longer be relevant."""
        outdated = []

        # Load current scenarios to compare
        scenario_file = f"tests/generated/{automation_name}_scenarios.json"
        try:
            with open(scenario_file) as f:
                current_scenarios = json.load(f)
            current_names = {s["name"] for s in current_scenarios.get("scenarios", [])}

            # Tests not in current scenarios are potentially outdated
            for test in test_history:
                if test["test_name"] not in current_names:
                    outdated.append({
                        "test_name": test["test_name"],
                        "last_run": test["executed_at"],
                        "recommendation": "Test no longer matches current automation requirements"
                    })
        except Exception:
            pass

        return outdated

    def _find_redundant_tests(self, test_history):
        """Find tests with duplicate coverage."""
        seen_names = set()
        redundant = []

        for test in test_history:
            name = test["test_name"].lower().strip()
            if name in seen_names:
                redundant.append({
                    "test_name": test["test_name"],
                    "recommendation": "Duplicate test — consider consolidating"
                })
            seen_names.add(name)

        return redundant

    def _calculate_health_score(self, test_history, fragile, outdated):
        """Calculate overall test suite health score (0-100)."""
        if not test_history:
            return 0

        total = len(test_history)
        passed = len([t for t in test_history if t["status"] == "passed"])
        pass_rate = passed / max(total, 1)

        # Deduct for fragile and outdated tests
        fragile_penalty = len(fragile) * 5
        outdated_penalty = len(outdated) * 3

        score = (pass_rate * 100) - fragile_penalty - outdated_penalty
        return max(0, min(100, round(score, 1)))

    def _generate_health_summary(self, automation_name, test_history, fragile, outdated, redundant):
        """Use AI to generate a plain English health summary."""
        try:
            system_prompt = """You are a QA health analyst.
Summarize the test suite health in 2-3 sentences.
Be direct and actionable. No markdown."""

            user_prompt = f"""Automation: {automation_name}
Total tests: {len(test_history)}
Passed: {len([t for t in test_history if t['status'] == 'passed'])}
Failed: {len([t for t in test_history if t['status'] == 'failed'])}
Fragile tests: {len(fragile)}
Outdated tests: {len(outdated)}
Redundant tests: {len(redundant)}

Give a 2-3 sentence health summary and top recommendation."""

            return ask_ai(system_prompt, user_prompt)
        except Exception:
            return f"Test suite has {len(test_history)} tests. {len(fragile)} fragile and {len(outdated)} outdated tests found."

    def _print_report(self, report):
        """Print health report."""
        score = report["health_score"]
        icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"

        print(f"   {icon} Health Score: {score}/100")
        print(f"   📊 Total Tests: {report['total_tests']}")

        if report["fragile_tests"]:
            print(f"\n   🔴 Fragile Tests ({len(report['fragile_tests'])}):")
            for t in report["fragile_tests"]:
                print(f"      • {t['test_name']} — {t['failure_rate']}% failure rate")

        if report["outdated_tests"]:
            print(f"\n   🟡 Outdated Tests ({len(report['outdated_tests'])}):")
            for t in report["outdated_tests"][:3]:
                print(f"      • {t['test_name']}")

        if report["redundant_tests"]:
            print(f"\n   🔵 Redundant Tests ({len(report['redundant_tests'])}):")
            for t in report["redundant_tests"][:3]:
                print(f"      • {t['test_name']}")

        print(f"\n   🤖 AI Summary:")
        print(f"      {report['ai_summary']}")

    def _save_report(self, automation_name, report):
        """Save health report to file."""
        os.makedirs("tests/health_reports", exist_ok=True)
        filename = f"tests/health_reports/{automation_name}_health.json"
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n   💾 Report saved to {filename}")

    def _empty_report(self, automation_name):
        return {
            "automation": automation_name,
            "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": 0,
            "fragile_tests": [],
            "outdated_tests": [],
            "redundant_tests": [],
            "health_score": 0,
            "ai_summary": "No test history found. Run the pipeline first to generate test results."
        }

    def _log_to_audit(self, automation_name, report):
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
                "scan_test_health",
                f"Health score: {report['health_score']}/100. Fragile: {len(report['fragile_tests'])}, Outdated: {len(report['outdated_tests'])}",
                "success"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    from database import create_all_tables
    from data_generator import seed_all
    from langchain.orchestrator import run_all_automations

    # First run pipeline to generate test history
    print("Running pipeline first to generate test history...")
    run_all_automations()

    # Then scan health
    agent = TestHealthAgent()
    for automation in ["loan_processing", "fraud_detection", "account_onboarding"]:
        agent.scan(automation)

    print("\n🎉 Test Health Agent working!")
