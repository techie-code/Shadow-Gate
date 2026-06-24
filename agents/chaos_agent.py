"""
ShadowGate - Agent 3: Chaos Agent
Inspired by Netflix's Chaos Monkey.
Deliberately injects realistic failures into automations
to find weaknesses before they hit production.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
from datetime import datetime
from database import get_connection


# ─────────────────────────────────────────
# 6 CHAOS FAILURE TYPES
# ─────────────────────────────────────────

CHAOS_TYPES = {
    "null_spike": {
        "name": "Null Spike",
        "description": "Injects NULL values into critical fields",
        "severity": "high",
        "icon": "💀"
    },
    "schema_change": {
        "name": "Schema Change",
        "description": "Renames or removes critical columns",
        "severity": "critical",
        "icon": "🔀"
    },
    "invalid_values": {
        "name": "Invalid Values",
        "description": "Injects out-of-range or wrong type values",
        "severity": "high",
        "icon": "❌"
    },
    "row_count_drop": {
        "name": "Row Count Drop",
        "description": "Simulates 40% data loss in pipeline",
        "severity": "critical",
        "icon": "📉"
    },
    "type_mismatch": {
        "name": "Type Mismatch",
        "description": "Changes integer fields to strings",
        "severity": "medium",
        "icon": "🔤"
    },
    "api_timeout": {
        "name": "API Timeout",
        "description": "Simulates external API being unavailable",
        "severity": "high",
        "icon": "⏱️"
    }
}


class ChaosAgent:
    """
    Injects realistic failures into automation data
    to test how automations handle unexpected conditions.
    """

    def __init__(self):
        self.name = "ChaosAgent"
        self.injections = []

    def inject_chaos(self, automation_name, chaos_types=None):
        """
        Inject chaos into a specific automation's data.
        chaos_types: list of chaos types to inject, or None for random selection
        Returns chaos report.
        """
        print(f"\n💥 Chaos Agent — {automation_name.upper()}")
        print(f"🎯 Injecting failures to find weaknesses...\n")

        if chaos_types is None:
            # Randomly pick 2-3 chaos types
            chaos_types = random.sample(list(CHAOS_TYPES.keys()), k=random.randint(2, 3))

        results = []

        for chaos_type in chaos_types:
            print(f"   {CHAOS_TYPES[chaos_type]['icon']} Injecting: {CHAOS_TYPES[chaos_type]['name']}")

            result = self._inject(automation_name, chaos_type)
            results.append(result)

            status = "✅ Injected" if result["success"] else "⚠️ Skipped"
            print(f"      → {status}: {result['description']}")

        chaos_report = {
            "automation": automation_name,
            "chaos_injected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_injections": len(results),
            "successful_injections": len([r for r in results if r["success"]]),
            "injections": results
        }

        self._log_to_audit(automation_name, chaos_report)
        self._print_summary(chaos_report)

        return chaos_report

    def _inject(self, automation_name, chaos_type):
        """Inject a specific chaos type into automation data."""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if automation_name == "loan_processing":
                result = self._chaos_loan(cursor, chaos_type)
            elif automation_name == "fraud_detection":
                result = self._chaos_fraud(cursor, chaos_type)
            elif automation_name == "account_onboarding":
                result = self._chaos_onboarding(cursor, chaos_type)
            else:
                result = {"success": False, "description": "Unknown automation"}

            conn.commit()
            conn.close()
            return {**result, "chaos_type": chaos_type, "automation": automation_name}

        except Exception as e:
            return {
                "success": False,
                "chaos_type": chaos_type,
                "automation": automation_name,
                "description": f"Injection failed: {str(e)}"
            }

    def _chaos_loan(self, cursor, chaos_type):
        """Inject chaos into loan applications."""
        if chaos_type == "null_spike":
            cursor.execute("""
                UPDATE loan_applications
                SET credit_score = NULL
                WHERE application_id IN (
                    SELECT application_id FROM loan_applications
                    ORDER BY RANDOM() LIMIT 20
                )
            """)
            return {"success": True, "description": "Set credit_score to NULL for 20 applications"}

        elif chaos_type == "schema_change":
            # Simulate schema change by setting invalid status
            cursor.execute("""
                UPDATE loan_applications
                SET status = 'UNKNOWN_STATUS'
                WHERE application_id IN (
                    SELECT application_id FROM loan_applications
                    ORDER BY RANDOM() LIMIT 15
                )
            """)
            return {"success": True, "description": "Set invalid status values for 15 applications"}

        elif chaos_type == "invalid_values":
            cursor.execute("""
                UPDATE loan_applications
                SET credit_score = 9999
                WHERE application_id IN (
                    SELECT application_id FROM loan_applications
                    ORDER BY RANDOM() LIMIT 10
                )
            """)
            return {"success": True, "description": "Set credit_score to 9999 (out of range) for 10 applications"}

        elif chaos_type == "row_count_drop":
            cursor.execute("""
                DELETE FROM loan_applications
                WHERE application_id IN (
                    SELECT application_id FROM loan_applications
                    ORDER BY RANDOM() LIMIT 40
                )
            """)
            return {"success": True, "description": "Deleted 40% of loan applications (row count drop)"}

        elif chaos_type == "type_mismatch":
            cursor.execute("""
                UPDATE loan_applications
                SET loan_amount = 'NOT_A_NUMBER'
                WHERE application_id IN (
                    SELECT application_id FROM loan_applications
                    ORDER BY RANDOM() LIMIT 10
                )
            """)
            return {"success": True, "description": "Set loan_amount to string value for 10 applications"}

        elif chaos_type == "api_timeout":
            return {"success": True, "description": "Simulated credit score API timeout — 30 applications unprocessable"}

        return {"success": False, "description": "Unknown chaos type"}

    def _chaos_fraud(self, cursor, chaos_type):
        """Inject chaos into transactions."""
        if chaos_type == "null_spike":
            cursor.execute("""
                UPDATE transactions
                SET customer_id = NULL
                WHERE transaction_id IN (
                    SELECT transaction_id FROM transactions
                    ORDER BY RANDOM() LIMIT 40
                )
            """)
            return {"success": True, "description": "Set customer_id to NULL for 40 transactions"}

        elif chaos_type == "schema_change":
            cursor.execute("""
                UPDATE transactions
                SET transaction_type = 'INVALID_TYPE'
                WHERE transaction_id IN (
                    SELECT transaction_id FROM transactions
                    ORDER BY RANDOM() LIMIT 30
                )
            """)
            return {"success": True, "description": "Set invalid transaction_type for 30 transactions"}

        elif chaos_type == "invalid_values":
            cursor.execute("""
                UPDATE transactions
                SET amount = -999.99
                WHERE transaction_id IN (
                    SELECT transaction_id FROM transactions
                    ORDER BY RANDOM() LIMIT 20
                )
            """)
            return {"success": True, "description": "Set negative amounts for 20 transactions"}

        elif chaos_type == "row_count_drop":
            cursor.execute("""
                DELETE FROM transactions
                WHERE transaction_id IN (
                    SELECT transaction_id FROM transactions
                    ORDER BY RANDOM() LIMIT 80
                )
            """)
            return {"success": True, "description": "Deleted 40% of transactions (row count drop)"}

        elif chaos_type == "type_mismatch":
            cursor.execute("""
                UPDATE transactions
                SET transaction_date = 'NOT-A-DATE'
                WHERE transaction_id IN (
                    SELECT transaction_id FROM transactions
                    ORDER BY RANDOM() LIMIT 25
                )
            """)
            return {"success": True, "description": "Set malformed dates for 25 transactions"}

        elif chaos_type == "api_timeout":
            return {"success": True, "description": "Simulated fraud scoring API timeout — 50 transactions unscored"}

        return {"success": False, "description": "Unknown chaos type"}

    def _chaos_onboarding(self, cursor, chaos_type):
        """Inject chaos into customer onboarding."""
        if chaos_type == "null_spike":
            cursor.execute("""
                UPDATE customers
                SET kyc_verified = NULL
                WHERE customer_id IN (
                    SELECT customer_id FROM customers
                    ORDER BY RANDOM() LIMIT 15
                )
            """)
            return {"success": True, "description": "Set kyc_verified to NULL for 15 customers"}

        elif chaos_type == "schema_change":
            cursor.execute("""
                UPDATE customers
                SET account_type = 'INVALID_ACCOUNT'
                WHERE customer_id IN (
                    SELECT customer_id FROM customers
                    ORDER BY RANDOM() LIMIT 10
                )
            """)
            return {"success": True, "description": "Set invalid account_type for 10 customers"}

        elif chaos_type == "invalid_values":
            cursor.execute("""
                UPDATE customers
                SET email = 'not-an-email'
                WHERE customer_id IN (
                    SELECT customer_id FROM customers
                    ORDER BY RANDOM() LIMIT 12
                )
            """)
            return {"success": True, "description": "Set malformed emails for 12 customers"}

        elif chaos_type == "row_count_drop":
            cursor.execute("""
                DELETE FROM customers
                WHERE customer_id IN (
                    SELECT customer_id FROM customers
                    ORDER BY RANDOM() LIMIT 20
                )
            """)
            return {"success": True, "description": "Deleted 40% of customers (row count drop)"}

        elif chaos_type == "type_mismatch":
            cursor.execute("""
                UPDATE customers
                SET phone = NULL
                WHERE customer_id IN (
                    SELECT customer_id FROM customers
                    ORDER BY RANDOM() LIMIT 8
                )
            """)
            return {"success": True, "description": "Set phone to NULL for 8 customers"}

        elif chaos_type == "api_timeout":
            return {"success": True, "description": "Simulated KYC verification API timeout — 20 customers unverifiable"}

        return {"success": False, "description": "Unknown chaos type"}

    def _print_summary(self, report):
        """Print chaos injection summary."""
        print(f"\n💥 Chaos Summary for {report['automation']}:")
        print(f"   🎯 Injections attempted: {report['total_injections']}")
        print(f"   ✅ Successful:           {report['successful_injections']}")
        print(f"\n   Failure types injected:")
        for injection in report["injections"]:
            icon = CHAOS_TYPES.get(injection["chaos_type"], {}).get("icon", "💥")
            severity = CHAOS_TYPES.get(injection["chaos_type"], {}).get("severity", "medium")
            print(f"   {icon} [{severity.upper()}] {injection['description']}")

    def _log_to_audit(self, automation_name, report):
        """Log chaos injection to audit trail."""
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
                "inject_chaos",
                f"Injected {report['successful_injections']} chaos types: {[i['chaos_type'] for i in report['injections']]}",
                "success"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    from database import create_all_tables
    from data_generator import seed_all

    # Setup fresh data
    create_all_tables()
    seed_all()

    # Test chaos on loan processing
    agent = ChaosAgent()

    # Inject specific chaos types for demo
    report = agent.inject_chaos("loan_processing", [
        "null_spike",
        "schema_change",
        "row_count_drop"
    ])

    print(f"\n🎉 Chaos Agent working!")
    print(f"Now run the automation and watch it struggle with the injected failures.")
