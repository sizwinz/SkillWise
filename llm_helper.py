# llm_helper.py
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import re
import time
from typing import List, Dict, Tuple
import requests
import google.generativeai as genai

DEFAULT_MODELS: Dict[str, List[str]] = {
    "Google Gemini": [
        "gemini-3.8-flash",
        "gemini-4-argon",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ],
    "OpenAI (ChatGPT)": [
        "gpt-6-astra",
        "gpt-6.1-sol",
        "gpt-6-luna",
        "gpt-5.4",
        "gpt-5.4-mini",
        "o3",
        "o4-mini",
        "o3-mini",
        "o1",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4o-mini",
    ],
    "Anthropic (Claude)": [
        "claude-opus-5-5",
        "claude-sonnet-5-5",
        "claude-haiku-5-5",
        "claude-sonnet-4-5",
        "claude-opus-4-5",
        "claude-haiku-4-5",
        "claude-3-7-sonnet-latest",
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
    ],
    "Groq": [
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "deepseek-r1-distill-llama-70b",
    ],
    "Ollama (Local)": [
        "qwen3",
        "gemma3",
        "llama3.3",
        "llama3.2",
        "llama3.1",
        "deepseek-r1",
        "qwen2.5",
        "mistral",
    ],
    "OpenRouter": [
        "google/gemini-3.8-flash",
        "anthropic/claude-opus-5-5",
        "anthropic/claude-sonnet-5-5",
        "openai/gpt-6-astra",
        "qwen/qwen3.8-27b",
        "deepseek/deepseek-r1",
        "meta-llama/llama-3.3-70b-instruct",
    ],
    "xAI (Grok)": [
        "grok-4.7",
        "grok-4.3",
        "grok-4.20-reasoning",
        "grok-4",
        "grok-3",
        "grok-3-mini",
    ],
    "Mistral": [
        "mistral-large-latest",
        "magistral-medium-latest",
        "codestral-latest",
        "mistral-medium-latest",
        "mistral-small-latest",
        "pixtral-large-latest",
    ],
}

# TTL Cache for live model discovery: {(provider, key_hash): (timestamp, models_list)}
_MODEL_CACHE: Dict[Tuple[str, str], Tuple[float, List[str]]] = {}
_CACHE_TTL_SECONDS = 600.0


def is_reasoning_model(model_name: str) -> bool:
    """Check if the model uses modern reasoning tokens and requires max_completion_tokens."""
    if not model_name:
        return False
    lower = model_name.lower()
    return any(
        prefix in lower
        for prefix in ["gpt-6", "gpt-5", "o1", "o3", "o4", "reasoning", "r1", "qwq", "magistral"]
    )


