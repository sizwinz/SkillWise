# roadmap_generator.py
import os
import time
from typing import Optional
from llm_helper import generate_llm_content


class RoadmapGenerationError(Exception):
    """Custom exception for roadmap generation errors."""
    pass


def validate_prompt(prompt: str) -> bool:
    """Validate the prompt for roadmap generation."""
    if not prompt or not isinstance(prompt, str):
        return False
    clean = prompt.strip()
    if len(clean) < 30:
        return False
    if len(clean) > 200000:
        return False
    return True


def generate_roadmap(
    prompt: str,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_retries: int = 3,
) -> str:
    """
    Generate a learning roadmap using the selected AI model with smart retry backoff.
    Fails fast on authentication/configuration ValueErrors instead of blocking the UI.
    """
    if not validate_prompt(prompt):
        raise RoadmapGenerationError("Invalid prompt. Please provide a detailed prompt with at least 30 characters.")

    if not provider or not api_key or not model:
        try:
            import streamlit as st
            provider = provider or st.session_state.get("ai_provider", "Google Gemini")
            api_key = api_key or st.session_state.get("api_key") or os.getenv("GEMINI_API_KEY")
            model = model or st.session_state.get("selected_model", "")
        except Exception:
            provider = provider or "Google Gemini"
            api_key = api_key or os.getenv("GEMINI_API_KEY")
            model = model or ""

    if provider == "Ollama (Local)" and not api_key:
        api_key = "http://localhost:11434"

    if not api_key:
        raise RoadmapGenerationError(
            f"API key or Base URL for {provider} is not configured. Please configure it in the sidebar."
        )

    retry_count = 0
    last_error = None

    while retry_count < max_retries:
        try:
            response_text = generate_llm_content(provider, api_key, model, prompt)
            if not response_text or not response_text.strip():
                raise RoadmapGenerationError("Received empty response from the AI model.")
            return response_text.strip()
        except ValueError as ve:
            # Fail fast on non-retryable auth, invalid model, or safety errors
            raise RoadmapGenerationError(str(ve))
        except Exception as e:
            last_error = str(e)
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(1.5 ** retry_count)

    raise RoadmapGenerationError(
        f"Failed to generate roadmap after {max_retries} attempts. Last error: {last_error}."
    )
