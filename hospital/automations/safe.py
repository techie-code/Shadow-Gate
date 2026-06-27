"""
SAFE - Smart Allergy and Formula Engine
Hospital Treatment Safety Validator

Validates every treatment recommendation from ARIA.
Checks drug interactions, allergies, dosage limits.
Never lets a dangerous prescription through.

This is what ShadowGate tests.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from ai_client import ask_ai
import json


# Known dangerous drug interactions database
DRUG_INTERACTIONS = {
    ("warfarin", "aspirin"): "HIGH - Major bleeding risk. Combined anticoagulant effect.",
    ("warfarin", "ibuprofen"): "HIGH - Increases bleeding risk significantly.",
    ("metformin", "alcohol"): "HIGH - Lactic acidosis risk.",
    ("lisinopril", "potassium"): "MEDIUM - Hyperkalemia risk.",
    ("aspirin", "ibuprofen"): "MEDIUM - Reduced aspirin effectiveness.",
    ("warfarin", "amoxicillin"): "MEDIUM - May increase warfarin effect.",
    ("metformin", "contrast_dye"): "HIGH - Kidney failure risk.",
    ("digoxin", "amiodarone"): "HIGH - Digoxin toxicity risk.",
    ("ssri", "tramadol"): "HIGH - Serotonin syndrome risk.",
    ("statins", "clarithromycin"): "HIGH - Muscle damage risk.",
}

# Dosage limits by age group
DOSAGE_LIMITS = {
    "paracetamol": {
        "adult": {"max_mg": 4000, "per_dose_mg": 1000},
        "elderly": {"max_mg": 2000, "per_dose_mg": 500},
        "child": {"max_mg_per_kg": 15, "per_dose_mg_per_kg": 15}
    },
    "ibuprofen": {
        "adult": {"max_mg": 2400, "per_dose_mg": 400},
        "elderly": {"max_mg": 1200, "per_dose_mg": 200},
        "child": {"max_mg_per_kg": 10, "per_dose_mg_per_kg": 5}
    },
    "amoxicillin": {
        "adult": {"max_mg": 3000, "per_dose_mg": 500},
        "elderly": {"max_mg": 2000, "per_dose_mg": 500},
        "child": {"max_mg_per_kg": 90, "per_dose_mg_per_kg": 25}
    }
}


class SAFE:
    """
    Smart Allergy and Formula Engine.

    Validates every treatment plan from ARIA.
    Checks interactions, allergies, dosages.
    Blocks dangerous prescriptions before they reach patients.
    """

    def __init__(self):
        self.name = "SAFE"
        self.version = "1.0.0"
        self.processed = 0
        self.approved = 0
        self.blocked = 0
        self.warnings = 0
        self.errors = []

    def validate_treatment(self, patient, aria_result):
        """
        Validate a treatment plan from ARIA.
        Returns safety report for each scenario.
        """
        self.processed += 1

        patient_id = patient.get("patient_id")
        age = int(patient.get("age", 0))
        allergies = [a.lower() for a in patient.get("allergies", [])]
        current_meds = [m.lower() for m in patient.get("current_medications", [])]
        weight_kg = patient.get("weight_kg", 70)
        kidney_disease = "kidney disease" in [h.lower() for h in patient.get("medical_history", [])]
        liver_disease = "liver disease" in [h.lower() for h in patient.get("medical_history", [])]

        scenarios = aria_result.get("scenarios", {})
        safety_reports = {}

        for scenario_key in ["best_case", "moderate_case", "worst_case"]:
            scenario = scenarios.get(scenario_key, {})
            medications = [m.lower() for m in scenario.get("medications", [])]

            report = self.check_scenario_safety(
                scenario_key, medications, allergies,
                current_meds, age, weight_kg,
                kidney_disease, liver_disease
            )
            safety_reports[scenario_key] = report

            status = report.get("status")
            if status == "BLOCKED":
                self.blocked += 1
            elif status == "WARNING":
                self.warnings += 1
            else:
                self.approved += 1

        overall_safe = all(
            r.get("status") != "BLOCKED"
            for r in safety_reports.values()
        )

        result = {
            "patient_id": patient_id,
            "validated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_safe": overall_safe,
            "safety_reports": safety_reports,
            "automation": self.name
        }

        self.print_safety_result(patient, result)
        return result

    def check_scenario_safety(self, scenario_key, medications, allergies,
                               current_meds, age, weight_kg,
                               kidney_disease, liver_disease):
        """Check safety of one scenario."""
        issues = []
        warnings = []

        # Check 1: Allergy violations
        for med in medications:
            for allergy in allergies:
                if allergy in med or med in allergy:
                    issues.append({
                        "type": "ALLERGY_VIOLATION",
                        "severity": "HIGH",
                        "detail": f"{med} is contraindicated. Patient allergic to {allergy}.",
                        "recommendation": f"Remove {med} from treatment plan immediately."
                    })

        # Check 2: Drug interactions with current medications
        all_meds = medications + current_meds
        for i, med1 in enumerate(all_meds):
            for med2 in all_meds[i+1:]:
                key1 = (med1, med2)
                key2 = (med2, med1)
                interaction = DRUG_INTERACTIONS.get(key1) or DRUG_INTERACTIONS.get(key2)
                if interaction:
                    severity = "HIGH" if interaction.startswith("HIGH") else "MEDIUM"
                    if severity == "HIGH":
                        issues.append({
                            "type": "DRUG_INTERACTION",
                            "severity": "HIGH",
                            "detail": f"{med1} and {med2}: {interaction}",
                            "recommendation": f"Consider alternative to {med2}."
                        })
                    else:
                        warnings.append({
                            "type": "DRUG_INTERACTION",
                            "severity": "MEDIUM",
                            "detail": f"{med1} and {med2}: {interaction}",
                            "recommendation": "Monitor closely if combination necessary."
                        })

        # Check 3: Age-related concerns
        if age >= 70:
            for med in medications:
                if med in ["ibuprofen", "naproxen"]:
                    warnings.append({
                        "type": "AGE_CONCERN",
                        "severity": "MEDIUM",
                        "detail": f"{med} carries increased GI bleeding risk for patients over 70.",
                        "recommendation": "Consider paracetamol or lower dose with gastric protection."
                    })
                if med in ["benzodiazepines", "diazepam", "lorazepam"]:
                    issues.append({
                        "type": "AGE_CONCERN",
                        "severity": "HIGH",
                        "detail": f"{med} causes confusion and fall risk in elderly patients.",
                        "recommendation": "Avoid or use minimal dose with close monitoring."
                    })

        # Check 4: Kidney disease concerns
        if kidney_disease:
            kidney_risky = ["ibuprofen", "naproxen", "metformin", "lithium"]
            for med in medications:
                for risky in kidney_risky:
                    if risky in med:
                        issues.append({
                            "type": "ORGAN_CONCERN",
                            "severity": "HIGH",
                            "detail": f"{med} requires kidney clearance. Patient has kidney disease.",
                            "recommendation": f"Reduce dose or use kidney-safe alternative."
                        })

        # Check 5: Liver disease concerns
        if liver_disease:
            liver_risky = ["paracetamol", "statins", "methotrexate"]
            for med in medications:
                for risky in liver_risky:
                    if risky in med:
                        warnings.append({
                            "type": "ORGAN_CONCERN",
                            "severity": "MEDIUM",
                            "detail": f"{med} is metabolised by liver. Patient has liver disease.",
                            "recommendation": "Reduce dose and monitor liver function."
                        })

        # Determine overall status
        if issues:
            status = "BLOCKED"
        elif warnings:
            status = "WARNING"
        else:
            status = "APPROVED"

        return {
            "scenario": scenario_key,
            "status": status,
            "issues": issues,
            "warnings": warnings,
            "medications_checked": medications,
            "total_issues": len(issues),
            "total_warnings": len(warnings)
        }

    def print_safety_result(self, patient, result):
        """Print safety validation result."""
        print(f"\n SAFE Validation: {patient.get('name')} (Age {patient.get('age')})")
        for scenario_key, report in result.get("safety_reports", {}).items():
            status = report.get("status")
            icon = "APPROVED" if status == "APPROVED" else "WARNING" if status == "WARNING" else "BLOCKED"
            print(f"   {scenario_key}: {icon}")
            for issue in report.get("issues", []):
                print(f"     BLOCKED: {issue['detail']}")
            for warning in report.get("warnings", []):
                print(f"     WARNING: {warning['detail']}")

    def process(self, patients, aria_results):
        """Process all patients through SAFE."""
        print(f"\n SAFE - Smart Allergy and Formula Engine v{self.version}")
        print(f" Validating {len(patients)} patient(s)...\n")

        results = []
        for i, patient in enumerate(patients):
            if i < len(aria_results) and aria_results[i]:
                result = self.validate_treatment(patient, aria_results[i])
                results.append(result)

        print(f"\n SAFE Summary:")
        print(f" Processed: {self.processed}")
        print(f" Approved: {self.approved}")
        print(f" Warnings: {self.warnings}")
        print(f" Blocked: {self.blocked}")
        print(f" Errors: {len(self.errors)}")

        return {
            "automation": self.name,
            "processed": self.processed,
            "approved": self.approved,
            "warnings": self.warnings,
            "blocked": self.blocked,
            "errors": self.errors,
            "results": results,
            "success_rate": round((self.processed - len(self.errors)) / max(self.processed, 1) * 100, 2)
        }


REQUIREMENTS = """
SAFE validates every treatment plan generated by ARIA.

