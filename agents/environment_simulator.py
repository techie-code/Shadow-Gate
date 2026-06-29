"""
ShadowGate - Agent 1: Environment Simulator
Reads plain English automation requirements and generates test scenarios.
Caches scenarios to avoid hitting API rate limits.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from ai_client import ask_ai
from database import get_connection


class EnvironmentSimulatorAgent:

    def __init__(self):
        self.name = "EnvironmentSimulator"

    def generate_test_scenarios(self, automation_name, requirements_text):
        """
        Generates test scenarios from plain English requirements.
        Uses cached scenarios if they already exist to save API tokens.
        """

        # Check cache first
        scenario_file = f"tests/generated/{automation_name}_scenarios.json"
        if os.path.exists(scenario_file):
            print(f"\n🏗️  Environment Simulator Agent")
            print(f"📂 Loading existing scenarios for: {automation_name}")
            with open(scenario_file) as f:
                scenarios = json.load(f)
            print(f"✅ Loaded {len(scenarios.get('scenarios', []))} scenarios from cache")
            self._print_summary(scenarios)
            return scenarios

        # Generate new scenarios via AI
        print(f"\n🏗️  Environment Simulator Agent")
        print(f"📖 Reading requirements for: {automation_name}")
        print(f"🤖 Asking Groq (Llama 3.3) to generate test scenarios...\n")

        system_prompt = """You are an expert QA engineer specializing in enterprise automation testing.
Your job is to read automation requirements and generate comprehensive test scenarios.
You must respond ONLY with valid JSON - no markdown, no backticks, no explanation.
"""

        user_prompt = f"""Read these automation requirements and generate test scenarios:

AUTOMATION NAME: {automation_name}

REQUIREMENTS:
{requirements_text}

Generate exactly 10 test scenarios covering:
- 3 happy path scenarios (everything works correctly)
- 4 edge case scenarios (boundary conditions, unusual but valid inputs)
- 3 failure scenarios (invalid data, missing fields, wrong types)

Respond with ONLY this JSON structure, no other text:
{{
    "automation": "{automation_name}",
    "generated_at": "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    "total_scenarios": 10,
    "scenarios": [
        {{
            "id": 1,
            "name": "scenario name",
            "type": "happy_path",
            "description": "what this tests",
            "input": "what data goes in",
            "expected_output": "what should happen",
            "priority": "high"
        }}
    ]
}}
"""

        try:
            response = ask_ai(system_prompt, user_prompt, temperature=0.3)

            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()

            scenarios = json.loads(clean)
            self._save_scenarios(automation_name, scenarios)
            self._log_to_audit(automation_name, len(scenarios.get("scenarios", [])))

            print(f"✅ Generated {len(scenarios.get('scenarios', []))} test scenarios")
            self._print_summary(scenarios)
            return scenarios

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            print(f"❌ Environment Simulator failed: {e}")
            return None

    def _save_scenarios(self, automation_name, scenarios):
        os.makedirs("tests/generated", exist_ok=True)
        filename = f"tests/generated/{automation_name}_scenarios.json"
        with open(filename, "w") as f:
            json.dump(scenarios, f, indent=2)
        print(f"💾 Scenarios saved to {filename}")

    def _log_to_audit(self, automation_name, scenario_count):
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
                "generate_test_scenarios",
                f"Generated {scenario_count} test scenarios from plain English requirements",
                "success"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _print_summary(self, scenarios):
        scenario_list = scenarios.get("scenarios", [])
        happy = [s for s in scenario_list if s.get("type") == "happy_path"]
        edge = [s for s in scenario_list if s.get("type") == "edge_case"]
        failure = [s for s in scenario_list if s.get("type") == "failure"]

        print(f"\n📋 Scenario Summary:")
        print(f"   ✅ Happy Path:  {len(happy)}")
        print(f"   ⚠️  Edge Cases:  {len(edge)}")
        print(f"   💥 Failures:    {len(failure)}")
        print()

        print("📝 Generated Scenarios:")
        for s in scenario_list:
            icon = "✅" if s.get("type") == "happy_path" else "⚠️" if s.get("type") == "edge_case" else "💥"
            print(f"   {icon} [{s.get('priority', 'medium').upper()}] {s.get('name', '')}")


if __name__ == "__main__":
    from mock_automations.loan_processing.automation import REQUIREMENTS
    agent = EnvironmentSimulatorAgent()
    scenarios = agent.generate_test_scenarios("loan_processing", REQUIREMENTS)
    if scenarios:
        print(f"\n🎉 Environment Simulator Agent working perfectly!")
    else:
        print(f"\n❌ Something went wrong - check your GROQ_API_KEY in .env")
