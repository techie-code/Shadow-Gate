# ShadowGate
AI-Powered Hospital Automation Testing Platform 

We test what you know. We discover what you don't.

## What is ShadowGate? 

ShadowGate is an AI-powered testing platform that validates hospital automation workflows before they go live. It tests four critical hospital automations across 8 stages, discovers unknown risks nobody thought to test, and keeps humans in the loop at every critical decision point.

## The Problem

Hospital automation systems are tested against known scenarios. But what about the risks nobody thought to write tests for?

A patient on Warfarin gets prescribed Clopidogrel. The automation approves it. Nobody wrote a test for that interaction. The patient bleeds.

ShadowGate finds those risks before they reach patients.

## The Four Automations

| Automation | Full Name | Role |
|---|---|---|
| ARIA | Adaptive Risk Intelligence Analyser | Generates best/moderate/worst case scenarios. Discovers unknown risks using AI. |
| SAFE | Smart Allergy and Formula Engine | Validates drug interactions, allergies and dosage limits across all scenarios. |
| GUARDIAN | General Unit Assignment and Resource Director | Assigns doctors by experience level and availability. Monitors professional conduct. |
| CARA | Continuous Aftercare and Recovery Advisor | Tracks recovery, validates discharge criteria, schedules follow-ups. |

## Key Features

### Unknown Unknown Detection

ARIA discovers risks nobody wrote tests for. In each run it finds risks like:

- Warfarin + Heparin bleeding risk in elderly patients with kidney disease
- Metformin-induced lactic acidosis in patients with decreased kidney function
- Vancomycin-induced ototoxicity and nephrotoxicity in pediatric patients

### Why Priority Is Rule-Based, Not AI-Decided

Triage priority (P1-P4) is assigned using fixed clinical rules based on vitals, symptoms, age, and pain scale, not by asking an AI model to guess. Early testing showed AI-assigned priority was inconsistent (a healthy adult with a mild fever was sometimes flagged as critical). Hospitals already have proven triage protocols; AI guessing at something this safety-critical is the wrong tool for the job.

AI is used specifically where it adds unique value: ARIA's unknown risk discovery, where there is no existing rulebook to follow, and the ShadowGate testing engine's own scenario generation and analysis.

### Experience-Based Doctor Assignment

- P1 Critical: Senior doctors (20+ years experience)
- P2 Urgent: Senior doctors by specialty and availability
- P3/P4: Junior doctors (learning opportunity)

### Human in the Loop

- Confidential HTML email to Head of Department with 4 buttons: Approve Best Case, Approve Moderate Case, Approve Worst Case, Request Meeting with Chief Doctor
- Automatic reminder after 5 minutes (Slack to technical/deployment channel)
- Escalation with CC to senior management after 10 minutes (Slack to technical/deployment channel)
- Slack to doctor ONLY after Head approves (separate healthcare channel)
- Once approved, all other approval buttons are disabled for that patient

## ShadowGate Testing Pipeline (8 Stages)

1. Change Detection
2. Environment Simulation (AI-generated test scenarios)
3. Coverage Intelligence (finds gaps)
4. Chaos Injection (optional)
5. Automation Run
6. Validation
7. Test Health Scan
8. Release Guardian Analysis

## Results

- 95/100 confidence score
- 100% pass rate across all 4 automations
- GREEN deployment signal
- 9-12 unknown risks discovered per run

## Architecture

```
Patient Admitted
      |
      v
ARIA (AI-powered)
  Generates scenarios
  Discovers unknown risks
      |
      v
SAFE
  Validates drug interactions
  Checks allergies and dosages
      |
      v
GUARDIAN
  Assigns doctor by experience
  Monitors conduct
      |
      v
CARA
  Validates discharge criteria
  Schedules follow-up
      |
      v
ShadowGate Tests All 4 Automations
  8-stage pipeline
  95/100 confidence
  GREEN signal
      |
      v
Alerts
  Email to Head of Department (P1/P2)
  Slack to doctor (after approval, or directly for P3/P4)
```

## Tech Stack

