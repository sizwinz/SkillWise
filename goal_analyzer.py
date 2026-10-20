# goal_analyzer.py
import os
from typing import Optional
from llm_helper import generate_llm_content

def analyze_goals(
    text: str,
    provider: str = "Google Gemini",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> str:
    """
    Analyze career goals using the selected AI provider and model.
    
    Args:
        text: Career goal description from the user.
        provider: AI Provider name.
        api_key: Optional API key or base URL.
        model: Optional model identifier.
        
    Returns:
        str: Extracted target skills, domain keywords, and actionable insights.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return "Please provide a valid career goal text."
        
    try:
        if not api_key:
            try:
                import streamlit as st
                api_key = st.session_state.get("api_key") or os.getenv("GEMINI_API_KEY")
            except Exception:
                api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            return f"{provider} API Key/URL not configured. Please enter it in the sidebar."
            
        prompt = (
            f"Analyze the following career goal and extract the primary skills, relevant technical domains, "
            f"industry tools, and key target keywords. Format cleanly with bullet points:\n\n{text.strip()}"
        )
        return generate_llm_content(provider, api_key, model, prompt)
    except Exception as e:
        return f"Error analyzing career goal: {str(e)}"
