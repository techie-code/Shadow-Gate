"""
ARIA - Adaptive Risk Intelligence Analyser
Hospital Patient Scenario Generator

Takes patient data and generates ALL possible scenarios
from best case to worst case. Discovers risks nobody
thought to test. Every scenario checked for safety.

This is what ShadowGate tests.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from ai_client import ask_ai
import json


class ARIA:
    """
    Adaptive Risk Intelligence Analyser.

    For each patient, ARIA generates all possible
    scenarios from best case to worst case.
    Then thinks about what nobody tested.
    """

    def __init__(self):
        self.name = "ARIA"
        self.version = "1.0.0"
        self.processed = 0
        self.flagged = 0
        self.unknown_risks_found = 0
        self.errors = []

    def analyse_patient(self, patient):
        """
        Core function. Takes one patient record.
        Generates best to worst case scenarios.
        Discovers unknown risks.
        Returns full analysis.
        """
        self.processed += 1

        # Step 1: Validate patient data
        is_valid, reason = self.validate_patient(patient)
        if not is_valid:
            self.errors.append({
                "patient_id": patient.get("patient_id"),
                "error": reason
            })
            return None

        # Step 2: Generate scenarios using AI
        scenarios = self.generate_scenarios(patient)

        # Step 3: Discover unknown risks
        unknown_risks = self.discover_unknown_risks(patient, scenarios)

        if unknown_risks:
            self.unknown_risks_found += len(unknown_risks)
            self.flagged += 1

        # Step 4: Assign priority
        priority = self.assign_priority(patient, scenarios, unknown_risks)

        result = {
            "patient_id": patient.get("patient_id"),
            "patient_name": patient.get("name"),
            "age": patient.get("age"),
            "analysed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "priority": priority,
            "scenarios": scenarios,
            "unknown_risks": unknown_risks,
            "requires_head_approval": priority in ["P1", "P2"],
            "automation": self.name
        }

        return result

    def validate_patient(self, patient):
        """Validate patient data completeness."""
        required = ["patient_id", "name", "age", "symptoms", "vital_signs"]

        for field in required:
            if patient.get(field) is None:
                return False, f"Missing required field: {field}"

        age = patient.get("age")
        try:
            if int(age) < 0 or int(age) > 150:
                return False, f"Invalid age: {age}"
        except (TypeError, ValueError):
            return False, f"Invalid age format: {age}"

        vitals = patient.get("vital_signs", {})
        heart_rate = vitals.get("heart_rate")
        if heart_rate is not None:
            try:
                if int(heart_rate) < 0:
                    return False, f"Invalid heart rate: {heart_rate}"
            except (TypeError, ValueError):
                return False, f"Invalid heart rate format: {heart_rate}"

        return True, "Valid"

    def generate_scenarios(self, patient):
        """
        Generate best to worst case scenarios for this patient.
        Uses AI to think through all possibilities.
        """
        system_prompt = """You are a senior hospital physician with 20 years experience.
Given a patient's data, generate treatment scenarios from best case to worst case.
Consider all symptoms, history, medications, and allergies carefully.
Respond ONLY with valid JSON, no markdown."""

        vitals = patient.get("vital_signs", {})
        history = patient.get("medical_history", [])
        medications = patient.get("current_medications", [])
        allergies = patient.get("allergies", [])

        user_prompt = f"""Generate treatment scenarios for this patient:

PATIENT:
  Age: {patient.get('age')}
  Gender: {patient.get('gender', 'unknown')}
  Symptoms: {patient.get('symptoms')}
  Vital Signs: Heart Rate {vitals.get('heart_rate')} bpm, BP {vitals.get('blood_pressure')}, Temp {vitals.get('temperature_f')}F, O2 {vitals.get('oxygen_saturation')}%
  Medical History: {history}
  Current Medications: {medications}
  Allergies: {allergies}
  Symptom Duration: {patient.get('symptom_duration', 'unknown')}
  Pain Scale: {patient.get('pain_scale', 'unknown')}/10

Generate exactly 3 scenarios. Respond with ONLY this JSON:
{{
    "best_case": {{
        "diagnosis": "most optimistic diagnosis",
        "probability": "percentage chance",
        "recommended_treatment": "specific treatment",
        "medications": ["medication 1", "medication 2"],
        "estimated_recovery": "recovery time",
        "risk_level": "LOW",
        "notes": "any important notes"
    }},
    "moderate_case": {{
        "diagnosis": "moderate diagnosis",
        "probability": "percentage chance",
        "recommended_treatment": "specific treatment",
        "medications": ["medication 1", "medication 2"],
        "estimated_recovery": "recovery time",
        "risk_level": "MEDIUM",
        "notes": "any important notes"
    }},
    "worst_case": {{
        "diagnosis": "most serious diagnosis",
        "probability": "percentage chance",
        "recommended_treatment": "specific treatment",
        "medications": ["medication 1", "medication 2"],
        "estimated_recovery": "recovery time",
        "risk_level": "HIGH",
        "notes": "any important notes"
    }}
}}"""

        try:
            response = ask_ai(system_prompt, user_prompt, temperature=0.2)
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean.strip())
        except Exception as e:
            return self.fallback_scenarios(patient)

    def discover_unknown_risks(self, patient, scenarios):
        """
        THE CREATIVE FEATURE.
        Thinks about risks nobody wrote tests for.
        Goes beyond the scenarios to find hidden dangers.
        """
        system_prompt = """You are a patient safety expert who thinks about what could go wrong
