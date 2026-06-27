"""
ShadowGate - Main Entry Point
AI-powered hospital automation testing platform.

Tests ARIA, SAFE, GUARDIAN and CARA automations.
Discovers unknown risks nobody thought to test.

We test what you know. We discover what you don't.
"""

import sys
import os
from datetime import datetime
from database import get_connection
conn = get_connection()
conn.execute("DELETE FROM test_results")
conn.commit()

def main():
    print(f"\n{'='*55}")
    print(f" SHADOWGATE")
    print(f" AI-Powered Hospital Automation Testing Platform")
    print(f" We test what you know. We discover what you don't.")
    print(f"{'='*55}")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}\n")

    # Create database tables
    from database import create_all_tables
    create_all_tables()

    # Run full pipeline
    from langchain.orchestrator import run_all_automations
    run_all_automations()


if __name__ == "__main__":
    main()
