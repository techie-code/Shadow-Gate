"""
ShadowGate - Mock Automation 1: Loan Processing
Simulates a UiPath automation that processes loan applications.
This is what ShadowGate will test.
"""

import sqlite3
import random
from datetime import datetime
from database import get_connection


class LoanProcessingAutomation:
    """
    Simulates the loan processing automation.
    Reads applications, validates data, makes decisions.
    """

    def __init__(self):
        self.name = "loan_processing"
        self.version = "1.0.0"
        self.processed = 0
        self.approved = 0
        self.rejected = 0
        self.escalated = 0
        self.errors = []

    def validate_application(self, app):
        """Validate a loan application — returns (is_valid, reason)."""
        if app["customer_id"] is None:
            return False, "Missing customer ID"
        if app["credit_score"] is None:
            return False, "Missing credit score"
        if not (300 <= app["credit_score"] <= 850):
            return False, f"Invalid credit score: {app['credit_score']}"
        if app["annual_income"] is None or app["annual_income"] <= 0:
            return False, f"Invalid annual income: {app['annual_income']}"
        if app["loan_amount"] is None or app["loan_amount"] <= 0:
            return False, f"Invalid loan amount: {app['loan_amount']}"
        if app["loan_type"] not in ['personal', 'home', 'auto', 'business']:
            return False, f"Invalid loan type: {app['loan_type']}"
        return True, "Valid"

    def make_decision(self, app):
        """Make a loan decision based on application data."""
        credit_score = app["credit_score"]
        income = app["annual_income"]
        loan_amount = app["loan_amount"]

        # Debt-to-income ratio check
        monthly_payment = loan_amount / 60  # 5 year term
        monthly_income = income / 12
        dti_ratio = monthly_payment / monthly_income

        if credit_score >= 750 and dti_ratio < 0.3:
            return "approved", "Excellent credit and healthy DTI ratio"
        elif credit_score >= 650 and dti_ratio < 0.4:
            return "approved", "Good credit score and acceptable DTI ratio"
        elif credit_score >= 580 and dti_ratio < 0.5:
            return "escalated", "Borderline credit score — requires manual review"
        else:
            return "rejected", f"Credit score {credit_score} too low or DTI ratio {dti_ratio:.2f} too high"

    def process(self):
        """Run the loan processing automation."""
        conn = get_connection()
        cursor = conn.cursor()

        # Fetch pending applications
        cursor.execute("""
            SELECT * FROM loan_applications WHERE status = 'pending'
        """)
        applications = [dict(row) for row in cursor.fetchall()]

        print(f"\n🏦 Loan Processing Automation v{self.version}")
        print(f"📋 Processing {len(applications)} pending applications...\n")

        for app in applications:
            self.processed += 1

            # Validate
            is_valid, reason = self.validate_application(app)

            if not is_valid:
                self.errors.append({
                    "application_id": app["application_id"],
                    "error": reason
                })
                continue

            # Make decision
            decision, explanation = self.make_decision(app)

            # Update application status
            cursor.execute("""
                UPDATE loan_applications
                SET status = ?, processed_by = 'automation'
                WHERE application_id = ?
            """, (decision if decision != "escalated" else "under_review", app["application_id"]))

            # Log decision
            cursor.execute("""
                INSERT INTO loan_decisions
                (application_id, decision, reason, decided_at, decided_by)
                VALUES (?, ?, ?, ?, ?)
            """, (
                app["application_id"],
                decision,
                explanation,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "automation" if decision != "escalated" else "pending_human_review"
            ))

            if decision == "approved":
                self.approved += 1
            elif decision == "rejected":
                self.rejected += 1
            else:
                self.escalated += 1

        conn.commit()
        conn.close()

        # Summary
        print(f"✅ Approved:   {self.approved}")
        print(f"❌ Rejected:   {self.rejected}")
        print(f"👤 Escalated:  {self.escalated}")
        print(f"⚠️  Errors:     {len(self.errors)}")

        return {
            "automation": self.name,
            "processed": self.processed,
            "approved": self.approved,
            "rejected": self.rejected,
            "escalated": self.escalated,
            "errors": self.errors,
            "success_rate": round((self.processed - len(self.errors)) / max(self.processed, 1) * 100, 2)
        }


# Plain English requirements — used by Environment Simulator Agent
REQUIREMENTS = """
The loan processing automation:
- Reads all pending loan applications from the database
- Validates that customer_id, credit_score, annual_income, and loan_amount are present and valid
- credit_score must be an integer between 300 and 850
- annual_income must be a positive number
- loan_amount must be a positive number
- loan_type must be one of: personal, home, auto, business
- Makes approval decisions based on credit score and debt-to-income ratio
- Applications with credit score >= 750 and DTI < 0.3 are approved automatically
- Applications with credit score >= 650 and DTI < 0.4 are approved automatically
- Applications with credit score >= 580 and DTI < 0.5 are escalated for human review
- All other applications are rejected
- Every decision is logged with a reason
- Invalid applications are logged as errors
"""


if __name__ == "__main__":
    automation = LoanProcessingAutomation()
    result = automation.process()
    print(f"\n📊 Result: {result}")