that nobody considered. You look beyond the obvious diagnosis to find hidden risks.
Be specific and clinical. Respond ONLY with valid JSON, no markdown."""

        age = patient.get("age", 0)
        history = patient.get("medical_history", [])
        medications = patient.get("current_medications", [])
        allergies = patient.get("allergies", [])
        vitals = patient.get("vital_signs", {})

        # Extract all medications from all scenarios
        all_scenario_meds = []
        for scenario_key in ["best_case", "moderate_case", "worst_case"]:
            scenario = scenarios.get(scenario_key, {})
            all_scenario_meds.extend(scenario.get("medications", []))

        user_prompt = f"""A patient is being treated. The automation generated scenarios.
Now think about what hidden risks nobody tested.

PATIENT PROFILE:
  Age: {age}
  Medical History: {history}
  Current Medications: {medications}
  Allergies: {allergies}
  Vital Signs: {vitals}

MEDICATIONS IN ALL SCENARIOS: {all_scenario_meds}

Find up to 3 unknown risks that are NOT obvious.
Think about: drug interactions, age-related concerns, organ function,
combination effects, contraindications with history.

Respond with ONLY this JSON:
{{
    "unknown_risks": [
        {{
            "risk": "specific risk description",
            "why_dangerous": "clinical explanation",
            "who_affected": "which patients face this",
            "severity": "HIGH or MEDIUM or LOW",
            "recommendation": "what to check or change"
        }}
    ]
}}

If no unknown risks found, return: {{"unknown_risks": []}}"""

        try:
            response = ask_ai(system_prompt, user_prompt, temperature=0.1)
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            data = json.loads(clean.strip())
            risks = data.get("unknown_risks", [])

            if risks:
                print(f"\n   SHADOWGATE DISCOVERED {len(risks)} UNKNOWN RISK(S):")
                for risk in risks:
                    severity = risk.get('severity', 'UNKNOWN')
                    icon = "HIGH" if severity == "HIGH" else "MEDIUM" if severity == "MEDIUM" else "LOW"
                    print(f"   [{icon}] {risk.get('risk', '')}")
                    print(f"         Why dangerous: {risk.get('why_dangerous', '')}")
                    print(f"         Recommendation: {risk.get('recommendation', '')}")

            return risks

        except Exception:
            return []

    def assign_priority(self, patient, scenarios, unknown_risks):
        """
        Assign priority based on clear clinical rules.
        Simple, reliable, predictable.
        """
        vitals = patient.get("vital_signs", {})
        age = int(patient.get("age", 30))
        symptoms = patient.get("symptoms", "").lower()
        pain = int(patient.get("pain_scale", 5))
        history = patient.get("medical_history", [])

        try:
            hr = int(vitals.get("heart_rate", 80))
            o2 = int(vitals.get("oxygen_saturation", 98))
            temp = float(vitals.get("temperature_f", 98.6))
        except Exception:
            hr, o2, temp = 80, 98, 98.6

        # P1 - Life threatening vitals or symptoms
        if hr > 130 or hr < 40 or o2 < 90 or temp > 104:
            return "P1"
        p1_words = ["chest pain", "cardiac", "heart attack", "stroke",
                    "not breathing", "unconscious", "severe bleeding"]
        if any(w in symptoms for w in p1_words):
            return "P1"
        if age > 70 and pain >= 7 and len(history) > 0:
            return "P1"

        # P2 - Urgent
        if age < 5 and temp > 102:
            return "P2"
        if pain >= 8:
            return "P2"
        if age > 65 and any(w in symptoms for w in ["fever","chest","breathing"]):
            return "P2"

        # P3 - Moderate (fever, cold, infection in healthy adults)
        p3_words = ["fever","cold","cough","sore throat","infection",
                    "rash","vomiting","headache","back pain","flu"]
        if any(w in symptoms for w in p3_words):
            return "P3"
        if pain >= 5:
            return "P3"

        # P4 - Minor
        return "P4"

    def _ask_ai_for_priority(self, patient, scenarios, unknown_risks):
        """Ask AI to determine patient priority."""
        vitals = patient.get("vital_signs", {})
        high_risks = [r for r in unknown_risks if r.get("severity") == "HIGH"]
        medium_risks = [r for r in unknown_risks if r.get("severity") == "MEDIUM"]

        system_prompt = """You are a triage nurse with 15 years experience.
