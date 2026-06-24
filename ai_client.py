"""
ShadowGate - AI Client
Central connection to Groq API (free tier).
All agents use this client to make AI calls.
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

# ─────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────

def get_llm(temperature=0.2):
    """
    Get a configured Groq LLM instance.
    Uses llama-3.3-70b-versatile — free, fast, high quality.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")

    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=api_key,
        temperature=temperature,
    )


def ask_ai(system_prompt, user_prompt, temperature=0.2):
    """
    Simple wrapper to ask Groq a question.
    Returns the response as a string.
    """
    llm = get_llm(temperature=temperature)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    response = llm.invoke(messages)
    return response.content


def test_connection():
    """Test that Groq API is working."""
    try:
        response = ask_ai(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'ShadowGate AI connection successful' and nothing else."
        )
        print(f"✅ Groq API connected: {response}")
        return True
    except Exception as e:
        print(f"❌ Groq API connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
