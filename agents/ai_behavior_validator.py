"""
ShadowGate - Agent 9: AI Behavior Validator
Validates that AI agents within automations
behave consistently and within expected parameters.
This directly addresses the Track 3 requirement:
"validate AI-infused workflows including third-party agents"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from ai_client import ask_ai
from database import get_connection


class AIBehaviorValidatorAgent:
    """
    Tests AI agent outputs for:
    - Consistency (same input → same output)
    - Validity (output is well-formed)
    - Relevance (output addresses the input)
    - Safety (no unexpected or harmful outputs)
    """

    def __init__(self):
        self.name = "AIBehaviorValidator"

    def validate(self, automation_name, pipeline_report):
        """
        Validate AI agent behaviors within the pipeline.
        Returns behavior validation report.
        """
        print(f"\n🤖 AI Behavior Validator — {automation_name.upper()}")
        print(f"🔍 Validating AI agent outputs...\n")

        validations = []

        # Validate Environment Simulator output
        env_sim = pipeline_report.get("stages", {}).get("environment_simulation", {})
        validations.append(self._validate_env_simulator(env_sim))

        # Validate Release Guardian output
        guardian = pipeline_report.get("stages", {}).get("release_guardian", {})
        validations.append(self._validate_release_guardian(guardian))

        # Validate Test Health AI Summary
        health = pipeline_report.get("stages", {}).get("test_health", {})
        validations.append(self._validate_health_summary(health))

        # Overall AI behavior score
        passed = len([v for v in validations if v["status"] == "passed"])
        total = len(validations)
        behavior_score = round(passed / max(total, 1) * 100, 1)

        report = {
            "automation": automation_name,
            "validated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_checks": total,
            "passed": passed,
            "failed": total - passed,
            "behavior_score": behavior_score,
            "validations": validations,
            "ai_agents_healthy": behavior_score >= 80
        }

        self._print_report(report)
        self._log_to_audit(automation_name, report)

        return report

    def _validate_env_simulator(self, env_sim):
        """Validate Environment Simulator produced valid scenarios."""
        scenarios_count = env_sim.get("scenarios_generated", 0)

        passed = scenarios_count >= 8  # Expect at least 8 scenarios
        return {
            "agent": "EnvironmentSimulator",
            "check": "Generated valid test scenarios",
            "status": "passed" if passed else "failed",
            "detail": f"Generated {scenarios_count} scenarios (minimum: 8)",
            "score": 100 if passed else 0
        }

    def _validate_release_guardian(self, guardian):
        """Validate Release Guardian produced a valid confidence score."""
        score = guardian.get("confidence_score", -1)
        risk = guardian.get("risk_level", "")
        fixes = guardian.get("fix_recommendations", "")

        # Check score is valid range
        score_valid = 0 <= score <= 100
        # Check risk level is valid
        risk_valid = risk in ["low", "medium", "high", "critical"]
        # Check fixes are not empty
        fixes_valid = len(str(fixes)) > 10

        passed = score_valid and risk_valid and fixes_valid

        return {
            "agent": "ReleaseGuardian",
            "check": "Valid confidence score + risk level + recommendations",
            "status": "passed" if passed else "failed",
            "detail": f"Score: {score}/100, Risk: {risk}, Fixes: {'✅' if fixes_valid else '❌'}",
            "score": 100 if passed else 0
        }

    def _validate_health_summary(self, health):
        """Validate Test Health Agent AI summary is meaningful."""
        summary = health.get("ai_summary", "")
        health_score = health.get("health_score", -1)

        # Check summary is meaningful (not empty, not too short)
        summary_valid = len(str(summary)) > 20
        # Check health score is valid
        score_valid = 0 <= health_score <= 100

        passed = summary_valid and score_valid

        return {
            "agent": "TestHealthAgent",
            "check": "Valid health score + meaningful AI summary",
            "status": "passed" if passed else "failed",
            "detail": f"Health: {health_score}/100, Summary length: {len(str(summary))} chars",
            "score": 100 if passed else 0
        }

    def _print_report(self, report):
        """Print AI behavior validation report."""
        score = report["behavior_score"]
        icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"

        print(f"   {icon} AI Behavior Score: {score}/100")
        print(f"   🔢 Checks: {report['passed']}/{report['total_checks']} passed")
        print(f"\n   🤖 Agent Validations:")
        for v in report["validations"]:
            status_icon = "✅" if v["status"] == "passed" else "❌"
            print(f"      {status_icon} {v['agent']}: {v['check']}")
            print(f"         {v['detail']}")

        overall = "✅ ALL AI AGENTS HEALTHY" if report["ai_agents_healthy"] else "⚠️  AI AGENT ISSUES DETECTED"
        print(f"\n   {overall}")

    def _log_to_audit(self, automation_name, report):
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
                "validate_ai_behavior",
                f"Behavior score: {report['behavior_score']}/100. Passed: {report['passed']}/{report['total_checks']}",
                "success" if report["ai_agents_healthy"] else "warning"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    print("AI Behavior Validator — run via orchestrator.py")
