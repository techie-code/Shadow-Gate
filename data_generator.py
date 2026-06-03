"""
ShadowGate - Mock Data Generator
Generates realistic banking data for all 3 automations using Faker.
"""

import sqlite3
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker
from database import get_connection, DB_PATH

fake = Faker()
random.seed(42)
Faker.seed(42)


# ─────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────

def random_date(days_back=365):
    """Generate a random date within the last N days."""
    start = datetime.now() - timedelta(days=days_back)
    delta = timedelta(days=random.randint(0, days_back))
    return (start + delta).strftime("%Y-%m-%d %H:%M:%S")


def random_account_id():
    """Generate a realistic bank account ID."""
    return f"ACC{random.randint(100000, 999999)}"


# ─────────────────────────────────────────────────
# AUTOMATION 1: LOAN PROCESSING DATA
# ─────────────────────────────────────────────────

def generate_loan_applications(count=100, inject_failures=False):
    """
    Generate mock loan applications.
    inject_failures=True simulates broken pipeline data for chaos testing.
    """
    conn = get_connection()
    cursor = conn.cursor()

    loan_types = ['personal', 'home', 'auto', 'business']
    employment_statuses = ['employed', 'self_employed', 'unemployed']
    statuses = ['pending', 'approved', 'rejected', 'under_review']

    applications = []

    for i in range(1, count + 1):
        app = {
            "application_id":   i,
            "customer_id":      random.randint(1000, 9999),
            "full_name":        fake.name(),
            "email":            fake.email(),
            "loan_amount":      round(random.uniform(5000, 500000), 2),
            "loan_type":        random.choice(loan_types),
            "annual_income":    round(random.uniform(20000, 200000), 2),
            "credit_score":     random.randint(300, 850),
            "employment_status": random.choice(employment_statuses),
            "application_date": random_date(180),
            "status":           random.choice(statuses),
            "processed_by":     "automation"
        }

        # Inject failures for chaos testing
        if inject_failures:
            failure_type = random.choice([
                "null_credit_score",
                "invalid_status",
                "negative_income",
                "schema_change",
                "type_mismatch",
                "none"
            ])

            if failure_type == "null_credit_score" and random.random() < 0.3:
                app["credit_score"] = None
            elif failure_type == "invalid_status":
                app["status"] = "unknown_status"
            elif failure_type == "negative_income":
                app["annual_income"] = -1000
            elif failure_type == "type_mismatch":
                app["application_id"] = f"APP{i}"  # String instead of int

        applications.append(app)

    # Clear existing and insert fresh
    cursor.execute("DELETE FROM loan_applications")
    for app in applications:
        try:
            cursor.execute("""
                INSERT INTO loan_applications VALUES (
                    :application_id, :customer_id, :full_name, :email,
                    :loan_amount, :loan_type, :annual_income, :credit_score,
                    :employment_status, :application_date, :status, :processed_by
                )
            """, app)
        except Exception:
            pass  # Intentional failures for chaos scenarios

    conn.commit()
    conn.close()

    inserted = len([a for a in applications if a.get("credit_score") is not None])
    print(f"✅ Loan applications: {inserted}/{count} records inserted")
    return applications


# ─────────────────────────────────────────────────
# AUTOMATION 2: FRAUD DETECTION DATA
# ─────────────────────────────────────────────────

def generate_transactions(count=200, inject_failures=False):
    """
    Generate mock banking transactions.
    inject_failures=True simulates broken pipeline data.
    """
    conn = get_connection()
    cursor = conn.cursor()

    transaction_types = ['debit', 'credit', 'transfer']
    statuses = ['pending', 'completed', 'flagged', 'blocked']
    merchants = [
        'Amazon', 'Walmart', 'Target', 'Shell Gas', 'Starbucks',
        'Netflix', 'Apple Store', 'Unknown Merchant', 'ATM Withdrawal',
        'International Wire', 'Crypto Exchange', 'Online Casino'
    ]
    locations = [
        'New York, US', 'London, UK', 'Lagos, NG', 'Moscow, RU',
        'Tokyo, JP', 'Sydney, AU', 'Dubai, UAE', 'Unknown Location'
    ]

    transactions = []

    for i in range(1, count + 1):
        # Make some transactions suspicious
        is_suspicious = random.random() < 0.15
        amount = round(random.uniform(9000, 15000), 2) if is_suspicious else round(random.uniform(10, 5000), 2)
        location = random.choice(['Unknown Location', 'Moscow, RU', 'Lagos, NG']) if is_suspicious else random.choice(locations)

        txn = {
            "transaction_id":   i,
            "customer_id":      random.randint(1000, 9999),
            "account_id":       random_account_id(),
            "amount":           amount,
            "transaction_type": random.choice(transaction_types),
            "merchant":         random.choice(merchants),
            "location":         location,
            "transaction_date": random_date(90),
            "status":           'flagged' if is_suspicious else random.choice(statuses),
            "is_fraudulent":    1 if is_suspicious and random.random() < 0.5 else 0
        }

        # Inject failures
        if inject_failures:
            failure_type = random.choice([
                "null_transaction_id",
                "duplicate_entry",
                "malformed_date",
                "none", "none", "none"  # weighted towards none
            ])

            if failure_type == "null_transaction_id" and random.random() < 0.2:
                txn["transaction_id"] = None
            elif failure_type == "malformed_date":
                txn["transaction_date"] = "not-a-date"

        transactions.append(txn)

    cursor.execute("DELETE FROM transactions")
    for txn in transactions:
        try:
            cursor.execute("""
                INSERT INTO transactions VALUES (
                    :transaction_id, :customer_id, :account_id, :amount,
                    :transaction_type, :merchant, :location, :transaction_date,
                    :status, :is_fraudulent
                )
            """, txn)
        except Exception:
            pass

    conn.commit()
    conn.close()
    print(f"✅ Transactions: {count} records generated")
    return transactions


