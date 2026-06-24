"""
ShadowGate - Agent 6: Deployment Readiness
Final gate before production deployment.
Takes confidence score and gives GREEN or RED signal
with plain English explanation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from ai_client import ask_ai
from database import get_connection


class DeploymentReadinessAgent:
    """
    Final deployment gate.
    Aggregates all automation scores and gives
    a single GREEN or RED deployment decision.
    """

    def __init__(self):
        self.name = "DeploymentReadiness"
        self.threshold = 85  # Minimum confidence score to deploy

    def assess(self, all_guardian_reports):
        """
        Assess deployment readiness across all automations.
        Returns final deployment decision.
        """
        print(f"\n🚦 Deployment Readiness Agent")
        print(f"🔍 Assessing deployment readiness across all automations...\n")

        scores = []
        blockers = []
        warnings = []

        for automation_name, report in all_guardian_reports.items():
            score = report.get("confidence_score", 0)
            risk = report.get("risk_level", "unknown")
            scores.append(score)

            if score < self.threshold:
                blockers.append({
                    "automation": automation_name,
                    "score": score,
                    "risk": risk,
                    "fixes": report.get("fix_recommendations", "")
                })
            elif score < 90:
                warnings.append({
                    "automation": automation_name,
                    "score": score,
                    "risk": risk
                })

        # Overall score = average of all automation scores
        overall_score = round(sum(scores) / max(len(scores), 1), 1)
        deployment_ready = len(blockers) == 0 and overall_score >= self.threshold

        # Generate AI deployment summary
        summary = self._generate_summary(
            overall_score, deployment_ready, blockers, warnings, all_guardian_reports
        )

        report = {
            "assessed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_confidence": overall_score,
            "deployment_ready": deployment_ready,
            "signal": "GREEN" if deployment_ready else "RED",
            "automations_assessed": len(all_guardian_reports),
            "blockers": blockers,
            "warnings": warnings,
            "individual_scores": {
                name: r.get("confidence_score", 0)
                for name, r in all_guardian_reports.items()
            },
            "ai_summary": summary
        }

        self._print_decision(report)
        self._log_to_audit(overall_score, deployment_ready, len(blockers))

        return report

    def _generate_summary(self, score, ready, blockers, warnings, reports):
        """Generate AI plain English deployment summary."""
        try:
            system_prompt = """You are a deployment manager making a final go/no-go decision.
Be direct and decisive. Maximum 3 sentences. No markdown."""

            blocker_text = "\n".join([
                f"- {b['automation']}: score {b['score']}/100 ({b['risk']} risk)"
                for b in blockers
            ]) if blockers else "None"

            warning_text = "\n".join([
                f"- {w['automation']}: score {w['score']}/100"
                for w in warnings
            ]) if warnings else "None"

            user_prompt = f"""Overall confidence: {score}/100
Deployment decision: {'GO' if ready else 'NO-GO'}
Blockers: {blocker_text}
Warnings: {warning_text}

Write a 2-3 sentence deployment decision summary."""

            return ask_ai(system_prompt, user_prompt)

        except Exception:
            if ready:
                return f"All automations passed with {score}/100 confidence. No blockers detected. Safe to deploy to production."
            else:
                return f"Deployment blocked. {len(blockers)} automation(s) below confidence threshold. Resolve blockers before deploying."

    def _print_decision(self, report):
        """Print the final deployment decision."""
        signal = report["signal"]
        score = report["overall_confidence"]

        print(f"\n{'='*55}")
        if signal == "GREEN":
            print(f"   ✅ DEPLOYMENT SIGNAL: GREEN")
            print(f"   🚀 SAFE TO DEPLOY TO PRODUCTION")
        else:
            print(f"   ❌ DEPLOYMENT SIGNAL: RED")
            print(f"   🛑 DO NOT DEPLOY — BLOCKERS FOUND")
        print(f"{'='*55}")

        print(f"\n   📊 Overall Confidence: {score}/100")
        print(f"   🔢 Automations Assessed: {report['automations_assessed']}")

        print(f"\n   📈 Individual Scores:")
        for name, score in report["individual_scores"].items():
            icon = "✅" if score >= 85 else "⚠️" if score >= 70 else "❌"
            print(f"      {icon} {name.replace('_', ' ').title()}: {score}/100")

        if report["blockers"]:
            print(f"\n   🚫 Blockers ({len(report['blockers'])}):")
            for b in report["blockers"]:
                print(f"      ❌ {b['automation'].replace('_', ' ').title()}: {b['score']}/100")
                print(f"         Fix: {b['fixes'][:100]}...")

        if report["warnings"]:
            print(f"\n   ⚠️  Warnings ({len(report['warnings'])}):")
            for w in report["warnings"]:
                print(f"      ⚠️  {w['automation'].replace('_', ' ').title()}: {w['score']}/100")

        print(f"\n   🤖 AI Summary:")
        for line in report["ai_summary"].split("\n"):
            if line.strip():
                print(f"      {line}")

    def _log_to_audit(self, score, ready, blocker_count):
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
                "all_automations",
                "assess_deployment_readiness",
                f"Signal: {'GREEN' if ready else 'RED'}. Score: {score}/100. Blockers: {blocker_count}",
                "success" if ready else "warning"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    print("Deployment Readiness Agent — run via orchestrator.py")
