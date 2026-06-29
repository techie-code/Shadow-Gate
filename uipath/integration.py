"""
ShadowGate - UiPath Integration
Connects our Python pipeline to UiPath Automation Cloud.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("UIPATH_CLIENT_ID")
CLIENT_SECRET = os.getenv("UIPATH_CLIENT_SECRET")
TENANT_NAME = os.getenv("UIPATH_TENANT_NAME", "hackathon26_171")
ACCOUNT_NAME = os.getenv("UIPATH_ACCOUNT_NAME", "hackathon26_171")
BASE_URL = f"https://staging.uipath.com/{TENANT_NAME}"


def get_access_token():
    """Get OAuth access token from UiPath."""
    url = f"https://staging.uipath.com/{TENANT_NAME}/identity_/connect/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "OR.Execution TM.Projects"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"   ✅ UiPath authentication successful")
            return token
        else:
            print(f"   ⚠️ Auth failed: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        print(f"   ⚠️ Auth error: {e}")
        return None


def call_shadowgate_agent(automation_name, pipeline_report, token):
    """Call the deployed ShadowGate agent on UiPath."""
    if not token:
        return None

    confidence = pipeline_report.get("confidence_score", 0)
    pass_rate = pipeline_report.get("pass_rate", 0)
    health = pipeline_report.get("health_score", 0)
    errors = pipeline_report.get("stages", {}).get("automation_run", {}).get("result", {}).get("errors", [])

    prompt = f"""Analyse the test results for {automation_name}:
Pass Rate: {pass_rate}%
Health Score: {health}/100
Confidence Score: {confidence}/100
Errors Found: {len(errors)}
Chaos Mode: {pipeline_report.get('chaos_mode', False)}

Provide:
1. A confidence score assessment
2. Top 3 issues found
3. Specific fix recommendations
4. Deployment signal: GREEN or RED"""

    url = f"{BASE_URL}/orchestrator_/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-UIPATH-TenantName": TENANT_NAME
    }
    payload = {
        "startInfo": {
            "ReleaseName": "ShadowGate",
            "Strategy": "All",
            "JobsCount": 1,
            "InputArguments": json.dumps({
                "automation_name": automation_name,
                "prompt": prompt
            })
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code in [200, 201]:
            print(f"   ✅ UiPath agent invoked for {automation_name}")
            return response.json()
        else:
            print(f"   ⚠️ Agent call failed: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"   ⚠️ Agent call error: {e}")
        return None


def run_uipath_integration(all_reports):
    """Main integration - called after Python pipeline completes."""
    print(f"\n🔗 UiPath Integration")
    print(f"🌐 Connecting to UiPath Automation Cloud...")

    if not CLIENT_ID or not CLIENT_SECRET:
        print(f"   ⚠️ UiPath credentials not configured in .env")
        return False

    token = get_access_token()
    if not token:
        print(f"   ⚠️ Could not authenticate with UiPath")
        return False

    results = {}
    for automation_name, report in all_reports.items():
        print(f"\n   📤 Sending {automation_name} results to UiPath...")
        result = call_shadowgate_agent(automation_name, report, token)
        results[automation_name] = result

    print(f"\n   ✅ UiPath integration complete!")
    print(f"   🌐 View at: {BASE_URL}/portal_/home")
    return True


def test_connection():
    """Test UiPath connection."""
    print(f"\n🔗 Testing UiPath Connection...")
    print(f"   Tenant: {TENANT_NAME}")
    print(f"   URL: {BASE_URL}")
    token = get_access_token()
    if token:
        print(f"   ✅ Connection successful!")
        return True
    else:
        print(f"   ❌ Connection failed - check credentials in .env")
        return False


if __name__ == "__main__":
    test_connection()
