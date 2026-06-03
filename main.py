"""
ShadowGate - Main Entry Point
"Test everything. Touch nothing. Ship with confidence."

Usage:
    python main.py                    # Run all automations normally
    python main.py --chaos            # Run with chaos injection
    python main.py --setup            # Setup database only
    python main.py --automation loan  # Run specific automation
"""

import sys
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()


def print_banner():
    console.print(Panel.fit(
        "[bold cyan]ShadowGate[/bold cyan]\n"
        "[dim]Test everything. Touch nothing. Ship with confidence.[/dim]\n"
        "[dim]UiPath AgentHack 2026 — Track 3: UiPath Test Cloud[/dim]",
        border_style="cyan"
    ))


def setup_database():
    """Initialize the database."""
    from database import create_all_tables
    console.print("\n[cyan]Setting up database...[/cyan]")
    create_all_tables()


def seed_data(chaos=False):
    """Seed mock data."""
    from data_generator import seed_all
    seed_all(inject_failures=chaos)


def run_automations(automation_filter=None, chaos=False):
    """Run mock automations."""
    results = {}

    automations = {
        "loan": ("mock_automations.loan_processing.automation", "LoanProcessingAutomation"),
        "fraud": ("mock_automations.fraud_detection.automation", "FraudDetectionAutomation"),
        "onboarding": ("mock_automations.account_onboarding.automation", "AccountOnboardingAutomation"),
    }

    for key, (module_path, class_name) in automations.items():
        if automation_filter and key != automation_filter:
            continue

        try:
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            automation = cls()
            result = automation.process()
            results[key] = result
        except Exception as e:
            console.print(f"[red]Error running {key}: {e}[/red]")
            results[key] = {"error": str(e)}

    return results


def print_results_table(results):
    """Print a summary table of automation results."""
    table = Table(title="ShadowGate — Automation Results", border_style="cyan")
    table.add_column("Automation", style="cyan")
    table.add_column("Processed", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Status", justify="center")

    for name, result in results.items():
        if "error" in result:
            table.add_row(name, "—", "—", "—", "[red]FAILED[/red]")
        else:
            success_rate = result.get("success_rate", 0)
            errors = len(result.get("errors", []))
            status = "[green]✅ OK[/green]" if errors == 0 else "[yellow]⚠️ WARNINGS[/yellow]"
            table.add_row(
                name.replace("_", " ").title(),
                str(result.get("processed", 0)),
                f"{success_rate}%",
                str(errors),
                status
            )

    console.print(table)


def main():
    print_banner()

    args = sys.argv[1:]
    chaos = "--chaos" in args
    setup_only = "--setup" in args
    automation_filter = None

    if "--automation" in args:
        idx = args.index("--automation")
        if idx + 1 < len(args):
            automation_filter = args[idx + 1]

    if chaos:
        console.print("\n[bold red]💥 CHAOS MODE ENABLED — Injecting failures into pipeline[/bold red]\n")

    # Step 1: Setup
    setup_database()

    if setup_only:
        console.print("[green]✅ Database setup complete.[/green]")
        return

    # Step 2: Seed data
    seed_data(chaos=chaos)

    # Step 3: Run automations
    console.print("\n[cyan]Running automations...[/cyan]")
    results = run_automations(automation_filter=automation_filter, chaos=chaos)

    # Step 4: Print results
    print_results_table(results)

    console.print(f"\n[dim]Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
    console.print("[bold cyan]ShadowGate ready. Week 2: Building agents next.[/bold cyan]\n")


if __name__ == "__main__":
    main()
