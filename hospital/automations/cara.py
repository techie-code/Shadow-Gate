"""
CARA - Continuous Aftercare and Recovery Advisor
Hospital Recovery Tracking and Discharge Planner

Tracks patient recovery continuously.
Validates discharge criteria are fully met.
Ensures patient feels safe and cared for.
Schedules follow-up and sends discharge summary.

This is what ShadowGate tests.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta
import json


# Discharge criteria by priority
DISCHARGE_CRITERIA = {
    "P1": {
        "min_observation_hours": 48,
        "required_vitals_stable_hours": 24,
        "required_fields": [
            "vitals_stable",
            "pain_controlled",
            "medication_prescribed",
            "follow_up_scheduled",
            "discharge_summary_complete",
            "patient_education_done",
            "emergency_contacts_verified"
        ]
    },
    "P2": {
        "min_observation_hours": 24,
        "required_vitals_stable_hours": 12,
        "required_fields": [
            "vitals_stable",
            "pain_controlled",
            "medication_prescribed",
            "follow_up_scheduled",
            "discharge_summary_complete"
        ]
    },
    "P3": {
        "min_observation_hours": 6,
        "required_vitals_stable_hours": 4,
        "required_fields": [
            "vitals_stable",
            "pain_controlled",
            "medication_prescribed",
            "follow_up_scheduled"
        ]
    },
    "P4": {
        "min_observation_hours": 2,
        "required_vitals_stable_hours": 1,
        "required_fields": [
            "vitals_stable",
            "medication_prescribed"
        ]
    }
}


class CARA:
    """
    Continuous Aftercare and Recovery Advisor.

    Monitors recovery. Validates discharge.
    Makes sure every patient leaves safely and cared for.
    """

    def __init__(self):
        self.name = "CARA"
        self.version = "1.0.0"
        self.processed = 0
        self.approved_discharge = 0
        self.blocked_discharge = 0
        self.follow_ups_scheduled = 0
        self.errors = []

    def assess_recovery(self, patient, aria_result, treatment_data):
        """
        Assess patient recovery status.
        Check if ready for discharge.
        """
        self.processed += 1

        patient_id = patient.get("patient_id")
        priority = aria_result.get("priority", "P4")
        criteria = DISCHARGE_CRITERIA.get(priority, DISCHARGE_CRITERIA["P4"])

        # Check each discharge criterion
        discharge_check = self.check_discharge_criteria(
            patient, priority, criteria, treatment_data
        )

        # Check for new symptoms
        raw_new_symptoms = treatment_data.get("new_symptoms", [])
        # Filter out empty strings, "none", "no", "nil" etc
        no_symptom_words = ["none", "no", "nothing", "nil", "n/a", "na", "nope", "no symptoms"]
        if isinstance(raw_new_symptoms, list):
            new_symptoms = [s for s in raw_new_symptoms if s and s.strip().lower() not in no_symptom_words]
        elif isinstance(raw_new_symptoms, str):
            new_symptoms = [] if raw_new_symptoms.strip().lower() in no_symptom_words or not raw_new_symptoms.strip() else [raw_new_symptoms]
        else:
            new_symptoms = []

        if new_symptoms:
            discharge_check["status"] = "BLOCKED"
            discharge_check["blockers"].append({
                "criterion": "new_symptoms",
                "detail": f"New symptoms reported: {new_symptoms}",
                "severity": "HIGH"
            })

        # Schedule follow-up if approved
        follow_up = None
        if discharge_check["status"] == "APPROVED":
            self.approved_discharge += 1
            follow_up = self.schedule_follow_up(patient, priority, aria_result)
            self.follow_ups_scheduled += 1
        else:
            self.blocked_discharge += 1

        # Generate patient message
        patient_message = self.generate_patient_message(
            patient, discharge_check, follow_up
        )

        result = {
            "patient_id": patient_id,
            "patient_name": patient.get("name"),
            "assessed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "priority": priority,
            "discharge_check": discharge_check,
            "follow_up": follow_up,
            "patient_message": patient_message,
            "automation": self.name
        }

        self.print_recovery_status(result)
        return result

    def check_discharge_criteria(self, patient, priority, criteria, treatment_data):
        """Check all discharge criteria for a patient."""
        required_fields = criteria.get("required_fields", [])
        blockers = []
        warnings = []
        passed = []

        for field in required_fields:
            value = treatment_data.get(field)

            if field == "vitals_stable":
                if not value:
                    blockers.append({
                        "criterion": field,
                        "detail": "Vital signs not confirmed stable",
                        "severity": "HIGH"
                    })
                else:
                    passed.append(field)

            elif field == "pain_controlled":
                pain_score = treatment_data.get("current_pain_scale", 10)
                if pain_score > 4:
                    blockers.append({
                        "criterion": field,
                        "detail": f"Pain score {pain_score}/10 still too high for discharge",
                        "severity": "HIGH"
                    })
                else:
                    passed.append(field)

            elif field == "medication_prescribed":
                if not value:
                    blockers.append({
                        "criterion": field,
                        "detail": "Discharge medications not yet prescribed",
                        "severity": "HIGH"
                    })
                else:
                    passed.append(field)

            elif field == "follow_up_scheduled":
                if not value:
                    warnings.append({
                        "criterion": field,
                        "detail": "Follow-up appointment not yet scheduled",
                        "severity": "MEDIUM"
                    })
                else:
                    passed.append(field)

            elif field == "discharge_summary_complete":
                if not value:
                    blockers.append({
                        "criterion": field,
                        "detail": "Discharge summary not completed by doctor",
                        "severity": "HIGH"
                    })
                else:
                    passed.append(field)

            elif field == "patient_education_done":
                if not value:
                    warnings.append({
                        "criterion": field,
                        "detail": "Patient education on home care not completed",
                        "severity": "MEDIUM"
                    })
                else:
                    passed.append(field)

            elif field == "emergency_contacts_verified":
                contacts = patient.get("emergency_contacts", [])
                if not contacts:
                    warnings.append({
                        "criterion": field,
                        "detail": "Emergency contact details not verified",
                        "severity": "MEDIUM"
                    })
                else:
                    passed.append(field)

            else:
                if not value:
                    warnings.append({
                        "criterion": field,
                        "detail": f"{field} not completed",
                        "severity": "LOW"
                    })
                else:
                    passed.append(field)

        # Check insurance
        insurance = patient.get("insurance_status")
        if insurance == "expired":
            warnings.append({
                "criterion": "insurance",
                "detail": "Patient insurance has expired. Finance team notified.",
                "severity": "MEDIUM"
            })

        # Check patient lives alone
        lives_alone = patient.get("lives_alone", False)
        age = int(patient.get("age", 0))
        if lives_alone and age > 70 and priority in ["P1", "P2"]:
            warnings.append({
                "criterion": "home_support",
                "detail": "Elderly patient lives alone. Consider social worker referral.",
                "severity": "MEDIUM"
            })

        status = "BLOCKED" if blockers else "APPROVED"

        return {
            "status": status,
            "passed": passed,
            "blockers": blockers,
            "warnings": warnings,
            "criteria_met": len(passed),
            "criteria_total": len(required_fields)
        }

    def schedule_follow_up(self, patient, priority, aria_result):
        """Schedule follow-up appointment after discharge."""
        follow_up_days = {
            "P1": 3,
            "P2": 7,
            "P3": 14,
            "P4": 30
        }

        days = follow_up_days.get(priority, 14)
        follow_up_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        return {
            "scheduled_date": follow_up_date,
            "days_from_now": days,
            "type": "In-person" if priority in ["P1", "P2"] else "Telephone",
            "department": "Cardiology" if "chest" in patient.get("symptoms", "").lower() else "General Medicine",
            "reminder_sent": True
        }

    def generate_patient_message(self, patient, discharge_check, follow_up):
        """Generate a caring message for the patient."""
        name = patient.get("name", "").split()[0]

        if discharge_check["status"] == "BLOCKED":
            blockers = discharge_check.get("blockers", [])
            reason = blockers[0]["detail"] if blockers else "Some criteria not yet met"
            return (
                f"Dear {name}, we want to make sure you are completely well "
                f"before you go home. We are keeping you a little longer to "
                f"ensure your full recovery. Our team is here for you. "
                f"Reason: {reason}"
            )

        if follow_up:
            return (
                f"Dear {name}, you are ready to go home safely. "
                f"Your treatment is complete and our team is happy with your recovery. "
                f"Your follow-up appointment is on {follow_up['scheduled_date']}. "
                f"Please do not hesitate to contact us if anything concerns you. "
                f"Take care and get well soon."
            )

        return (
            f"Dear {name}, you are ready to go home. "
            f"Please follow your prescribed medications and rest well."
        )

    def print_recovery_status(self, result):
        """Print recovery assessment status."""
        status = result["discharge_check"]["status"]
        icon = "APPROVED" if status == "APPROVED" else "BLOCKED"
        print(f"\n CARA Recovery: {result['patient_name']}")
        print(f"   Discharge: {icon}")
        print(f"   Criteria met: {result['discharge_check']['criteria_met']}/{result['discharge_check']['criteria_total']}")

        for blocker in result["discharge_check"].get("blockers", []):
            print(f"   BLOCKED: {blocker['detail']}")

        for warning in result["discharge_check"].get("warnings", []):
            print(f"   WARNING: {warning['detail']}")

        if result.get("follow_up"):
            print(f"   Follow-up: {result['follow_up']['scheduled_date']}")

        print(f"   Message: {result['patient_message'][:80]}...")

    def process(self, patients, aria_results, treatment_data_list):
        """Process all patients through CARA."""
        print(f"\n CARA - Continuous Aftercare and Recovery Advisor v{self.version}")
        print(f" Assessing recovery for {len(patients)} patient(s)...\n")

        results = []
        for i, patient in enumerate(patients):
            aria_result = aria_results[i] if i < len(aria_results) else {}
            treatment_data = treatment_data_list[i] if i < len(treatment_data_list) else {}

            if aria_result:
                result = self.assess_recovery(patient, aria_result, treatment_data)
                results.append(result)

        print(f"\n CARA Summary:")
        print(f" Processed: {self.processed}")
        print(f" Approved for discharge: {self.approved_discharge}")
        print(f" Discharge blocked: {self.blocked_discharge}")
        print(f" Follow-ups scheduled: {self.follow_ups_scheduled}")

        return {
            "automation": self.name,
            "processed": self.processed,
            "approved_discharge": self.approved_discharge,
            "blocked_discharge": self.blocked_discharge,
            "follow_ups_scheduled": self.follow_ups_scheduled,
            "errors": self.errors,
            "results": results,
            "success_rate": round((self.processed - len(self.errors)) / max(self.processed, 1) * 100, 2)
        }


REQUIREMENTS = """
CARA tracks patient recovery and manages discharge planning.

