"""
ShadowGate - Agent 7: Coverage Intelligence
Analyses automation logic to find untested paths
and generates missing test scenarios automatically.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from ai_client import ask_ai
from database import get_connection


class CoverageIntelligenceAgent:
    """
    Analyses what's been tested vs what exists in the automation.
    Finds gaps and generates missing scenarios.
    """

    def __init__(self):
        self.name = "CoverageIntelligence"

    def analyse(self, automation_name, requirements, existing_scenarios):
        """
        Analyse coverage gaps and suggest missing scenarios.
        Returns coverage report.
        """
        print(f"\n🔭 Coverage Intelligence Agent - {automation_name.upper()}")
        print(f"🔍 Analysing test coverage gaps...\n")

        existing = existing_scenarios.get("scenarios", [])
        existing_types = {s.get("type") for s in existing}
        existing_names = [s.get("name", "") for s in existing]

        # Find coverage gaps using AI
        gaps = self._find_gaps(automation_name, requirements, existing_names)

        # Calculate coverage metrics
        coverage_metrics = self._calculate_coverage(existing)

        # Generate missing scenarios
        missing_scenarios = self._generate_missing(automation_name, requirements, gaps)

        report = {
            "automation": automation_name,
            "analysed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "existing_scenarios": len(existing),
            "coverage_metrics": coverage_metrics,
            "gaps_found": gaps,
            "missing_scenarios": missing_scenarios,
            "coverage_score": coverage_metrics.get("overall_score", 0)
        }

        self._print_report(report)
        self._log_to_audit(automation_name, report)

        return report

    def _find_gaps(self, automation_name, requirements, existing_names):
        """Use AI to find untested paths."""
        try:
            system_prompt = """You are a QA coverage expert.
Identify gaps in test coverage based on requirements and existing tests.
Respond ONLY with valid JSON, no markdown."""

            user_prompt = f"""Automation: {automation_name}
Requirements: {requirements[:500]}
Existing test names: {existing_names}

Find 3 untested scenarios not covered by existing tests.
Respond with ONLY this JSON:
{{
    "gaps": [
        {{
            "area": "area not tested",
            "description": "what is missing",
            "risk": "high/medium/low"
        }}
    ]
}}"""

            response = ask_ai(system_prompt, user_prompt)
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean.strip()).get("gaps", [])

        except Exception:
            return [
                {"area": "Concurrent processing", "description": "Multiple records processed simultaneously", "risk": "medium"},
                {"area": "Boundary values", "description": "Exact threshold values not tested", "risk": "high"},
                {"area": "Recovery scenarios", "description": "System recovery after partial failure", "risk": "medium"}
            ]

    def _generate_missing(self, automation_name, requirements, gaps):
        """Generate test scenarios for identified gaps."""
        missing = []
        for gap in gaps[:3]:
            missing.append({
                "name": f"Gap: {gap.get('area', 'Unknown')}",
                "type": "edge_case",
                "description": gap.get("description", ""),
                "risk": gap.get("risk", "medium"),
                "status": "needs_implementation"
            })
        return missing

    def _calculate_coverage(self, scenarios):
        """Calculate coverage metrics from existing scenarios."""
        total = len(scenarios)
        happy = len([s for s in scenarios if s.get("type") == "happy_path"])
        edge = len([s for s in scenarios if s.get("type") == "edge_case"])
        failure = len([s for s in scenarios if s.get("type") == "failure"])

        # Coverage score based on scenario distribution
        ideal_happy = 3
        ideal_edge = 4
        ideal_failure = 3

        happy_score = min(happy / ideal_happy, 1) * 33
        edge_score = min(edge / ideal_edge, 1) * 34
        failure_score = min(failure / ideal_failure, 1) * 33
        overall = round(happy_score + edge_score + failure_score, 1)

        return {
            "total_scenarios": total,
            "happy_path": happy,
            "edge_cases": edge,
            "failure_scenarios": failure,
            "overall_score": overall
        }

    def _print_report(self, report):
        """Print coverage report."""
        metrics = report["coverage_metrics"]
        score = report["coverage_score"]
        icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"

        print(f"   {icon} Coverage Score: {score}/100")
        print(f"   📊 Existing Scenarios: {report['existing_scenarios']}")
        print(f"      ✅ Happy Path:  {metrics.get('happy_path', 0)}")
        print(f"      ⚠️  Edge Cases:  {metrics.get('edge_cases', 0)}")
        print(f"      💥 Failures:    {metrics.get('failure_scenarios', 0)}")

        if report["gaps_found"]:
            print(f"\n   🔍 Coverage Gaps ({len(report['gaps_found'])}):")
            for gap in report["gaps_found"]:
                risk_icon = "🔴" if gap.get("risk") == "high" else "🟡" if gap.get("risk") == "medium" else "🟢"
                print(f"      {risk_icon} [{gap.get('risk', 'medium').upper()}] {gap.get('area', '')}")
                print(f"         {gap.get('description', '')}")

        if report["missing_scenarios"]:
            print(f"\n   📝 Generated Missing Scenarios:")
            for s in report["missing_scenarios"]:
                print(f"      • {s['name']}")

    def _log_to_audit(self, automation_name, report):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log
                (timestamp, agent_name, automation_name, action, output_summary, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.name,
                automation_name,
                "analyse_coverage",
                f"Coverage score: {report['coverage_score']}/100. Gaps found: {len(report['gaps_found'])}",
                "success"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    print("Coverage Intelligence Agent - run via orchestrator.py")