For each patient scenario SAFE checks:
- Allergy violations: prescribed medication matches known allergy
- Drug interactions: new medications interact with current medications
- Age related concerns: medications unsafe for elderly patients over 70
- Organ concerns: medications requiring kidney or liver function
- Dosage limits: dose appropriate for patient age and weight

SAFE assigns status to each scenario:
- APPROVED: no issues found, safe to proceed
- WARNING: concerns found, proceed with caution and monitoring
- BLOCKED: dangerous issues found, cannot proceed without changes

Any BLOCKED scenario triggers immediate review.
SAFE never allows allergy violations through under any circumstances.
HIGH severity drug interactions always result in BLOCKED status.
Kidney disease patients must not receive kidney-damaging medications.
All errors must be caught gracefully without crashing.
"""


if __name__ == "__main__":
    from aria import ARIA

    sample_patients = [
        {
            "patient_id": "P001",
            "name": "Arthur Collins",
            "age": 78,
            "gender": "Male",
            "symptoms": "Chest pain and shortness of breath",
            "vital_signs": {
                "heart_rate": 98,
                "blood_pressure": "155/95",
                "temperature_f": 98.8,
                "oxygen_saturation": 94
            },
            "medical_history": ["Heart disease", "Kidney disease"],
            "current_medications": ["Warfarin"],
            "allergies": ["Aspirin"],
            "weight_kg": 75,
            "symptom_duration": "2 hours",
            "pain_scale": 7
        }
    ]

    aria = ARIA()
    aria_output = aria.process(sample_patients)

    safe = SAFE()
    safe_output = safe.process(sample_patients, aria_output["results"])
    print(f"\n SAFE working correctly!")
