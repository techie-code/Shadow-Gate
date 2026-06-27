"""
ShadowGate - Hospital Database
SQLite database for hospital patient management system.
Stores patients, scenarios, safety validations, assignments and discharge records.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("SHADOWGATE_DB_PATH", "shadowgate.db")


def get_connection():
    """Get database connection with WAL mode to prevent locking."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def create_all_tables():
    """Create all hospital database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # PATIENTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id          TEXT PRIMARY KEY,
            name                TEXT NOT NULL,
            age                 INTEGER,
            gender              TEXT,
            symptoms            TEXT,
            symptom_duration    TEXT,
            pain_scale          INTEGER,
            medical_history     TEXT,
            current_medications TEXT,
            allergies           TEXT,
            weight_kg           REAL,
            lives_alone         INTEGER DEFAULT 0,
            emergency_contacts  TEXT,
            insurance_status    TEXT DEFAULT 'active',
            admitted_at         TEXT NOT NULL
        )
    """)

    # VITAL SIGNS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vital_signs (
            vital_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id          TEXT NOT NULL,
            heart_rate          INTEGER,
            blood_pressure      TEXT,
            temperature_f       REAL,
            oxygen_saturation   INTEGER,
            recorded_at         TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        )
    """)

    # ARIA - PATIENT SCENARIOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_scenarios (
            scenario_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id          TEXT NOT NULL,
            priority            TEXT NOT NULL,
            best_case           TEXT,
            moderate_case       TEXT,
            worst_case          TEXT,
            unknown_risks       TEXT,
            requires_approval   INTEGER DEFAULT 0,
            head_approved       INTEGER DEFAULT 0,
            approved_by         TEXT,
            approved_at         TEXT,
            generated_at        TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        )
    """)

    # SAFE - SAFETY VALIDATIONS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS safety_validations (
            validation_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id          TEXT NOT NULL,
            scenario_type       TEXT NOT NULL,
            status              TEXT NOT NULL,
            issues              TEXT,
            warnings            TEXT,
            validated_at        TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        )
    """)

    # GUARDIAN - DOCTOR ASSIGNMENTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctor_assignments (
            assignment_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id          TEXT NOT NULL,
            doctor_id           TEXT NOT NULL,
            doctor_name         TEXT NOT NULL,
            specialty           TEXT,
            priority            TEXT,
            estimated_wait      INTEGER,
            assigned_at         TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        )
    """)

    # GUARDIAN - CONDUCT ALERTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conduct_alerts (
            alert_id            TEXT PRIMARY KEY,
            doctor_id           TEXT NOT NULL,
            patient_id          TEXT NOT NULL,
            action              TEXT NOT NULL,
            severity            TEXT NOT NULL,
            description         TEXT,
            recommended_action  TEXT,
            head_notified       INTEGER DEFAULT 1,
            resolved            INTEGER DEFAULT 0,
            created_at          TEXT NOT NULL
        )
    """)

    # CARA - RECOVERY TRACKING
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recovery_records (
            record_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id          TEXT NOT NULL,
            discharge_status    TEXT NOT NULL,
            criteria_met        INTEGER,
            criteria_total      INTEGER,
            blockers            TEXT,
            warnings            TEXT,
            follow_up_date      TEXT,
            follow_up_type      TEXT,
            patient_message     TEXT,
            assessed_at         TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        )
    """)

    # SHADOWGATE - AUDIT LOG
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp           TEXT NOT NULL,
            agent_name          TEXT NOT NULL,
            automation_name     TEXT NOT NULL,
            action              TEXT NOT NULL,
            patient_id          TEXT,
            input_summary       TEXT,
            output_summary      TEXT,
            decision            TEXT,
            severity            TEXT,
            duration_ms         INTEGER,
            status              TEXT NOT NULL
        )
    """)

    # SHADOWGATE - TEST RESULTS
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

    # SHADOWGATE - SIMULATION RUNS
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
    print("All hospital database tables created successfully")


if __name__ == "__main__":
    create_all_tables()
