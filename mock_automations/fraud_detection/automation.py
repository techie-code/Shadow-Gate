"""
ShadowGate - Mock Automation 2: Fraud Detection
Simulates a UiPath automation that monitors transactions for fraud.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from database import get_connection


class FraudDetectionAutomation:

    def __init__(self):
        self.name = "fraud_detection"
        self.version = "1.0.0"
        self.processed = 0
        self.flagged = 0
        self.confirmed_fraud = 0
        self.escalated = 0
        self.errors = []

    def validate_transaction(self, txn):
        if txn.get("transaction_id") is None:
            return False, "Missing transaction ID"
        if txn.get("customer_id") is None:
            return False, "Missing customer ID"
        try:
            if float(txn.get("amount", 0)) <= 0:
                return False, f"Invalid amount: {txn.get('amount')}"
        except (TypeError, ValueError):
            return False, f"Invalid amount type: {txn.get('amount')}"
        if txn.get("transaction_type") not in ['debit', 'credit', 'transfer']:
            return False, f"Invalid transaction type: {txn.get('transaction_type')}"
        date_val = txn.get("transaction_date", "")
        if not date_val or date_val == "not-a-date" or date_val == "NOT-A-DATE":
            return False, "Malformed transaction date"
        return True, "Valid"

    def assess_fraud_risk(self, txn):
        amount = float(txn.get("amount", 0))
        location = txn.get("location") or ""
        merchant = txn.get("merchant") or ""
        is_fraudulent = txn.get("is_fraudulent", 0)

        high_risk_locations = ['Unknown Location', 'Moscow, RU', 'Lagos, NG']
        high_risk_merchants = ['Unknown Merchant', 'Crypto Exchange', 'Online Casino']

        risk_score = 0
        if amount > 9000:
            risk_score += 3
        if location in high_risk_locations:
            risk_score += 2
        if merchant in high_risk_merchants:
            risk_score += 2
        if is_fraudulent:
            risk_score += 5

        if risk_score >= 8:
            return "critical", "confirmed_fraud", f"Multiple high-risk indicators. Amount: ${amount:.2f}, Location: {location}"
        elif risk_score >= 5:
            return "high", "suspicious_activity", f"Suspicious pattern. Amount: ${amount:.2f}, Merchant: {merchant}"
        elif risk_score >= 3:
            return "medium", "unusual_activity", f"Unusual activity. Amount: ${amount:.2f}"
        else:
            return "low", "routine_check", "Transaction within normal parameters"

    def process(self):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM transactions
            WHERE status IN ('pending', 'completed')
            LIMIT 500
        """)
        transactions = [dict(row) for row in cursor.fetchall()]

        print(f"\n🔍 Fraud Detection Automation v{self.version}")
        print(f"📋 Scanning {len(transactions)} transactions...\n")

        for txn in transactions:
            self.processed += 1

            try:
                is_valid, reason = self.validate_transaction(txn)
                if not is_valid:
                    self.errors.append({
                        "transaction_id": txn.get("transaction_id"),
                        "error": reason
                    })
                    continue

                risk_level, alert_type, description = self.assess_fraud_risk(txn)

                if risk_level in ["critical", "high"]:
                    self.flagged += 1

                    try:
                        cursor.execute("""
                            INSERT INTO fraud_alerts
                            (transaction_id, alert_type, severity, description, created_at, resolved)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            txn["transaction_id"],
                            alert_type,
                            risk_level,
                            description,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            0
                        ))

                        new_status = "blocked" if risk_level == "critical" else "flagged"
                        cursor.execute("""
                            UPDATE transactions SET status = ? WHERE transaction_id = ?
                        """, (new_status, txn["transaction_id"]))

                        if risk_level == "critical":
                            self.confirmed_fraud += 1
                            self.escalated += 1

                    except Exception as db_err:
                        self.errors.append({
                            "transaction_id": txn.get("transaction_id"),
                            "error": f"DB update failed: {db_err}"
                        })
                        continue

            except Exception as e:
                self.errors.append({
                    "transaction_id": txn.get("transaction_id", "unknown"),
                    "error": str(e)
                })
                continue

        conn.commit()
        conn.close()

        print(f"🔍 Scanned:          {self.processed}")
        print(f"🚩 Flagged:          {self.flagged}")
        print(f"🚨 Confirmed Fraud:  {self.confirmed_fraud}")
        print(f"👤 Escalated:        {self.escalated}")
        print(f"⚠️  Errors:           {len(self.errors)}")

        return {
            "automation": self.name,
            "processed": self.processed,
            "flagged": self.flagged,
            "confirmed_fraud": self.confirmed_fraud,
            "escalated": self.escalated,
            "errors": self.errors,
            "fraud_rate": round(self.confirmed_fraud / max(self.processed, 1) * 100, 2),
            "success_rate": round((self.processed - len(self.errors)) / max(self.processed, 1) * 100, 2)
        }


REQUIREMENTS = """
The fraud detection automation:
- Scans all pending and completed transactions
- Validates that transaction_id, customer_id, amount, and transaction_type are present and valid
- amount must be a positive number
- transaction_type must be one of: debit, credit, transfer
- transaction_date must be a valid date format
- Assesses fraud risk based on amount, location, merchant, and known fraud indicators
- Transactions over $9,000 are flagged for structuring detection
- Transactions from high-risk locations (Unknown, Russia, Nigeria) increase risk score
- Transactions at high-risk merchants (Unknown Merchant, Crypto Exchange, Casino) increase risk score
- Critical risk transactions are blocked and escalated to human review
- High risk transactions are flagged for investigation
- All fraud alerts are logged with severity level and description
"""


if __name__ == "__main__":
    automation = FraudDetectionAutomation()
    result = automation.process()
    print(f"\n📊 Result: {result}")
