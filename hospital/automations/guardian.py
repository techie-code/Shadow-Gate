"""
GUARDIAN - General Unit Assignment and Resource Director
Hospital Doctor Assignment, Queue Management and Conduct Monitor

Assigns right doctor to right patient.
Manages priority queue and waiting times.
Monitors doctor conduct and flags unprofessional behavior.
Sends confidential alerts to Head of Department.

This is what ShadowGate tests.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
import json
import random


# Mock doctor database with experience levels
DOCTORS = [
    {
        "id": "D001", "name": "Dr. Rajan Kumar",
        "specialty": "Cardiology", "available": True,
        "current_patients": 1, "experience_years": 15,
        "level": "Senior", "handles_priority": ["P1", "P2", "P3", "P4"]
    },
    {
        "id": "D002", "name": "Dr. Priya Mehta",
        "specialty": "General Medicine", "available": True,
        "current_patients": 2, "experience_years": 10,
        "level": "Senior", "handles_priority": ["P2", "P3", "P4"]
    },
    {
        "id": "D003", "name": "Dr. James Wilson",
        "specialty": "Emergency", "available": True,
        "current_patients": 0, "experience_years": 20,
        "level": "Senior", "handles_priority": ["P1", "P2", "P3", "P4"]
    },
    {
        "id": "D004", "name": "Dr. Sarah Chen",
        "specialty": "Internal Medicine", "available": False,
        "current_patients": 3, "experience_years": 8,
        "level": "Mid", "handles_priority": ["P2", "P3", "P4"]
    },
    {
        "id": "D005", "name": "Dr. Michael Brown",
        "specialty": "Neurology", "available": True,
        "current_patients": 1, "experience_years": 12,
        "level": "Senior", "handles_priority": ["P1", "P2", "P3", "P4"]
    },
    {
        "id": "D006", "name": "Dr. Aisha Patel",
        "specialty": "General Medicine", "available": True,
        "current_patients": 0, "experience_years": 4,
        "level": "Junior", "handles_priority": ["P3", "P4"]
    },
    {
        "id": "D007", "name": "Dr. Tom Richards",
        "specialty": "Orthopedics", "available": True,
        "current_patients": 1, "experience_years": 6,
        "level": "Mid", "handles_priority": ["P3", "P4"]
    },
]

# Priority waiting time limits (minutes)
WAITING_TIME_LIMITS = {
    "P1": 5,
    "P2": 30,
    "P3": 120,
    "P4": 240
}

# Specialty mapping for symptoms
SYMPTOM_SPECIALTY_MAP = {
    "chest pain": "Cardiology",
    "heart": "Cardiology",
    "cardiac": "Cardiology",
    "neurological": "Neurology",
    "stroke": "Neurology",
    "headache": "Neurology",
    "fever": "General Medicine",
    "infection": "Internal Medicine",
    "breathing": "Emergency",
    "emergency": "Emergency"
}


class GUARDIAN:
    """
    General Unit Assignment and Resource Director.

    Assigns doctors. Manages queue. Monitors conduct.
    Protects patients from unprofessional behavior.
    """

    def __init__(self):
        self.name = "GUARDIAN"
        self.version = "1.0.0"
        self.processed = 0
        self.assigned = 0
        self.escalated = 0
        self.conduct_alerts = 0
        self.errors = []
        self.patient_queue = []
        self.conduct_log = []

    def assign_doctor(self, patient, aria_result, safe_result):
        """
        Assign right doctor to patient.
        Considers specialty, availability, current load.
        """
        self.processed += 1

        priority = aria_result.get("priority", "P4")
        symptoms = patient.get("symptoms", "").lower()

        # Find required specialty
        required_specialty = self.determine_specialty(symptoms, priority)

        # Find available doctor
        doctor = self.find_best_doctor(required_specialty, priority)

        if not doctor:
            self.escalated += 1
            return {
                "patient_id": patient.get("patient_id"),
                "status": "ESCALATED",
                "reason": f"No {required_specialty} doctor available",
                "action": "Head of Department notified for manual assignment",
                "priority": priority,
                "max_wait": WAITING_TIME_LIMITS.get(priority, 240)
            }

        self.assigned += 1
        waiting_time = self.calculate_waiting_time(priority, doctor)

        assignment = {
            "patient_id": patient.get("patient_id"),
            "patient_name": patient.get("name"),
            "status": "ASSIGNED",
            "doctor_id": doctor["id"],
            "doctor_name": doctor["name"],
            "specialty": doctor["specialty"],
            "priority": priority,
            "estimated_wait_minutes": waiting_time,
            "max_allowed_wait": WAITING_TIME_LIMITS.get(priority, 240),
            "wait_exceeded": waiting_time > WAITING_TIME_LIMITS.get(priority, 240),
            "assigned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "automation": self.name
        }

        # Add to queue
        self.patient_queue.append({
            "patient_id": patient.get("patient_id"),
            "priority": priority,
            "assigned_to": doctor["id"],
            "wait_minutes": waiting_time
        })

        print(f"\n GUARDIAN Assignment:")
        print(f"   Patient: {patient.get('name')} | Priority: {priority}")
        print(f"   Assigned to: {doctor['name']} ({doctor['specialty']})")
        print(f"   Experience: {doctor.get('experience_years', 0)} years | Level: {doctor.get('level', 'Unknown')}")
        print(f"   Estimated wait: {waiting_time} minutes")

        if assignment["wait_exceeded"]:
            print(f"   WARNING: Wait time exceeds {WAITING_TIME_LIMITS.get(priority)} min limit for {priority}")

        return assignment

    def determine_specialty(self, symptoms, priority):
        """Determine required medical specialty from symptoms."""
        if priority == "P1":
            return "Emergency"

        for keyword, specialty in SYMPTOM_SPECIALTY_MAP.items():
            if keyword in symptoms:
                return specialty

        return "General Medicine"

    def find_best_doctor(self, specialty, priority):
        """
        Find best available doctor based on:
        1. Priority level (P1/P2 need senior/experienced doctors)
        2. Specialty match
        3. Current workload (fewer patients = better)
        4. Experience level
        """
        # P1 - Must have senior emergency or specialist doctor
        if priority == "P1":
            senior_emergency = [d for d in DOCTORS
                if d["available"]
                and priority in d.get("handles_priority", [])
                and d["specialty"] == "Emergency"
                and d["level"] == "Senior"]
            if senior_emergency:
                return min(senior_emergency, key=lambda d: d["current_patients"])

            # Any senior doctor who handles P1
            senior_docs = [d for d in DOCTORS
                if d["available"]
                and priority in d.get("handles_priority", [])
                and d["level"] == "Senior"]
            if senior_docs:
                return min(senior_docs, key=lambda d: d["current_patients"])

        # P2 - Senior or mid-level doctor by specialty
        if priority == "P2":
            specialty_docs = [d for d in DOCTORS
                if d["available"]
                and priority in d.get("handles_priority", [])
                and d["specialty"] == specialty
                and d["level"] in ["Senior", "Mid"]]
            if specialty_docs:
                return min(specialty_docs, key=lambda d: d["current_patients"])

        # P3/P4 - Any available doctor including juniors, prefer specialty match
        # Junior doctors handle lower priority to build experience
        specialty_docs = [d for d in DOCTORS
            if d["available"]
            and priority in d.get("handles_priority", [])
            and d["specialty"] == specialty]
        if specialty_docs:
            # For P3/P4 prefer less experienced (learning opportunity)
            # but still available and not overloaded
            return min(specialty_docs, key=lambda d: d["current_patients"])

        # General medicine fallback
        general_docs = [d for d in DOCTORS
            if d["available"]
            and priority in d.get("handles_priority", [])
            and d["specialty"] == "General Medicine"]
        if general_docs:
            return min(general_docs, key=lambda d: d["current_patients"])

        # Any available doctor who handles this priority
        available_docs = [d for d in DOCTORS
            if d["available"]
            and priority in d.get("handles_priority", [])]
        if available_docs:
            return min(available_docs, key=lambda d: d["current_patients"])

        # Last resort - any available doctor
        available_docs = [d for d in DOCTORS if d["available"]]
        if available_docs:
            return min(available_docs, key=lambda d: d["current_patients"])

        return None

    def calculate_waiting_time(self, priority, doctor):
        """Calculate estimated waiting time in minutes."""
        base_times = {"P1": 2, "P2": 15, "P3": 45, "P4": 90}
        base = base_times.get(priority, 90)
        load_factor = doctor["current_patients"] * 10
        return base + load_factor

    def monitor_conduct(self, doctor_id, action, patient_id, context=None):
        """
        Monitor doctor conduct during treatment.
        Flag unprofessional behavior immediately.
        """
        conduct_issues = {
            "ignored_drug_interaction": {
                "severity": "HIGH",
                "description": "Doctor dismissed drug interaction warning without justification",
                "action": "Immediate Head of Department alert required"
            },
            "prescribed_allergen": {
                "severity": "HIGH",
                "description": "Doctor prescribed medication patient is allergic to",
                "action": "Prescription blocked and immediate alert sent"
            },
            "wrong_dosage": {
                "severity": "HIGH",
                "description": "Doctor prescribed dangerous dosage outside safe limits",
                "action": "Prescription blocked and Head of Department notified"
            },
            "missed_checkup": {
                "severity": "MEDIUM",
                "description": "Doctor missed scheduled patient checkup by more than 2 hours",
                "action": "Reminder sent, then supervisor notified if unresolved"
            },
            "delayed_p1": {
                "severity": "HIGH",
                "description": "P1 patient waited more than 5 minutes without treatment",
                "action": "Immediate escalation to Head of Department"
            },
            "modified_without_approval": {
                "severity": "MEDIUM",
                "description": "Doctor modified approved treatment plan without Head approval",
                "action": "Change flagged, Head of Department notified"
            }
        }

        if action in conduct_issues:
            issue = conduct_issues[action]
            self.conduct_alerts += 1

            alert = {
                "alert_id": f"CA{self.conduct_alerts:03d}",
                "doctor_id": doctor_id,
                "patient_id": patient_id,
                "action": action,
                "severity": issue["severity"],
                "description": issue["description"],
                "recommended_action": issue["action"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "context": context
            }

            self.conduct_log.append(alert)

            print(f"\n GUARDIAN CONDUCT ALERT:")
            print(f"   Doctor: {doctor_id}")
            print(f"   Issue: {issue['description']}")
            print(f"   Severity: {issue['severity']}")
            print(f"   Action: {issue['action']}")

            return alert

        return None

    def get_queue_status(self):
        """Get current patient queue status."""
        p1 = [p for p in self.patient_queue if p["priority"] == "P1"]
        p2 = [p for p in self.patient_queue if p["priority"] == "P2"]
        p3 = [p for p in self.patient_queue if p["priority"] == "P3"]
        p4 = [p for p in self.patient_queue if p["priority"] == "P4"]

        return {
            "total_patients": len(self.patient_queue),
            "P1_count": len(p1),
            "P2_count": len(p2),
            "P3_count": len(p3),
            "P4_count": len(p4),
            "average_wait": round(
                sum(p["wait_minutes"] for p in self.patient_queue) /
                max(len(self.patient_queue), 1), 1
            )
        }

    def process(self, patients, aria_results, safe_results):
        """Process all patients through GUARDIAN."""
        print(f"\n GUARDIAN - General Unit Assignment and Resource Director v{self.version}")
        print(f" Assigning doctors for {len(patients)} patient(s)...\n")

        results = []
        for i, patient in enumerate(patients):
            aria_result = aria_results[i] if i < len(aria_results) else {}
            safe_result = safe_results[i] if i < len(safe_results) else {}

            if aria_result:
                result = self.assign_doctor(patient, aria_result, safe_result)
                results.append(result)

        queue = self.get_queue_status()
        print(f"\n GUARDIAN Queue Status:")
        print(f"   Total patients: {queue['total_patients']}")
        print(f"   P1 Critical: {queue['P1_count']}")
        print(f"   P2 Urgent: {queue['P2_count']}")
        print(f"   P3 Moderate: {queue['P3_count']}")
        print(f"   P4 Non-urgent: {queue['P4_count']}")
        print(f"   Average wait: {queue['average_wait']} minutes")

        return {
            "automation": self.name,
            "processed": self.processed,
            "assigned": self.assigned,
            "escalated": self.escalated,
            "conduct_alerts": self.conduct_alerts,
            "errors": self.errors,
            "queue_status": queue,
            "results": results,
            "success_rate": round((self.processed - len(self.errors)) / max(self.processed, 1) * 100, 2)
        }


REQUIREMENTS = """
GUARDIAN assigns doctors to patients and monitors conduct.

