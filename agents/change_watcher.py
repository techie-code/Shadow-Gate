"""
ShadowGate - Agent 8: Change Watcher
Monitors automation files for changes and determines
which tests need to be re-run based on what changed.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import hashlib
from datetime import datetime
from database import get_connection


WATCH_FILES = {
    "loan_processing": "mock_automations/loan_processing/automation.py",
    "fraud_detection": "mock_automations/fraud_detection/automation.py",
    "account_onboarding": "mock_automations/account_onboarding/automation.py"
}

HASH_STORE = "history/change_hashes.json"


class ChangeWatcherAgent:
    """
    Watches automation files for changes.
    When a change is detected, identifies which tests
    are most critical to re-run.
    """

    def __init__(self):
        self.name = "ChangeWatcher"
        self.hashes = self._load_hashes()

    def check(self, automation_name):
        """
        Check if automation has changed since last run.
        Returns change report.
        """
        print(f"\n👁️  Change Watcher Agent — {automation_name.upper()}")

        file_path = WATCH_FILES.get(automation_name)
        if not file_path or not os.path.exists(file_path):
            print(f"   ⚠️  File not found: {file_path}")
            return self._no_change_report(automation_name)

        # Calculate current hash
        current_hash = self._hash_file(file_path)
        previous_hash = self.hashes.get(automation_name)

        if previous_hash is None:
            # First time seeing this file
            self.hashes[automation_name] = current_hash
            self._save_hashes()
            print(f"   📝 First scan — baseline recorded")
            return self._first_scan_report(automation_name)

        if current_hash == previous_hash:
            print(f"   ✅ No changes detected")
            return self._no_change_report(automation_name)

        # Change detected!
        print(f"   🔔 Change detected in {automation_name}!")

        # Determine what kind of change
        change_analysis = self._analyse_change(file_path, automation_name)

        # Update hash
        self.hashes[automation_name] = current_hash
        self._save_hashes()

        report = {
            "automation": automation_name,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "changed": True,
            "change_type": change_analysis.get("type", "unknown"),
            "affected_areas": change_analysis.get("affected_areas", []),
            "recommended_tests": change_analysis.get("recommended_tests", []),
            "priority": change_analysis.get("priority", "medium")
        }

        self._print_change_report(report)
        self._log_to_audit(automation_name, report)

        return report

    def check_all(self):
        """Check all automations for changes."""
        print(f"\n👁️  Change Watcher — Scanning all automations...")
        results = {}
        for automation_name in WATCH_FILES:
            results[automation_name] = self.check(automation_name)
        return results

    def _hash_file(self, file_path):
        """Calculate MD5 hash of a file."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None

    def _analyse_change(self, file_path, automation_name):
        """Analyse what changed in the file."""
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Simple keyword-based analysis
            affected = []
            recommended = []

            if "validate" in content.lower():
                affected.append("validation logic")
                recommended.append("Run all failure scenarios")

            if "credit_score" in content or "amount" in content or "balance" in content:
                affected.append("business rules")
                recommended.append("Run happy path + edge case scenarios")

            if "def process" in content:
                affected.append("core processing logic")
                recommended.append("Run full test suite")

            if not affected:
                affected = ["general logic"]
                recommended = ["Run smoke tests"]

            return {
                "type": "logic_change",
                "affected_areas": affected,
                "recommended_tests": recommended,
                "priority": "high" if "core processing" in str(affected) else "medium"
            }

        except Exception:
            return {
                "type": "unknown",
                "affected_areas": ["unknown"],
                "recommended_tests": ["Run full test suite"],
                "priority": "high"
            }

    def _load_hashes(self):
        """Load stored file hashes."""
        os.makedirs("history", exist_ok=True)
        try:
            if os.path.exists(HASH_STORE):
                with open(HASH_STORE) as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_hashes(self):
        """Save file hashes to disk."""
        os.makedirs("history", exist_ok=True)
        with open(HASH_STORE, "w") as f:
            json.dump(self.hashes, f, indent=2)

    def _no_change_report(self, automation_name):
        return {
            "automation": automation_name,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "changed": False,
            "change_type": "none",
            "affected_areas": [],
            "recommended_tests": [],
            "priority": "low"
        }

    def _first_scan_report(self, automation_name):
        return {
            "automation": automation_name,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "changed": False,
            "change_type": "first_scan",
            "affected_areas": [],
            "recommended_tests": ["Run full test suite — baseline established"],
            "priority": "low"
        }

    def _print_change_report(self, report):
        print(f"   🔔 Change Type:     {report['change_type']}")
        print(f"   📍 Affected Areas:  {', '.join(report['affected_areas'])}")
        print(f"   🎯 Priority:        {report['priority'].upper()}")
        print(f"   📋 Recommended Tests:")
        for t in report["recommended_tests"]:
            print(f"      • {t}")

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
                "check_for_changes",
                f"Changed: {report['changed']}. Areas: {report['affected_areas']}",
                "success"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    watcher = ChangeWatcherAgent()
    watcher.check_all()