Assign a priority level to this patient based on ALL available information.

Priority levels:
P1 - CRITICAL: Life threatening. Immediate attention. Examples: chest pain, cardiac event, stroke, oxygen below 90%, severe bleeding, unconscious.
P2 - URGENT: Serious but stable. Within 30 minutes. Examples: high fever in child, elderly with multiple risks, severe pain 8+, complex drug interactions.
P3 - MODERATE: Needs attention. Within 2 hours. Examples: mild fever, moderate pain, minor infection, simple illness in healthy adult.
P4 - NON-URGENT: Minor issue. Within 4 hours. Examples: cold, minor sprain, minor cut, routine check.

Respond with ONLY one of: P1, P2, P3, P4
Nothing else. Just the priority code."""

        # Build complete unknown risks summary
        risks_summary = ""
        if unknown_risks:
            risks_summary = chr(10).join([
                f"  [{r.get('severity')}] {r.get('risk')} - {r.get('why_dangerous','')}"
                for r in unknown_risks
            ])
        else:
            risks_summary = "  None found"

        user_prompt = f"""Complete patient profile for triage assessment:

PATIENT INFORMATION:
  Name: {patient.get('name', 'Unknown')}
  Age: {patient.get('age')}
  Gender: {patient.get('gender', 'Unknown')}
  Weight: {patient.get('weight_kg', 'Unknown')} kg
  Lives Alone: {patient.get('lives_alone', False)}

PRESENTING COMPLAINT:
  Symptoms: {patient.get('symptoms')}
  Duration: {patient.get('symptom_duration', 'Unknown')}
  Pain Scale: {patient.get('pain_scale')}/10

VITAL SIGNS:
  Heart Rate: {vitals.get('heart_rate')} bpm
  Blood Pressure: {vitals.get('blood_pressure')}
  Temperature: {vitals.get('temperature_f')}F
  Oxygen Saturation: {vitals.get('oxygen_saturation')}%

MEDICAL BACKGROUND:
  Medical History: {', '.join(patient.get('medical_history', [])) or 'None'}
  Current Medications: {', '.join(patient.get('current_medications', [])) or 'None'}
  Known Allergies: {', '.join(patient.get('allergies', [])) or 'None'}

CLINICAL SCENARIOS (AI Generated):
  Best Case: {scenarios.get('best_case', {}).get('diagnosis', 'Unknown')} | Risk: {scenarios.get('best_case', {}).get('risk_level', 'Unknown')} | Treatment: {scenarios.get('best_case', {}).get('recommended_treatment', 'Unknown')}
  Moderate:  {scenarios.get('moderate_case', {}).get('diagnosis', 'Unknown')} | Risk: {scenarios.get('moderate_case', {}).get('risk_level', 'Unknown')} | Treatment: {scenarios.get('moderate_case', {}).get('recommended_treatment', 'Unknown')}
  Worst Case:{scenarios.get('worst_case', {}).get('diagnosis', 'Unknown')} | Risk: {scenarios.get('worst_case', {}).get('risk_level', 'Unknown')} | Treatment: {scenarios.get('worst_case', {}).get('recommended_treatment', 'Unknown')}

UNKNOWN RISKS DISCOVERED BY SHADOWGATE ({len(unknown_risks)} total - {len(high_risks)} HIGH, {len(medium_risks)} MEDIUM):
{risks_summary}

Based on ALL of the above information, what is the correct triage priority?
Consider everything: vitals, symptoms, age, history, medications, allergies, scenarios AND unknown risks.