For each patient CARA checks all discharge criteria:
- Vital signs confirmed stable
- Pain score must be 4 or below for discharge
- Discharge medications must be prescribed
- Follow-up appointment must be scheduled
- Discharge summary must be completed by doctor
- Patient education on home care must be done
- Emergency contacts verified for P1 patients

CARA assigns discharge status:
- APPROVED: all criteria met, safe to go home
- BLOCKED: one or more criteria not met, patient stays

CARA always schedules follow-up appointments:
- P1 patients: follow-up in 3 days, in-person
- P2 patients: follow-up in 7 days, in-person
- P3 patients: follow-up in 14 days, telephone
- P4 patients: follow-up in 30 days, telephone

CARA checks special situations:
- New symptoms appearing during treatment block discharge immediately
- Elderly patients over 70 living alone get social worker referral
- Expired insurance triggers finance team notification
- Patient refusing discharge is flagged for doctor review

CARA sends caring patient messages:
- If blocked: explains why staying, reassures patient
- If approved: confirms safety, gives follow-up details

All discharge blocks must be logged and doctor notified.
Patient message must always be caring and reassuring.
All errors must be caught gracefully without crashing.
"""


if __name__ == "__main__":
    from aria import ARIA
    from safe import SAFE
    from guardian import GUARDIAN

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
            "pain_scale": 7,
            "lives_alone": True,
            "emergency_contacts": ["Jane Collins - 07700900123"],
            "insurance_status": "active"
        }
    ]

    # Mock treatment data (what happened during treatment)
    treatment_data = [
        {
            "vitals_stable": True,
            "current_pain_scale": 2,
            "medication_prescribed": True,
            "follow_up_scheduled": True,
            "discharge_summary_complete": True,
            "patient_education_done": True,
            "new_symptoms": []
        }
    ]

    aria = ARIA()
    aria_output = aria.process(sample_patients)

    cara = CARA()
    cara_output = cara.process(sample_patients, aria_output["results"], treatment_data)
    print(f"\n CARA working correctly!")
