"""
ShadowGate - Agent 10: Governance Logger
Full audit trail of every agent decision.
Generates governance reports for compliance and oversight.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from database import get_connection


class GovernanceLogger:
    """
    Records and reports on every agent action.
    Provides full audit trail for governance and compliance.
    """

    def __init__(self):
        self.name = "GovernanceLogger"

    def generate_report(self, session_reports=None):
        """
        Generate full governance report from audit log.
        Returns governance report.
        """
        print(f"\n📋 Governance Logger")
        print(f"🔍 Generating audit trail report...\n")

        # Get all audit entries
        audit_entries = self._get_audit_entries()
        session_summary = self._summarise_session(audit_entries)
        agent_activity = self._agent_activity(audit_entries)
        compliance_score = self._calculate_compliance(audit_entries)

        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_actions": len(audit_entries),
            "session_summary": session_summary,
            "agent_activity": agent_activity,
            "compliance_score": compliance_score,
            "audit_entries": audit_entries[-20:]  # Last 20 entries
        }

        self._print_report(report)
        self._save_report(report)

        return report

    def _get_audit_entries(self):
        """Get all audit log entries."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audit_log
                ORDER BY timestamp DESC
                LIMIT 100
            """)
            entries = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return entries
        except Exception:
            return []

    def _summarise_session(self, entries):
        """Summarise current session activity."""
        if not entries:
            return {}

        automations = list(set(e.get("automation_name", "") for e in entries))
        agents = list(set(e.get("agent_name", "") for e in entries))
        successes = len([e for e in entries if e.get("status") == "success"])
        warnings = len([e for e in entries if e.get("status") == "warning"])
        failures = len([e for e in entries if e.get("status") == "failure"])

        return {
            "automations_tested": automations,
            "agents_active": agents,
            "total_actions": len(entries),
            "successes": successes,
            "warnings": warnings,
            "failures": failures,
            "success_rate": round(successes / max(len(entries), 1) * 100, 1)
        }

    def _agent_activity(self, entries):
        """Break down activity by agent."""
        from collections import defaultdict
        activity = defaultdict(lambda: {"actions": 0, "successes": 0, "warnings": 0})

        for entry in entries:
            agent = entry.get("agent_name", "unknown")
            activity[agent]["actions"] += 1
            if entry.get("status") == "success":
                activity[agent]["successes"] += 1
            elif entry.get("status") == "warning":
                activity[agent]["warnings"] += 1

        return dict(activity)

    def _calculate_compliance(self, entries):
        """Calculate overall governance compliance score."""
        if not entries:
            return 0

        # Every action logged = compliant
        # Success rate contributes to compliance
        successes = len([e for e in entries if e.get("status") == "success"])
        rate = successes / max(len(entries), 1)
        return round(rate * 100, 1)

    def _print_report(self, report):
        """Print governance report."""
        summary = report.get("session_summary", {})
        compliance = report.get("compliance_score", 0)

        compliance_icon = "✅" if compliance >= 80 else "⚠️"
        print(f"   {compliance_icon} Compliance Score: {compliance}/100")
        print(f"   📊 Total Actions Logged: {report['total_actions']}")
        print(f"   ✅ Successes: {summary.get('successes', 0)}")
        print(f"   ⚠️  Warnings:  {summary.get('warnings', 0)}")
        print(f"   ❌ Failures:  {summary.get('failures', 0)}")

        print(f"\n   🤖 Agent Activity:")
        for agent, stats in report.get("agent_activity", {}).items():
            print(f"      • {agent}: {stats['actions']} actions, {stats['successes']} successes")

        print(f"\n   📋 Recent Audit Trail (last 5):")
        for entry in report["audit_entries"][:5]:
            status_icon = "✅" if entry.get("status") == "success" else "⚠️"
            print(f"      {status_icon} [{entry.get('timestamp', '')[:16]}] "
                  f"{entry.get('agent_name', '')} → {entry.get('action', '')}")

    def _save_report(self, report):
        """Save governance report to file."""
        os.makedirs("governance", exist_ok=True)
        filename = f"governance/governance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n   💾 Governance report saved to {filename}")


if __name__ == "__main__":
    logger = GovernanceLogger()
    logger.generate_report()
