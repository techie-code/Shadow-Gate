"""
ShadowGate - Mock Automation 3: Account Onboarding
Simulates a UiPath automation that onboards new bank customers.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
from datetime import datetime
from database import get_connection


class AccountOnboardingAutomation:

    def __init__(self):
        self.name = "account_onboarding"
        self.version = "1.0.0"
        self.processed = 0
        self.approved = 0
        self.rejected = 0
        self.pending_review = 0
        self.errors = []

    def validate_customer(self, customer):
        if not customer.get("full_name") or len(str(customer["full_name"])) < 2:
            return False, "Invalid or missing full name"
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, customer.get("email") or ""):
            return False, f"Invalid email format: {customer.get('email')}"
        if not customer.get("phone") or len(str(customer["phone"])) < 7:
            return False, "Invalid phone number"
        if not customer.get("date_of_birth"):
            return False, "Missing date of birth"
        if not customer.get("address"):
            return False, "Missing address"
        if customer.get("kyc_verified") is None:
            return False, "KYC verification status missing"
        if customer.get("account_type") not in ['savings', 'current', 'credit']:
            return False, f"Invalid account type: {customer.get('account_type')}"
        return True, "Valid"

    def process_onboarding(self, customer):
        kyc_verified = customer.get("kyc_verified")
        onboarding_status = customer.get("onboarding_status")

        if onboarding_status == "rejected":
            return "rejected", "Application previously rejected"
        if not kyc_verified:
            return "documents_pending", "KYC verification required"
        if onboarding_status in ["initiated", "documents_pending"]:
            return "under_review", "Documents received — under compliance review"
        if onboarding_status == "under_review":
            if customer.get("nationality") in ["US", "UK", "CA", "AU", "DE", "FR"]:
                return "approved", "KYC verified and compliance check passed"
            else:
                return "under_review", "Enhanced due diligence required"
        if onboarding_status == "approved":
            return "approved", "Account already approved and active"
        return "under_review", "Pending review"

    def process(self):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM customers
            WHERE onboarding_status NOT IN ('approved', 'rejected')
        """)
        customers = [dict(row) for row in cursor.fetchall()]

        print(f"\n🏦 Account Onboarding Automation v{self.version}")
        print(f"📋 Processing {len(customers)} customer onboarding requests...\n")

        for customer in customers:
            self.processed += 1

            try:
                is_valid, reason = self.validate_customer(customer)
                if not is_valid:
                    self.errors.append({
                        "customer_id": customer.get("customer_id"),
                        "error": reason
                    })
                    continue

                new_status, explanation = self.process_onboarding(customer)

                try:
                    cursor.execute("""
                        UPDATE customers
                        SET onboarding_status = ?
                        WHERE customer_id = ?
                    """, (new_status, customer["customer_id"]))

                    if new_status == "approved":
                        cursor.execute("""
                            UPDATE bank_accounts
                            SET status = 'active', last_updated = ?
                            WHERE customer_id = ?
                        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), customer["customer_id"]))
                        self.approved += 1
                    elif new_status == "rejected":
                        cursor.execute("""
                            UPDATE bank_accounts
                            SET status = 'suspended'
                            WHERE customer_id = ?
                        """, (customer["customer_id"],))
                        self.rejected += 1
                    else:
                        self.pending_review += 1

                except Exception as db_err:
                    self.errors.append({
                        "customer_id": customer.get("customer_id"),
                        "error": f"DB update failed: {db_err}"
                    })
                    continue

            except Exception as e:
                self.errors.append({
                    "customer_id": customer.get("customer_id", "unknown"),
                    "error": str(e)
                })
                continue

        conn.commit()
        conn.close()

        print(f"✅ Approved:        {self.approved}")
        print(f"❌ Rejected:        {self.rejected}")
        print(f"⏳ Pending Review:  {self.pending_review}")
        print(f"⚠️  Errors:          {len(self.errors)}")

        return {
            "automation": self.name,
            "processed": self.processed,
            "approved": self.approved,
            "rejected": self.rejected,
            "pending_review": self.pending_review,
            "errors": self.errors,
            "success_rate": round((self.processed - len(self.errors)) / max(self.processed, 1) * 100, 2)
        }


REQUIREMENTS = """
The account onboarding automation:
- Processes all customers not yet fully approved or rejected
- Validates full_name (minimum 2 characters), email (valid format), phone, date_of_birth, address
- Validates that kyc_verified is explicitly set (not null)
- account_type must be one of: savings, current, credit
- Customers without KYC verification are moved to documents_pending status
- Customers under review from low-risk nationalities (US, UK, CA, AU, DE, FR) are approved after compliance check
- Customers from other nationalities require enhanced due diligence
- Approved customers have their bank accounts activated
- Rejected customers have their bank accounts suspended
- Invalid customer records are logged as errors
"""


if __name__ == "__main__":
    automation = AccountOnboardingAutomation()
    result = automation.process()
    print(f"\n📊 Result: {result}")
