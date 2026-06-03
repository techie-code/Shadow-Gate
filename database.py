"""
ShadowGate - Database Setup
Creates SQLite database and all tables for the 3 mock automations.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("SHADOWGATE_DB_PATH", "shadowgate.db")


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_all_tables():
    """Create all tables for all 3 automations."""
    conn = get_connection()
    cursor = conn.cursor()

    # ─────────────────────────────────────────
    # AUTOMATION 1: LOAN PROCESSING
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_applications (
            application_id      INTEGER PRIMARY KEY,
            customer_id         INTEGER NOT NULL,
            full_name           TEXT NOT NULL,
            email               TEXT NOT NULL,
            loan_amount         REAL NOT NULL CHECK(loan_amount > 0),
            loan_type           TEXT NOT NULL CHECK(loan_type IN ('personal', 'home', 'auto', 'business')),
            annual_income       REAL NOT NULL CHECK(annual_income > 0),
            credit_score        INTEGER NOT NULL CHECK(credit_score BETWEEN 300 AND 850),
            employment_status   TEXT NOT NULL CHECK(employment_status IN ('employed', 'self_employed', 'unemployed')),
            application_date    TEXT NOT NULL,
            status              TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected', 'under_review')),
            processed_by        TEXT DEFAULT 'automation'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_decisions (
            decision_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id      INTEGER NOT NULL,
            decision            TEXT NOT NULL CHECK(decision IN ('approved', 'rejected', 'escalated')),
            reason              TEXT,
            decided_at          TEXT NOT NULL,
            decided_by          TEXT NOT NULL,
            FOREIGN KEY (application_id) REFERENCES loan_applications(application_id)
        )
    """)

    # ─────────────────────────────────────────
    # AUTOMATION 2: FRAUD DETECTION
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id      INTEGER PRIMARY KEY,
            customer_id         INTEGER NOT NULL,
            account_id          TEXT NOT NULL,
            amount              REAL NOT NULL CHECK(amount > 0),
            transaction_type    TEXT NOT NULL CHECK(transaction_type IN ('debit', 'credit', 'transfer')),
            merchant            TEXT,
            location            TEXT,
            transaction_date    TEXT NOT NULL,
            status              TEXT NOT NULL CHECK(status IN ('pending', 'completed', 'flagged', 'blocked')),
            is_fraudulent       INTEGER DEFAULT 0 CHECK(is_fraudulent IN (0, 1))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fraud_alerts (
            alert_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id      INTEGER NOT NULL,
            alert_type          TEXT NOT NULL,
            severity            TEXT NOT NULL CHECK(severity IN ('low', 'medium', 'high', 'critical')),
            description         TEXT,
            created_at          TEXT NOT NULL,
            resolved            INTEGER DEFAULT 0,
            FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
        )
    """)

    # ─────────────────────────────────────────
    # AUTOMATION 3: ACCOUNT ONBOARDING
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id         INTEGER PRIMARY KEY,
            full_name           TEXT NOT NULL,
            email               TEXT NOT NULL UNIQUE,
            phone               TEXT NOT NULL,
            date_of_birth       TEXT NOT NULL,
            address             TEXT NOT NULL,
            nationality         TEXT NOT NULL,
            kyc_verified        INTEGER NOT NULL DEFAULT 0 CHECK(kyc_verified IN (0, 1)),
            account_type        TEXT NOT NULL CHECK(account_type IN ('savings', 'current', 'credit')),
            onboarding_status   TEXT NOT NULL CHECK(onboarding_status IN ('initiated', 'documents_pending', 'under_review', 'approved', 'rejected')),
            created_at          TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_accounts (
            account_id          TEXT PRIMARY KEY,
            customer_id         INTEGER NOT NULL,
            account_type        TEXT NOT NULL CHECK(account_type IN ('savings', 'current', 'credit')),
            balance             REAL NOT NULL DEFAULT 0.0 CHECK(balance >= 0),
            currency            TEXT NOT NULL CHECK(currency IN ('USD', 'EUR', 'GBP')),
            status              TEXT NOT NULL CHECK(status IN ('active', 'inactive', 'suspended', 'closed')),
            created_at          TEXT NOT NULL,
            last_updated        TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    # ─────────────────────────────────────────
    # SHADOWGATE SYSTEM TABLES
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp           TEXT NOT NULL,
            agent_name          TEXT NOT NULL,
            automation_name     TEXT NOT NULL,
            action              TEXT NOT NULL,
            input_summary       TEXT,
            output_summary      TEXT,
            decision            TEXT,
            severity            TEXT,
            duration_ms         INTEGER,
            status              TEXT NOT NULL CHECK(status IN ('success', 'failure', 'warning'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            result_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            automation_name     TEXT NOT NULL,
            test_name           TEXT NOT NULL,
            test_type           TEXT NOT NULL,
            status              TEXT NOT NULL CHECK(status IN ('passed', 'failed', 'skipped')),
            confidence_score    REAL,
            failure_reason      TEXT,
            fix_recommendation  TEXT,
            executed_at         TEXT NOT NULL,
            duration_ms         INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            run_id              INTEGER PRIMARY KEY AUTOINCREMENT,
            automation_name     TEXT NOT NULL,
            scenarios_total     INTEGER NOT NULL,
            scenarios_passed    INTEGER NOT NULL,
            scenarios_failed    INTEGER NOT NULL,
            confidence_score    REAL NOT NULL,
            deployment_ready    INTEGER NOT NULL CHECK(deployment_ready IN (0, 1)),
            run_at              TEXT NOT NULL,
            duration_seconds    REAL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ All database tables created successfully")


if __name__ == "__main__":
    create_all_tables()
