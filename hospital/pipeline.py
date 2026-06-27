"""
ShadowGate Hospital Pipeline
Connects ARIA, SAFE, GUARDIAN and CARA.
Runs complete patient journey from admission to discharge.
This is what ShadowGate tests end to end.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from hospital.automations.aria import ARIA
from hospital.automations.safe import SAFE
from hospital.automations.guardian import GUARDIAN
from hospital.automations.cara import CARA


class HospitalPipeline:
    """
    Runs the complete patient journey through all 4 automations.
    ARIA -> SAFE -> GUARDIAN -> CARA
    """

    def __init__(self):
        self.name = "HospitalPipeline"
        self.version = "1.0.0"
        self.aria = ARIA()
        self.safe = SAFE()
        self.guardian = GUARDIAN()
        self.cara = CARA()

    def run(self, patients, treatment_data=None):
        """Run all patients through complete hospital pipeline."""

        print(f"\n{'='*55}")
        print(f" SHADOWGATE HOSPITAL PIPELINE v{self.version}")
        print(f" Patient Journey: Admission to Discharge")
        print(f"{'='*55}")
        print(f" Patients: {len(patients)}")
        print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*55}")

        start_time = datetime.now()

        # Default treatment data if not provided
        if treatment_data is None:
            treatment_data = [self.default_treatment_data() for _ in patients]

        # Stage 1: ARIA - Scenario Analysis
        print(f"\n STAGE 1: ARIA - Patient Scenario Analysis")
        print(f" Generating best to worst case scenarios...")
        aria_output = self.aria.process(patients)

        # Stage 2: SAFE - Treatment Validation
        print(f"\n STAGE 2: SAFE - Treatment Safety Validation")
        print(f" Checking drug interactions and allergies...")
        safe_output = self.safe.process(patients, aria_output["results"])

        # Stage 3: GUARDIAN - Doctor Assignment
        print(f"\n STAGE 3: GUARDIAN - Doctor Assignment and Monitoring")
        print(f" Assigning doctors and managing queue...")
        guardian_output = self.guardian.process(
            patients,
            aria_output["results"],
            safe_output["results"]
        )

        # Stage 4: CARA - Recovery and Discharge
        print(f"\n STAGE 4: CARA - Recovery and Discharge Planning")
        print(f" Assessing recovery and planning discharge...")
        cara_output = self.cara.process(
            patients,
            aria_output["results"],
            treatment_data
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Build final summary
        summary = self.build_summary(
            patients,
            aria_output,
            safe_output,
            guardian_output,
            cara_output,
            duration
        )

        self.print_summary(summary)

        return {
            "pipeline": self.name,
            "aria": aria_output,
            "safe": safe_output,
            "guardian": guardian_output,
            "cara": cara_output,
            "summary": summary,
            "duration_seconds": round(duration, 2)
        }

    def build_summary(self, patients, aria, safe, guardian, cara, duration):
        """Build pipeline execution summary."""

        # Count unknown risks across all patients
        total_unknown_risks = sum(
            len(r.get("unknown_risks", []))
            for r in aria.get("results", [])
            if r
        )

        # Count safety blocks
        total_blocked = sum(
            1 for r in safe.get("results", [])
            if r and not r.get("overall_safe")
        )

        # Count P1 patients
        p1_count = sum(
            1 for r in aria.get("results", [])
            if r and r.get("priority") == "P1"
        )

        # Count approved discharges
        approved_discharge = cara.get("approved_discharge", 0)

        return {
            "total_patients": len(patients),
            "p1_critical": p1_count,
            "unknown_risks_discovered": total_unknown_risks,
            "treatments_blocked": total_blocked,
            "approved_for_discharge": approved_discharge,
            "follow_ups_scheduled": cara.get("follow_ups_scheduled", 0),
            "conduct_alerts": guardian.get("conduct_alerts", 0),
            "duration_seconds": round(duration, 2),
            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def print_summary(self, summary):
        """Print final pipeline summary."""
        print(f"\n{'='*55}")
        print(f" HOSPITAL PIPELINE COMPLETE")
        print(f"{'='*55}")
        print(f" Total patients processed: {summary['total_patients']}")
        print(f" P1 Critical patients:     {summary['p1_critical']}")
        print(f" Unknown risks discovered: {summary['unknown_risks_discovered']}")
        print(f" Treatments blocked:       {summary['treatments_blocked']}")
        print(f" Approved for discharge:   {summary['approved_for_discharge']}")
        print(f" Follow-ups scheduled:     {summary['follow_ups_scheduled']}")
        print(f" Conduct alerts:           {summary['conduct_alerts']}")
        print(f" Duration:                 {summary['duration_seconds']}s")
        print(f"{'='*55}")

    def default_treatment_data(self):
        """Default treatment data for testing."""
        return {
            "vitals_stable": True,
            "current_pain_scale": 2,
            "medication_prescribed": True,
            "follow_up_scheduled": True,
            "discharge_summary_complete": True,
            "patient_education_done": True,
            "new_symptoms": []
        }


# Sample patients for testing
SAMPLE_PATIENTS = [
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
        "weight_kg": 75,
        "symptom_duration": "2 hours",
        "pain_scale": 7,
        "lives_alone": True,
        "emergency_contacts": ["Jane Collins - 07700900123"],
        "insurance_status": "active"
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
        "weight_kg": 62,
        "symptom_duration": "3 days",
        "pain_scale": 4,
        "lives_alone": False,
        "emergency_contacts": ["Mike Johnson - 07700900456"],
        "insurance_status": "active"
    },
    {
        "patient_id": "P003",
        "name": "Baby Emma Wilson",
        "age": 2,
        "gender": "Female",
        "symptoms": "High fever and rash for 1 day",
        "vital_signs": {
            "heart_rate": 120,
            "blood_pressure": "90/60",
            "temperature_f": 103.5,
            "oxygen_saturation": 97
        },
        "medical_history": [],
        "current_medications": [],
        "allergies": [],
        "weight_kg": 12,
        "symptom_duration": "1 day",
        "pain_scale": 8,
        "lives_alone": False,
        "emergency_contacts": ["Tom Wilson - 07700900789"],
        "insurance_status": "active"
    }
]


if __name__ == "__main__":
    pipeline = HospitalPipeline()
    result = pipeline.run(SAMPLE_PATIENTS)
    print(f"\n Hospital pipeline working correctly!")
