"""
ShadowGate - Mock Automation 2: Fraud Detection
Simulates a UiPath automation that monitors transactions for fraud.
"""

import sqlite3
from datetime import datetime
from database import get_connection


class FraudDetectionAutomation:
    """
    Simulates the fraud detection automation.
    Monitors transactions, flags suspicious activity, escalates confirmed fraud.
    """

    def __init__(self):
        self.name = "fraud_detection"
        self.version = "1.0.0"
        self.processed = 0
        self.flagged = 0
        self.confirmed_fraud = 0
        self.escalated = 0
        self.errors = []

    def validate_transaction(self, txn):
        """Validate a transaction record."""
        if txn["transaction_id"] is None:
            return False, "Missing transaction ID"
        if txn["customer_id"] is None:
            return False, "Missing customer ID"
        if txn["amount"] is None or txn["amount"] <= 0:
            return False, f"Invalid amount: {txn['amount']}"
        if txn["transaction_type"] not in ['debit', 'credit', 'transfer']:
            return False, f"Invalid transaction type: {txn['transaction_type']}"
        if txn["transaction_date"] == "not-a-date":
            return False, "Malformed transaction date"
        return True, "Valid"

    def assess_fraud_risk(self, txn):
        """
        Assess fraud risk of a transaction.
        Returns (risk_level, alert_type, description)
        """
        amount = txn["amount"]
        location = txn["location"] or ""
        merchant = txn["merchant"] or ""
        is_fraudulent = txn["is_fraudulent"]

        # High risk indicators
        high_risk_locations = ['Unknown Location', 'Moscow, RU', 'Lagos, NG']
        high_risk_merchants = ['Unknown Merchant', 'Crypto Exchange', 'Online Casino']

        risk_score = 0

        if amount > 9000:
            risk_score += 3  # Structuring detection
        if location in high_risk_locations:
            risk_score += 2
        if merchant in high_risk_merchants:
            risk_score += 2
        if is_fraudulent:
            risk_score += 5

        if risk_score >= 8:
            return "critical", "confirmed_fraud", f"Multiple high-risk indicators detected. Amount: ${amount:.2f}, Location: {location}"
        elif risk_score >= 5:
            return "high", "suspicious_activity", f"Suspicious transaction pattern. Amount: ${amount:.2f}, Merchant: {merchant}"
        elif risk_score >= 3:
            return "medium", "unusual_activity", f"Unusual activity detected. Amount: ${amount:.2f}"
        else:
            return "low", "routine_check", "Transaction within normal parameters"

    def process(self):
        """Run the fraud detection automation."""
        conn = get_connection()
        cursor = conn.cursor()

        # Fetch recent transactions
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

            # Validate
            is_valid, reason = self.validate_transaction(txn)
            if not is_valid:
                self.errors.append({
                    "transaction_id": txn["transaction_id"],
                    "error": reason
                })
                continue

            # Assess risk
            risk_level, alert_type, description = self.assess_fraud_risk(txn)

            if risk_level in ["critical", "high"]:
                self.flagged += 1

                # Create fraud alert
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

                # Update transaction status
                new_status = "blocked" if risk_level == "critical" else "flagged"
                cursor.execute("""
                    UPDATE transactions SET status = ? WHERE transaction_id = ?
                """, (new_status, txn["transaction_id"]))

                if risk_level == "critical":
                    self.confirmed_fraud += 1
                    self.escalated += 1

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
            "fraud_rate": round(self.confirmed_fraud / max(self.processed, 1) * 100, 2)
        }


# Plain English requirements — used by Environment Simulator Agent
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