| Component | Technology |
|---|---|
| Orchestration | UiPath Automation Cloud |
| Agent Type | Coded Agent |
| AI Engine | Groq (Llama 3.3 70B) |
| AI Integration (in progress) | Claude via UiPath AI Fabric |
| Backend | Python 3.11 |
| Database | SQLite |
| Notifications | Gmail SMTP + Slack Webhooks |
| Dashboard | HTML/CSS/JavaScript |
| API | Flask |

## Setup

### 1. Clone the repository

```
git clone https://github.com/yourusername/shadowgate.git
cd shadowgate
```

### 2. Create virtual environment

```
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Configure environment

Create a `.env` file:

```
# AI
GROQ_API_KEY=your_groq_key

# AI (Claude via UiPath - optional, falls back to Groq)
UIPATH_CLIENT_ID=your_client_id
UIPATH_CLIENT_SECRET=your_client_secret
UIPATH_TENANT_NAME=your_tenant
UIPATH_ACCOUNT_NAME=your_account

# Email alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail@gmail.com
SMTP_PASS=your_app_password
HEAD_OF_DEPT_EMAIL=head@hospital.com
SENIOR_EMAIL=senior@hospital.com

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SLACK_PATIENT_WEBHOOK=https://hooks.slack.com/...

# Hospital
HOSPITAL_NAME=City General Hospital
APPROVAL_SERVER_URL=http://localhost:5000
REMINDER_WAIT_SECONDS=300
ESCALATION_WAIT_SECONDS=600
```

## Running ShadowGate

Open 3 terminals:

**Terminal 1 - Approval Server:**
```
python notifications/approval_server.py
```

**Terminal 2 - Patient Intake API:**
```
python api/patient_intake.py
```

**Terminal 3 - Main Pipeline:**
```
python main.py
```

Then open `dashboard/index.html` in your browser.

## Dashboard

The dashboard has 4 tabs:

- **Dashboard** - Live scores, patient queue, unknown risks, approval status
- **Patient Intake** - Submit new patients with form validation
- **Results** - Patient journey timeline from admission to discharge
- **Discharge** - Doctor submits discharge criteria for CARA validation

## Alert Flow

```
Unknown risk found, priority P1 or P2
      |
      v
Confidential HTML email to Head of Department
(4 buttons: Approve Best/Moderate/Worst + Request Meeting)
      |
      v
No response after 5 mins -> Reminder (email + Slack to technical channel)
No response after 10 mins -> Escalation with CC to Senior (email + Slack to technical channel)
      |
      v
Head approves -> Slack to doctor (healthcare channel), all other buttons disabled
P3/P4 patients -> Slack directly to doctor (no approval needed)
```

## Discharge Validation

When treatment is complete, the doctor submits a discharge form. CARA checks every criterion (vitals, pain scale, medications, follow-up, discharge summary, patient education). If the pain scale is still above threshold or any criterion is unmet, discharge is blocked. If everything meets the criteria, discharge is approved and confirmed via Slack.

## Sample Patients

| Patient | Age | Condition | Priority | Doctor |
|---|---|---|---|---|
| Arthur Collins | 78 | Chest pain, on Warfarin | P1 | Dr. James Wilson (20yr, Senior) |
| Sarah Johnson | 32 | Fever, sore throat | P3 | Dr. Aisha Patel (4yr, Junior) |
| Baby Emma Wilson | 2 | High fever, rash | P2 | Dr. Priya Mehta (10yr, Senior) |
| James Murphy | 35 | Minor ankle sprain | P4 | Dr. Aisha Patel (4yr, Junior) |

## UiPath Integration

- **Platform:** UiPath Automation Cloud (staging)
- **Agent Type:** Coded Agent
- **Entrypoint:** `main.py` (`main(input: ShadowGateInput) -> ShadowGateOutput`)
- **AI:** Groq (Llama 3.3 70B), with Claude via UiPath AI Fabric integration in progress

Note: the full pipeline runs and has been verified end-to-end via direct local execution (`python main.py` and direct invocation of the entrypoint function). The UiPath serverless Debug environment currently returns a `PrepareEnvironmentError` during package installation, a known limitation of the Coded Agent (Preview) feature that we are continuing to work through with UiPath.