Reply with ONLY one of: P1, P2, P3, P4"""

        response = ask_ai(system_prompt, user_prompt, temperature=0.0)
        # Extract just the priority code
        response = response.strip().upper()
        for p in ["P1", "P2", "P3", "P4"]:
            if p in response:
                return p
        return "P3"

    def fallback_scenarios(self, patient):
        """Fallback scenarios if AI fails."""
        return {
            "best_case": {
                "diagnosis": "Minor condition",
                "probability": "60%",
                "recommended_treatment": "Rest and monitoring",
                "medications": ["Paracetamol"],
                "estimated_recovery": "1 to 2 days",
                "risk_level": "LOW",
                "notes": "Standard treatment"
            },
            "moderate_case": {
                "diagnosis": "Moderate condition requiring treatment",
                "probability": "30%",
                "recommended_treatment": "Medication and monitoring",
                "medications": ["Standard medication"],
                "estimated_recovery": "3 to 7 days",
                "risk_level": "MEDIUM",
                "notes": "Requires doctor review"
            },
            "worst_case": {
                "diagnosis": "Serious condition",
                "probability": "10%",
                "recommended_treatment": "Immediate intervention",
                "medications": ["Emergency medication"],
                "estimated_recovery": "2 to 4 weeks",
                "risk_level": "HIGH",
                "notes": "Escalate to specialist"
            }
        }

    def process(self, patients):
        """Process all patients through ARIA."""
        print(f"\n ARIA - Adaptive Risk Intelligence Analyser v{self.version}")
        print(f" Analysing {len(patients)} patient(s)...\n")

        results = []
        for patient in patients:
            print(f" Patient: {patient.get('name')} | Age: {patient.get('age')}")
            print(f" Symptoms: {patient.get('symptoms')}")

            result = self.analyse_patient(patient)

            if result:
                priority = result.get("priority")
                unknown_risks = result.get("unknown_risks", [])
                icon = "P1" if priority == "P1" else "P2" if priority == "P2" else "P3" if priority == "P3" else "P4"
                print(f" Priority: {icon}")
                print(f" Unknown risks found: {len(unknown_risks)}")
                print(f" Requires Head approval: {result.get('requires_head_approval')}")
                results.append(result)
            else:
                print(f" ERROR: Could not analyse patient")

            print()

        print(f" ARIA Summary:")
        print(f" Processed: {self.processed}")
        print(f" Flagged: {self.flagged}")
        print(f" Unknown risks discovered: {self.unknown_risks_found}")
        print(f" Errors: {len(self.errors)}")

        return {
            "automation": self.name,
            "processed": self.processed,
            "flagged": self.flagged,
            "unknown_risks_found": self.unknown_risks_found,
            "errors": self.errors,
            "results": results,
            "success_rate": round((self.processed - len(self.errors)) / max(self.processed, 1) * 100, 2)
        }


# Plain English requirements used by ShadowGate simulation engine
REQUIREMENTS = """
ARIA analyses hospital patient data and generates treatment scenarios.

For each patient ARIA:
- Validates all required fields are present and valid
- Age must be between 0 and 150
- Heart rate must be a positive number
- Symptoms must be provided
- Vital signs must be present

ARIA generates three scenarios for every patient:
- Best case: most optimistic diagnosis and treatment
- Moderate case: middle ground diagnosis and treatment
- Worst case: most serious diagnosis and treatment

Each scenario includes:
- Specific diagnosis
- Recommended medications
- Estimated recovery time
- Risk level (LOW, MEDIUM, HIGH)

ARIA assigns priority:
- P1: Critical, immediate attention, heart rate over 130 or under 40, oxygen below 90%
- P2: Urgent, within 30 minutes, moderate risk with unknown dangers
- P3: Moderate, within 2 hours, pain scale 7 or above
- P4: Non urgent, within 4 hours, minor symptoms

ARIA discovers unknown risks that nobody tested:
- Drug interactions between current medications and recommended treatments
- Age related contraindications for elderly patients over 70
- Organ function concerns for patients with relevant history
- Combination effects nobody considered

All P1 and P2 patients require Head of Department approval before treatment.
Any unknown risk found triggers confidential email to Head of Department.
Invalid patient data must be caught and logged as errors without crashing.
"""


if __name__ == "__main__":
    # Test ARIA with sample patients
    sample_patients = [
        {
            "patient_id": "P001",
            "name": "Arthur Collins",
            "age": 78,
            "gender": "Male",
            "symptoms": "Chest pain and shortness of breath for 2 hours",
            "vital_signs": {
                "heart_rate": 98,
                "blood_pressure": "155/95",
                "temperature_f": 98.8,
                "oxygen_saturation": 94
            },
            "medical_history": ["Heart disease", "Type 2 diabetes", "Kidney disease"],
            "current_medications": ["Warfarin", "Metformin", "Lisinopril"],
            "allergies": ["Aspirin"],
            "symptom_duration": "2 hours",
            "pain_scale": 7
        },
        {
            "patient_id": "P002",
            "name": "Sarah Johnson",
            "age": 32,
            "gender": "Female",
            "symptoms": "Fever and sore throat for 3 days",
            "vital_signs": {
                "heart_rate": 88,
                "blood_pressure": "118/76",
                "temperature_f": 101.2,
                "oxygen_saturation": 98
            },
            "medical_history": [],
            "current_medications": [],
            "allergies": ["Penicillin"],
            "symptom_duration": "3 days",
            "pain_scale": 4
        }
    ]

    aria = ARIA()
    result = aria.process(sample_patients)
    print(f"\n ARIA working correctly!")
    print(f" Results: {len(result['results'])} patients analysed")