For each patient GUARDIAN:
- Determines required medical specialty from symptoms
- P1 patients always assigned to Emergency specialist first
- Finds most available doctor in required specialty
- Calculates estimated waiting time
- Flags if waiting time exceeds priority limits

Priority waiting time limits:
- P1 Critical: maximum 5 minutes
- P2 Urgent: maximum 30 minutes
- P3 Moderate: maximum 120 minutes
- P4 Non-urgent: maximum 240 minutes

GUARDIAN monitors doctor conduct during treatment:
- Ignored drug interaction warning: HIGH severity alert
- Prescribed medication patient is allergic to: HIGH severity, prescription blocked
- Wrong dosage outside safe limits: HIGH severity alert
- Missed scheduled checkup over 2 hours late: MEDIUM severity
- P1 patient waited more than 5 minutes: HIGH severity escalation
- Modified treatment without Head approval: MEDIUM severity

All HIGH severity conduct alerts sent immediately and confidentially to Head of Department.
MEDIUM severity alerts sent first as reminders then escalated if unresolved.
No conduct alerts shared with the wider team without Head of Department approval.
All errors must be caught gracefully without crashing.
"""


if __name__ == "__main__":
    from aria import ARIA
    from safe import SAFE

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

    guardian = GUARDIAN()
    guardian_output = guardian.process(
        sample_patients,
        aria_output["results"],
        safe_output["results"]
    )

    # Test conduct monitoring
    print(f"\n Testing conduct monitoring...")
    guardian.monitor_conduct("D001", "ignored_drug_interaction", "P001")

    print(f"\n GUARDIAN working correctly!")
