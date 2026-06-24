"""
ShadowGate - Database Setup
Creates SQLite database and all tables for the 3 mock automations.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("SHADOWGATE_DB_PATH", "shadowgate.db")


def get_connection():
    """Get a database connection with timeout to prevent locking."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Prevents database locked errors
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def create_all_tables():
    """Create all tables for all 3 automations."""
    conn = get_connection()
    cursor = conn.cursor()

    # AUTOMATION 1: LOAN PROCESSING
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_applications (
            application_id      INTEGER PRIMARY KEY,
            customer_id         INTEGER,
            full_name           TEXT,
            email               TEXT,
            loan_amount         REAL,
            loan_type           TEXT,
            annual_income       REAL,
            credit_score        INTEGER,
            employment_status   TEXT,
            application_date    TEXT,
            status              TEXT,
            processed_by        TEXT DEFAULT 'automation'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_decisions (
            decision_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id      INTEGER NOT NULL,
            decision            TEXT NOT NULL,
            reason              TEXT,
            decided_at          TEXT NOT NULL,
            decided_by          TEXT NOT NULL,
            FOREIGN KEY (application_id) REFERENCES loan_applications(application_id)
        )
    """)

    # AUTOMATION 2: FRAUD DETECTION
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id      INTEGER PRIMARY KEY,
            customer_id         INTEGER,
            account_id          TEXT,
            amount              REAL,
            transaction_type    TEXT,
            merchant            TEXT,
            location            TEXT,
            transaction_date    TEXT,
            status              TEXT,
            is_fraudulent       INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fraud_alerts (
            alert_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id      INTEGER NOT NULL,
            alert_type          TEXT NOT NULL,
            severity            TEXT NOT NULL,
            description         TEXT,
            created_at          TEXT NOT NULL,
            resolved            INTEGER DEFAULT 0,
            FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
        )
    """)

    # AUTOMATION 3: ACCOUNT ONBOARDING
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id         INTEGER PRIMARY KEY,
            full_name           TEXT,
            email               TEXT,
            phone               TEXT,
            date_of_birth       TEXT,
            address             TEXT,
            nationality         TEXT,
            kyc_verified        INTEGER DEFAULT 0,
            account_type        TEXT,
            onboarding_status   TEXT,
            created_at          TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_accounts (
            account_id          TEXT PRIMARY KEY,
            customer_id         INTEGER NOT NULL,
            account_type        TEXT NOT NULL,
            balance             REAL NOT NULL DEFAULT 0.0,
            currency            TEXT NOT NULL,
            status              TEXT NOT NULL,
            created_at          TEXT NOT NULL,
            last_updated        TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    # SHADOWGATE SYSTEM TABLES
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
            status              TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            result_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            automation_name     TEXT NOT NULL,
            test_name           TEXT NOT NULL,
            test_type           TEXT NOT NULL,
            status              TEXT NOT NULL,
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
            deployment_ready    INTEGER NOT NULL,
            run_at              TEXT NOT NULL,
            duration_seconds    REAL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ All database tables created successfully")


if __name__ == "__main__":
    create_all_tables()
