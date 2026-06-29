# ShadowGate
### AI-Powered Hospital Automation Testing Platform

> **We test what you know. We discover what you don't.**

Built for **UiPath AgentHack 2026** - Track 3: UiPath Test Cloud

---

## What is ShadowGate?

ShadowGate is an AI-powered testing platform that validates hospital automation workflows before they go live. It tests four critical hospital automations across 8 stages, discovers unknown risks nobody thought to test, and keeps humans in the loop at every critical decision point.

---

## The Problem

Hospital automation systems are tested against known scenarios. But what about the risks nobody thought to write tests for?

A patient on Warfarin gets prescribed Clopidogrel. The automation approves it. Nobody wrote a test for that interaction. The patient bleeds.

**ShadowGate finds those risks before they reach patients.**

---

## The Four Automations

| Automation | Full Name | Role |
|------------|-----------|------|
| **ARIA** | Adaptive Risk Intelligence Analyser | Generates best/moderate/worst case scenarios. Discovers unknown risks using Claude AI. |
| **SAFE** | Smart Allergy and Formula Engine | Validates drug interactions, allergies and dosage limits across all scenarios. |
| **GUARDIAN** | General Unit Assignment and Resource Director | Assigns doctors by experience level and availability. Monitors professional conduct. |
| **CARA** | Continuous Aftercare and Recovery Advisor | Tracks recovery, validates discharge criteria, schedules follow-ups. |

---

## Key Features

### Unknown Unknown Detection
ARIA discovers risks nobody wrote tests for. In each run it finds risks like:
- Warfarin + Clopidogrel bleeding risk in elderly patients with kidney disease
- Azithromycin QT interval prolongation risk
- Vancomycin + Ceftriaxone renal toxicity in pediatric patients

### Experience-Based Doctor Assignment
- P1 Critical: Senior doctors only (20+ years experience)
- P2 Urgent: Senior or mid-level by specialty
- P3/P4: Junior doctors (learning opportunity)

### Human in the Loop
- Confidential HTML email to Head of Department with 4 approval buttons
- Automatic reminder after 5 minutes
- Escalation with CC to senior management after 10 minutes
- Slack to doctor ONLY after Head approves
- Double approval prevention

### ShadowGate Testing Pipeline (8 Stages)
1. Change Detection
2. Environment Simulation (AI-generated test scenarios)
3. Coverage Intelligence (finds gaps)
4. Chaos Injection (optional)
5. Automation Run
6. Validation
7. Test Health Scan
8. Release Guardian Analysis

### Results
- **95/100** confidence score
- **100%** pass rate across all 4 automations
- **GREEN** deployment signal
- **9 unknown risks** discovered per run

---

## Architecture

```
Patient Admitted
      |
      v
ARIA (Claude AI via UiPath)
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
  Email to Head of Department
  Slack to doctor after approval
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Orchestration | UiPath Automation Cloud |
| Agent Type | Coded Agent |
| AI Engine | Claude claude-sonnet-4-5 via UiPath AI Fabric |
| Fallback AI | Groq Llama 3.3 70B |
| Backend | Python 3.11 |
| Database | SQLite |
| Notifications | Gmail SMTP + Slack Webhooks |
| Dashboard | HTML/CSS/JavaScript |
| API | Flask |

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/shadowgate.git
cd shadowgate
```

### 2. Create virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
Create a `.env` file:
```env
# AI (Claude via UiPath - primary)
UIPATH_CLIENT_ID=your_client_id
UIPATH_CLIENT_SECRET=your_client_secret
UIPATH_TENANT_NAME=your_tenant
UIPATH_ACCOUNT_NAME=your_account

# AI Fallback
GROQ_API_KEY=your_groq_key

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

---

## Running ShadowGate

Open 3 terminals:

**Terminal 1 - Approval Server:**
```bash
python notifications/approval_server.py
```

**Terminal 2 - Patient Intake API:**
```bash
python api/patient_intake.py
```

**Terminal 3 - Main Pipeline:**
```bash
python main.py
```

Then open `dashboard/index.html` in your browser.

---

## Dashboard

The dashboard has 4 tabs:

- **Dashboard** - Live scores, patient queue, unknown risks, approval status
- **Patient Intake** - Submit new patients with form validation
- **Results** - Patient journey timeline from admission to discharge
- **Discharge** - Doctor submits discharge criteria for CARA validation

---

## Alert Flow

```
Unknown risk found
      |
      v
Confidential HTML email to Head of Department
(4 buttons: Approve Best/Moderate/Worst + Request Meeting)
      |
      v
No response after 5 mins -> Reminder email
No response after 10 mins -> Escalation with CC to Senior
      |
      v
Head approves -> Slack to doctor
P3/P4 patients -> Slack directly (no approval needed)
```

---

## Sample Patients

| Patient | Age | Condition | Priority | Doctor |
|---------|-----|-----------|----------|--------|
| Arthur Collins | 78 | Chest pain | P1 | Dr. James Wilson (20yr) |
| Sarah Johnson | 32 | Fever | P2 | Dr. Priya Mehta (10yr) |
| Baby Emma Wilson | 2 | High fever | P2 | Dr. Priya Mehta (10yr) |
| James Murphy | 35 | Ankle sprain | P4 | Dr. Aisha Patel (4yr) |

---

## UiPath Integration

- **Platform**: UiPath Automation Cloud (staging)
- **Agent Type**: Coded Agent
- **Entrypoint**: `run_all_automations`
- **AI**: Claude via UiPath AI Fabric

---

## License

MIT License

---

*ShadowGate - UiPath AgentHack 2026*
