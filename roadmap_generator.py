# roadmap_generator.py
import os
import time
from typing import Optional
import streamlit as st
from llm_helper import generate_llm_content

class RoadmapGenerationError(Exception):
    """Custom exception for roadmap generation errors."""
    pass

def validate_prompt(prompt: str) -> bool:
    """Validate the prompt for roadmap generation."""
    if not prompt or not isinstance(prompt, str):
        return False
    if len(prompt) < 50:
        return False
    if len(prompt) > 100000:  # Allow long prompts (e.g. including full resumes)
        return False
    return True

def generate_roadmap(prompt: str, max_retries: int = 3) -> str:
    """
    Generate a learning roadmap using the selected AI model.
    
    Args:
        prompt (str): The prompt for roadmap generation
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        str: Generated roadmap text
        
    Raises:
        RoadmapGenerationError: If generation fails after retries
    """
    if not validate_prompt(prompt):
        raise RoadmapGenerationError("Invalid prompt. Please provide a detailed prompt between 50 and 4000 characters.")
    
    provider = st.session_state.get("ai_provider", "Google Gemini")
    api_key = st.session_state.get("api_key") or os.getenv("GEMINI_API_KEY")
    model = st.session_state.get("selected_model", "")
    
    if not api_key:
        raise RoadmapGenerationError(f"API key or Base URL for {provider} is not configured. Please set it in the sidebar.")
        
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            response_text = generate_llm_content(provider, api_key, model, prompt)
            if not response_text:
                raise RoadmapGenerationError("Empty response from model")
            return response_text
            
        except Exception as e:
            last_error = str(e)
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(2 ** retry_count)  # Exponential backoff
            continue
    
    raise RoadmapGenerationError(f"Failed to generate roadmap after {max_retries} attempts. Last error: {last_error}.")