def strip_reasoning_thoughts(text: str) -> str:
    """Remove internal <think>...</think> chains emitted by reasoning models."""
    if not text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Also handle unclosed <think> tags if output was truncated
    if "<think>" in cleaned.lower() and "</think>" not in cleaned.lower():
        cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def fetch_available_models(provider: str, api_key_or_url: str) -> List[str]:
    """Fetch live available models from provider API with TTL caching and fallback to verified defaults."""
    defaults = list(DEFAULT_MODELS.get(provider, []))
    if not api_key_or_url or not api_key_or_url.strip():
        return defaults

    clean_key = api_key_or_url.strip()
    cache_key = (provider, str(hash(clean_key)))
    now = time.time()

    if cache_key in _MODEL_CACHE:
        cached_time, cached_models = _MODEL_CACHE[cache_key]
        if now - cached_time < _CACHE_TTL_SECONDS and cached_models:
            return cached_models

    try:
        if provider == "Google Gemini":
            genai.configure(api_key=clean_key)
            models = []
            for m in genai.list_models():
                methods = getattr(m, "supported_generation_methods", [])
                if "generateContent" in methods:
                    name = m.name.replace("models/", "")
                    models.append(name)
            combined = [d for d in defaults if d in models] + [m for m in models if m not in defaults]
            result = combined if combined else defaults

        elif provider == "Anthropic (Claude)":
            headers = {
                "x-api-key": clean_key,
                "anthropic-version": "2023-06-01",
            }
            r = requests.get("https://api.anthropic.com/v1/models", headers=headers, timeout=6)
            if r.status_code == 200:
                data = r.json()
                models = [m["id"] for m in data.get("data", []) if "id" in m]
                combined = [d for d in defaults if d in models] + [m for m in models if m not in defaults]
                result = combined if combined else defaults
            else:
                result = defaults

        elif provider == "Ollama (Local)":
            base = clean_key.rstrip("/")
            result = defaults
            try:
                r = requests.get(f"{base}/api/tags", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    models = [m["name"] for m in data.get("models", []) if "name" in m]
                    if models:
                        result = models
            except Exception:
                try:
                    r2 = requests.get(f"{base}/v1/models", timeout=3)
                    if r2.status_code == 200:
                        data = r2.json()
                        models = [m["id"] for m in data.get("data", []) if "id" in m]
                        if models:
                            result = models
                except Exception:
                    pass

        else:
            url_map = {
                "OpenAI (ChatGPT)": "https://api.openai.com/v1/models",
                "Groq": "https://api.groq.com/openai/v1/models",
                "OpenRouter": "https://openrouter.ai/api/v1/models",
                "xAI (Grok)": "https://api.x.ai/v1/models",
                "Mistral": "https://api.mistral.ai/v1/models",
            }
            url = url_map.get(provider)
            if not url:
                return defaults

            headers = {"Authorization": f"Bearer {clean_key}"}
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code == 200:
                data = r.json()
                models = [m["id"] for m in data.get("data", []) if "id" in m]
                if provider == "OpenAI (ChatGPT)":
                    models = [m for m in models if any(k in m for k in ["gpt", "o1", "o3", "o4"])]
                combined = [d for d in defaults if d in models] + [m for m in models if m not in defaults]
                result = combined if combined else defaults
            else:
                result = defaults

        _MODEL_CACHE[cache_key] = (now, result)
        return result

    except Exception:
        return defaults


def generate_llm_content(
    provider: str,
    api_key_or_url: str,
    model: str,
    prompt: str,
    max_tokens: int = None,
) -> str:
    """Generate content across supported AI providers with resilient error handling and parameter routing."""
    if provider == "Ollama (Local)" and (not api_key_or_url or not api_key_or_url.strip()):
        api_key_or_url = "http://localhost:11434"

    if not api_key_or_url or not api_key_or_url.strip():
        raise ValueError(f"API key or Base URL is required to query {provider}.")

    api_key_or_url = api_key_or_url.strip()

    if not model or not model.strip():
        model = DEFAULT_MODELS.get(provider, [""])[0]
    model = model.strip()

    if provider == "Google Gemini":
        genai.configure(api_key=api_key_or_url)
        model_name = model if model.startswith("models/") else f"models/{model}"
        try:
            model_obj = genai.GenerativeModel(model_name)
            gen_config = {"max_output_tokens": max_tokens} if max_tokens else None
            response = (
                model_obj.generate_content(prompt, generation_config=gen_config)
                if gen_config
                else model_obj.generate_content(prompt)
            )
        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg or "API_KEY_INVALID" in err_msg or "401" in err_msg:
                raise ValueError("Google Gemini API Key is invalid or unauthorized. Please check your credentials.")
            if "404" in err_msg or "not found" in err_msg.lower():
                raise ValueError(f"Gemini model '{model}' is unavailable or deprecated. Please select another model.")
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                raise RuntimeError("Google Gemini rate limit or quota exceeded. Please try again in a few moments.")
            raise RuntimeError(f"Gemini API request failed: {err_msg}")

        if not response:
            raise RuntimeError("Received empty response from Gemini.")

        if getattr(response, "candidates", None):
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason and str(finish_reason).upper() in ["2", "SAFETY"]:
                raise ValueError("Gemini candidate blocked by content safety filters.")

            if getattr(candidate, "content", None) and getattr(candidate.content, "parts", None):
                parts_text = "".join(
                    part.text for part in candidate.content.parts if hasattr(part, "text") and part.text
                )
                if parts_text.strip():
                    return strip_reasoning_thoughts(parts_text)

        try:
            if response.text:
                return strip_reasoning_thoughts(response.text)
        except Exception as e:
            raise RuntimeError(f"Could not extract text from Gemini response: {str(e)}")

        raise RuntimeError("Received empty text content from Gemini.")

    elif provider == "Anthropic (Claude)":
        headers = {
            "x-api-key": api_key_or_url,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens or 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", json=body, headers=headers, timeout=90)
        except requests.exceptions.Timeout:
            raise TimeoutError("Anthropic API request timed out after 90 seconds.")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Anthropic API: {str(e)}")

        if r.status_code in (401, 403):
            raise ValueError("Anthropic API key is invalid or unauthorized.")
        elif r.status_code == 404:
            raise ValueError(f"Anthropic model '{model}' not found. Please select an updated Claude model.")
        elif r.status_code == 429:
            raise RuntimeError("Anthropic rate limit reached. Please wait a moment before retrying.")
        elif r.status_code != 200:
            raise RuntimeError(f"Anthropic API Error {r.status_code}: {r.text}")

        data = r.json()
        content_items = data.get("content", [])
        text_parts = [item.get("text", "") for item in content_items if item.get("type") == "text"]
        result = strip_reasoning_thoughts("".join(text_parts))
        if not result:
            raise RuntimeError("Anthropic returned an empty text response.")
        return result

    else:
        headers = {"Content-Type": "application/json"}
        if provider == "OpenRouter":
            headers["Authorization"] = f"Bearer {api_key_or_url}"
            headers["HTTP-Referer"] = "https://skillwise-sahaj33.streamlit.app"
            headers["X-Title"] = "SkillWise"
        elif provider != "Ollama (Local)":
            headers["Authorization"] = f"Bearer {api_key_or_url}"

        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if is_reasoning_model(model):
            if max_tokens:
                body["max_completion_tokens"] = max_tokens
        else:
            if max_tokens:
                body["max_tokens"] = max_tokens

        url_map = {
            "OpenAI (ChatGPT)": "https://api.openai.com/v1/chat/completions",
            "Groq": "https://api.groq.com/openai/v1/chat/completions",
            "OpenRouter": "https://openrouter.ai/api/v1/chat/completions",
            "xAI (Grok)": "https://api.x.ai/v1/chat/completions",
            "Mistral": "https://api.mistral.ai/v1/chat/completions",
        }

        if provider == "Ollama (Local)":
            base = api_key_or_url.rstrip("/")
            url = f"{base}/v1/chat/completions" if not base.endswith("/v1") else f"{base}/chat/completions"
        else:
            url = url_map.get(provider)
            if not url:
                raise ValueError(f"Unknown provider: {provider}")

        try:
            r = requests.post(url, json=body, headers=headers, timeout=90)
        except requests.exceptions.Timeout:
            raise TimeoutError(f"{provider} request timed out after 90 seconds.")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to {provider}: {str(e)}")

        if r.status_code in (401, 403):
            raise ValueError(f"{provider} authentication failed. Please verify your API key.")
        elif r.status_code in (400, 404) and ("model" in r.text.lower() or "decommissioned" in r.text.lower()):
            raise ValueError(f"Model '{model}' on {provider} is deprecated or unavailable: {r.text}")
        elif r.status_code == 429:
            raise RuntimeError(f"{provider} rate limit reached or credits exhausted.")
        elif r.status_code != 200:
            raise RuntimeError(f"{provider} API Error {r.status_code}: {r.text}")

        res_data = r.json()
        choices = res_data.get("choices", [])
        if not choices:
            raise RuntimeError(f"No choices returned by {provider}.")

        content = choices[0].get("message", {}).get("content", "")
        cleaned = strip_reasoning_thoughts(content)
        if not cleaned:
            raise RuntimeError(f"{provider} returned empty message content.")
        return cleaned
