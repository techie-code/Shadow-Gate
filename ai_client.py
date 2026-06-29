"""
ShadowGate - AI Client
Uses Claude via UiPath AI fabric.
Falls back to Groq if UiPath not available.

UiPath provides Claude claude-sonnet-4-5 through their AI platform.
This is the primary AI for unknown risk discovery and test generation.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# UiPath AI fabric settings
UIPATH_BASE_URL = f"https://staging.uipath.com/{os.getenv('UIPATH_TENANT_NAME', 'hackathon26_171')}"
UIPATH_CLIENT_ID = os.getenv("UIPATH_CLIENT_ID", "")
UIPATH_CLIENT_SECRET = os.getenv("UIPATH_CLIENT_SECRET", "")

# Groq fallback
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

_uipath_token = None


def get_uipath_token():
    """Get OAuth token from UiPath."""
    global _uipath_token
    if _uipath_token:
        return _uipath_token

    if not UIPATH_CLIENT_ID or not UIPATH_CLIENT_SECRET:
        return None

    try:
        url = f"https://staging.uipath.com/{os.getenv('UIPATH_TENANT_NAME', 'hackathon26_171')}/identity_/connect/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": UIPATH_CLIENT_ID,
            "client_secret": UIPATH_CLIENT_SECRET,
            "scope": "OR.Execution"
        }
        response = requests.post(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        if response.status_code == 200:
            _uipath_token = response.json().get("access_token")
            return _uipath_token
    except Exception:
        pass
    return None


def ask_claude_via_uipath(system_prompt, user_prompt):
    """
    Call Claude claude-sonnet-4-5 via UiPath AI fabric.
    UiPath provides Claude as part of their platform.
    """
    token = get_uipath_token()
    if not token:
        return None

    try:
        url = f"{UIPATH_BASE_URL}/llmgateway_/api/claude/chat"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "claude-sonnet-4-5",
            "messages": [
                {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
            ],
            "max_tokens": 2000
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", [{}])
            if isinstance(content, list) and len(content) > 0:
                return content[0].get("text", "")
            return data.get("completion", "")
    except Exception:
        pass
    return None


def ask_groq(system_prompt, user_prompt):
    """Call Groq Llama 3.3 as fallback."""
    if not GROQ_API_KEY:
        return None

    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=GROQ_API_KEY,
            temperature=0.2
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        return response.content
    except Exception:
        pass
    return None


def ask_ai(system_prompt, user_prompt, temperature=0.2):
    """
    Main AI call function.
    Priority:
    1. Claude via UiPath AI fabric (primary)
    2. Groq Llama 3.3 (fallback)
    """
    # Try Claude via UiPath first
    result = ask_claude_via_uipath(system_prompt, user_prompt)
    if result:
        return result

    # Fall back to Groq
    result = ask_groq(system_prompt, user_prompt)
    if result:
        return result

    raise ValueError("No AI provider available. Check UIPATH credentials or GROQ_API_KEY in .env")


def get_ai_provider():
    """Return which AI provider is being used."""
    token = get_uipath_token()
    if token:
        return "Claude claude-sonnet-4-5 via UiPath AI Fabric"
    elif GROQ_API_KEY:
        return "Groq Llama 3.3 70B (fallback)"
    return "No AI provider configured"


def test_connection():
    """Test AI connection."""
    try:
        provider = get_ai_provider()
        print(f"   AI Provider: {provider}")
        response = ask_ai(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'ShadowGate AI connection successful' and nothing else."
        )
        print(f"   Response: {response}")
        return True
    except Exception as e:
        print(f"   AI connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
