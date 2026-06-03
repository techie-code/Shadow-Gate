# ShadowGate 🌑
> *Test everything. Touch nothing. Ship with confidence.*

**UiPath AgentHack 2026 — Track 3: UiPath Test Cloud**

---

## What is ShadowGate?

ShadowGate is an AI-powered digital twin testing platform for enterprise automations. It creates a simulated shadow of your production environment and runs your automations through thousands of scenarios — including deliberate chaos — before a single line of code touches production.

No manual test writing. No environment setup. No production surprises.

---

## The Problem

Testing UiPath automations today is:
- **Slow** — engineers spend hours writing test cases manually
- **Fragile** — tests break every time the automation changes
- **Blind** — nobody knows which tests matter most before a release
- **Late** — critical failures are discovered after hitting production

---

## The Solution

ShadowGate's 10 AI agents work together to:

| Agent | Job |
|---|---|
| **Environment Simulator** | Generates a simulated production environment from plain English |
| **Chaos Agent** | Injects realistic failures (timeouts, nulls, schema changes) |
| **Behaviour Learning** | Learns real production patterns to improve simulations |
| **Coverage Intelligence** | Finds untested paths and generates missing scenarios |
| **Release Guardian** | Gives a 0-100 confidence score + recommends specific fixes |
| **Test Health Agent** | Flags fragile and outdated tests before release |
| **Change Watcher** | Detects automation changes and triggers relevant tests |
| **AI Behavior Validator** | Validates AI agent outputs for consistency |
| **Deployment Readiness** | Final GREEN/RED deployment signal |
| **Governance Logger** | Full audit trail of every agent decision |

---

## Tech Stack

- **AI / LLM:** Claude API (claude-sonnet-4-20250514) via Claude Code
- **Agent Orchestration:** LangChain
- **UiPath Platform:** Agent Builder + Maestro + Test Cloud
- **Mock Automations:** Python + Pandas + SQLite
- **Dashboard:** HTML + CSS + JavaScript
- **Notifications:** Slack Webhook

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/shadowgate.git
cd shadowgate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and fill environment variables
cp .env.example .env

# 4. Run normally
python main.py

# 5. Run with chaos injection
python main.py --chaos

# 6. Run specific automation
python main.py --automation loan
```

---

## Project Structure

```
shadowgate/
├── mock_automations/        # 3 banking automations being tested
│   ├── loan_processing/
│   ├── fraud_detection/
│   └── account_onboarding/
├── agents/                  # 10 ShadowGate AI agents
├── langchain/               # LangChain orchestration layer
├── uipath/                  # UiPath configuration
├── governance/              # Audit log + governance dashboard
├── dashboard/               # Multi-automation dashboard
├── notifications/           # Slack integration
├── tests/                   # Generated test cases
├── database.py              # SQLite database setup
├── data_generator.py        # Mock data generation
└── main.py                  # Entry point
```

---

## The 3 Mock Automations

| Automation | What it does |
|---|---|
| **Loan Processing** | Validates applications, checks credit scores, makes approval decisions |
| **Fraud Detection** | Monitors transactions, flags suspicious activity, escalates confirmed fraud |
| **Account Onboarding** | Validates KYC, provisions bank accounts, manages compliance checks |

---

## Built With Claude Code

ShadowGate was built using Claude Code — the same coding agent that powers ShadowGate's intelligence. This is intentional: we used the tools we're governing.

---

## License

MIT License — see LICENSE file.

---

*Built for UiPath AgentHack 2026*
