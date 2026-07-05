import os
from llm_helper import generate_llm_content

def analyze_goals(text, provider="Google Gemini", api_key=None, model=None):
    """Analyze career goals using selected AI provider and model."""
    if not text or not isinstance(text, str):
        return "⚠️ Please provide a valid career goal text."
    try:
        if not api_key:
            import streamlit as st
            api_key = st.session_state.get("api_key") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return f"⚠️ {provider} API Key/URL not set. Please enter it in the sidebar."
            
        prompt = (
            f"Analyze the following career goal and extract the main skills, roles, and relevant keywords. "
            f"Present the analysis in a clear, user-friendly way:\n\n{text}"
        )
        return generate_llm_content(provider, api_key, model, prompt)
    except Exception as e:
        return f"⚠️ Error analyzing goal with AI: {str(e)}"

