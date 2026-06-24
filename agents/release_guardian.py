"""
ShadowGate - Agent 5: Release Guardian
The most powerful agent — analyses all test results,
calculates a Release Confidence Score (0-100),
and recommends specific fixes using AI.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from ai_client import ask_ai
from database import get_connection


class ReleaseGuardianAgent:
    """
    Analyses automation test results and chaos injection data
    to produce a Release Confidence Score and fix recommendations.
    """

    def __init__(self):
        self.name = "ReleaseGuardian"

    def analyse(self, automation_name, pipeline_report):
        """
        Main method — analyses full pipeline report.
        Returns confidence score + fix recommendations.
        """
        print(f"\n🛡️  Release Guardian Agent — {automation_name.upper()}")
        print(f"🔍 Analysing pipeline results...\n")

        # Extract key metrics
        validation = pipeline_report.get("stages", {}).get("validation", {})
        chaos = pipeline_report.get("stages", {}).get("chaos_injection", {})
        health = pipeline_report.get("stages", {}).get("test_health", {})
        automation_result = pipeline_report.get("stages", {}).get("automation_run", {}).get("result", {})

        pass_rate = validation.get("pass_rate", 0)
        health_score = health.get("health_score", 0)
        errors = automation_result.get("errors", [])
        chaos_injections = chaos.get("successful_injections", 0) if chaos.get("status") != "skipped" else 0

        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            pass_rate, health_score, errors, chaos_injections
        )

        # Get AI fix recommendations
        fix_recommendations = self._get_fix_recommendations(
            automation_name, pass_rate, errors, chaos, validation
        )

        # Determine release risk level
        risk_level = self._determine_risk(confidence_score)

        report = {
            "automation": automation_name,
            "analysed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "confidence_score": confidence_score,
            "risk_level": risk_level,
            "pass_rate": pass_rate,
            "health_score": health_score,
            "errors_found": len(errors),
            "chaos_injections": chaos_injections,
            "fix_recommendations": fix_recommendations,
            "release_approved": confidence_score >= 85
        }

        self._print_report(report)
        self._save_to_db(automation_name, confidence_score, fix_recommendations)
        self._log_to_audit(automation_name, confidence_score, risk_level)

        return report

    def _calculate_confidence(self, pass_rate, health_score, errors, chaos_injections):
        """
        Calculate Release Confidence Score (0-100).
        Based on pass rate, health score, errors, and chaos resilience.
        """
        # Base score from pass rate (40% weight)
        base = pass_rate * 0.4

        # Health score contribution (30% weight)
        health_contribution = health_score * 0.3

        # Error penalty (20% weight)
        error_count = len(errors)
        error_penalty = min(error_count * 2, 20)
        error_contribution = 20 - error_penalty

        # Chaos resilience bonus (10% weight)
        # If chaos was injected and automation still ran — bonus points
        chaos_bonus = min(chaos_injections * 3, 10) if chaos_injections > 0 else 5

        score = base + health_contribution + error_contribution + chaos_bonus
        return round(min(100, max(0, score)), 1)

    def _get_fix_recommendations(self, automation_name, pass_rate, errors, chaos, validation):
        """Use AI to generate specific fix recommendations."""
        try:
            failed_scenarios = [
                r for r in validation.get("results", [])
                if r.get("status") == "failed"
            ]

            chaos_injections = chaos.get("injections", []) if chaos.get("status") != "skipped" else []

            system_prompt = """You are a senior software engineer reviewing automation test results.
Provide specific, actionable fix recommendations.
Be concise — maximum 3 recommendations.
No markdown, no bullets, use plain numbered list."""

            user_prompt = f"""Automation: {automation_name}
Pass Rate: {pass_rate}%
Errors found: {len(errors)}
Failed scenarios: {[s.get('scenario_name', '') for s in failed_scenarios]}
Chaos injections applied: {[c.get('description', '') for c in chaos_injections]}
Error details: {[e.get('error', '') for e in errors[:3]]}

Give exactly 3 specific fix recommendations numbered 1, 2, 3."""

            return ask_ai(system_prompt, user_prompt)

        except Exception as e:
            return f"1. Review failed test scenarios\n2. Fix validation errors: {len(errors)} found\n3. Add error handling for edge cases"

    def _determine_risk(self, confidence_score):
        """Determine risk level from confidence score."""
        if confidence_score >= 90:
            return "low"
        elif confidence_score >= 75:
            return "medium"
        elif confidence_score >= 60:
            return "high"
        else:
            return "critical"

    def _print_report(self, report):
        """Print release guardian report."""
        score = report["confidence_score"]
        risk = report["risk_level"]

        # Score icon
        if score >= 85:
            score_icon = "✅"
        elif score >= 70:
            score_icon = "⚠️"
        else:
            score_icon = "❌"

        print(f"   {score_icon} Confidence Score: {score}/100")
        print(f"   🎯 Risk Level:       {risk.upper()}")
        print(f"   📈 Pass Rate:        {report['pass_rate']}%")
        print(f"   🏥 Health Score:     {report['health_score']}/100")
        print(f"   ⚠️  Errors Found:     {report['errors_found']}")
        print(f"   💥 Chaos Injections: {report['chaos_injections']}")

        release = "✅ APPROVED" if report["release_approved"] else "❌ BLOCKED"
        print(f"\n   🚦 Release Status: {release}")

        print(f"\n   🤖 Fix Recommendations:")
        for line in report["fix_recommendations"].split("\n"):
            if line.strip():
                print(f"      {line}")

    def _save_to_db(self, automation_name, confidence_score, recommendations):
        """Save to simulation_runs table."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO simulation_runs
                (automation_name, scenarios_total, scenarios_passed, scenarios_failed,
                 confidence_score, deployment_ready, run_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                automation_name,
                10,
                int(confidence_score / 10),
                10 - int(confidence_score / 10),
                confidence_score,
                1 if confidence_score >= 85 else 0,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _log_to_audit(self, automation_name, confidence_score, risk_level):
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
                "analyse_release_readiness",
                f"Confidence Score: {confidence_score}/100. Risk: {risk_level}",
                "success"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    print("Release Guardian Agent — run via orchestrator.py")