# ─────────────────────────────────────────────────
# AUTOMATION 3: ACCOUNT ONBOARDING DATA
# ─────────────────────────────────────────────────

def generate_customers(count=50, inject_failures=False):
    """
    Generate mock customer onboarding records.
    inject_failures=True simulates broken pipeline data.
    """
    conn = get_connection()
    cursor = conn.cursor()

    account_types = ['savings', 'current', 'credit']
    onboarding_statuses = ['initiated', 'documents_pending', 'under_review', 'approved', 'rejected']
    nationalities = ['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'IN', 'SG']
    currencies = ['USD', 'EUR', 'GBP']

    customers = []
    accounts = []

    for i in range(1, count + 1):
        account_type = random.choice(account_types)
        customer = {
            "customer_id":          i,
            "full_name":            fake.name(),
            "email":                fake.unique.email(),
            "phone":                fake.phone_number()[:15],
            "date_of_birth":        fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%Y-%m-%d"),
            "address":              fake.address().replace('\n', ', ')[:200],
            "nationality":          random.choice(nationalities),
            "kyc_verified":         random.choice([0, 1]),
            "account_type":         account_type,
            "onboarding_status":    random.choice(onboarding_statuses),
            "created_at":           random_date(30)
        }

        account = {
            "account_id":       random_account_id(),
            "customer_id":      i,
            "account_type":     account_type,
            "balance":          round(random.uniform(0, 50000), 2),
            "currency":         random.choice(currencies),
            "status":           "active" if customer["onboarding_status"] == "approved" else "inactive",
            "created_at":       customer["created_at"],
            "last_updated":     random_date(7)
        }

        # Inject failures
        if inject_failures:
            failure_type = random.choice([
                "invalid_email",
                "missing_kyc",
                "duplicate_customer",
                "none", "none"
            ])

            if failure_type == "invalid_email" and random.random() < 0.2:
                customer["email"] = "not-an-email"
            elif failure_type == "missing_kyc":
                customer["kyc_verified"] = None

        customers.append(customer)
        accounts.append(account)

    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM bank_accounts")

    for customer in customers:
        try:
            cursor.execute("""
                INSERT INTO customers VALUES (
                    :customer_id, :full_name, :email, :phone,
                    :date_of_birth, :address, :nationality, :kyc_verified,
                    :account_type, :onboarding_status, :created_at
                )
            """, customer)
        except Exception:
            pass

    for account in accounts:
        try:
            cursor.execute("""
                INSERT INTO bank_accounts VALUES (
                    :account_id, :customer_id, :account_type, :balance,
                    :currency, :status, :created_at, :last_updated
                )
            """, account)
        except Exception:
            pass

    conn.commit()
    conn.close()
    print(f"✅ Customers: {count} records generated")
    return customers


# ─────────────────────────────────────────────────
# SEED ALL DATA
# ─────────────────────────────────────────────────

def seed_all(inject_failures=False):
    """Seed all 3 automations with mock data."""
    mode = "💥 CHAOS MODE" if inject_failures else "✅ NORMAL MODE"
    print(f"\n🌱 Seeding ShadowGate database — {mode}\n")

    generate_loan_applications(count=100, inject_failures=inject_failures)
    generate_transactions(count=200, inject_failures=inject_failures)
    generate_customers(count=50, inject_failures=inject_failures)

    print(f"\n✅ All data seeded successfully in {mode}\n")


if __name__ == "__main__":
    import sys
    chaos = "--chaos" in sys.argv
    seed_all(inject_failures=chaos)
