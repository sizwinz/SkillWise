import requests
import google.generativeai as genai
import os

DEFAULT_MODELS = {
    "Google Gemini": ["gemini-2.0-flash", "gemini-2.5-flash-lite"],
    "OpenAI (ChatGPT)": ["gpt-4o", "gpt-4o-mini", "o1-mini", "o1-preview"],
    "Anthropic (Claude)": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
    "Groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
    "Ollama (Local)": ["llama3", "mistral", "gemma2", "phi3"],
    "OpenRouter": ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.3-70b-instruct", "openai/gpt-4o-mini"],
    "xAI (Grok)": ["grok-beta"],
    "Mistral": ["mistral-large-latest", "open-mistral-nemo", "pixtral-large-latest", "codestral-latest"]
}

def fetch_available_models(provider, api_key_or_url):
    if not api_key_or_url:
        return DEFAULT_MODELS.get(provider, [])
        
    try:
        if provider == "Google Gemini":
            genai.configure(api_key=api_key_or_url)
            models = []
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods:
                    name = m.name.replace("models/", "")
                    models.append(name)
            return models if models else DEFAULT_MODELS[provider]
            
        elif provider == "Anthropic (Claude)":
            headers = {
                "x-api-key": api_key_or_url,
                "anthropic-version": "2023-06-01"
            }
            r = requests.get("https://api.anthropic.com/v1/models", headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                models = [m["id"] for m in data.get("data", [])]
                return models if models else DEFAULT_MODELS[provider]
            return DEFAULT_MODELS[provider]
            
        elif provider == "Ollama (Local)":
            base = api_key_or_url.rstrip("/")
            r = requests.get(f"{base}/api/tags", timeout=3)
            if r.status_code == 200:
                data = r.json()
                models = [m["name"] for m in data.get("models", [])]
                return models if models else DEFAULT_MODELS[provider]
            r2 = requests.get(f"{base}/v1/models", timeout=3)
            if r2.status_code == 200:
                data = r2.json()
                models = [m["id"] for m in data.get("data", [])]
                return models if models else DEFAULT_MODELS[provider]
            return DEFAULT_MODELS[provider]
            
        else:
            url_map = {
                "OpenAI (ChatGPT)": "https://api.openai.com/v1/models",
                "Groq": "https://api.groq.com/openai/v1/models",
                "OpenRouter": "https://openrouter.ai/api/v1/models",
                "xAI (Grok)": "https://api.x.ai/v1/models",
                "Mistral": "https://api.mistral.ai/v1/models"
            }
            url = url_map.get(provider)
            if not url:
                return DEFAULT_MODELS.get(provider, [])
                
            headers = {"Authorization": f"Bearer {api_key_or_url}"}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                models = [m["id"] for m in data.get("data", [])]
                if provider == "OpenAI (ChatGPT)":
                    models = [m for m in models if "gpt" in m or "o1" in m]
                return models if models else DEFAULT_MODELS[provider]
            return DEFAULT_MODELS[provider]
            
    except Exception:
        return DEFAULT_MODELS.get(provider, [])

def generate_llm_content(provider, api_key_or_url, model, prompt, max_tokens=None):
    if not api_key_or_url:
        raise Exception(f"API key or Base URL is required to query {provider}.")
        
    if not model:
        model = DEFAULT_MODELS.get(provider, [""])[0]

    if provider == "Google Gemini":
        genai.configure(api_key=api_key_or_url)
        model_name = model if model.startswith("models/") else f"models/{model}"
        model_obj = genai.GenerativeModel(model_name)
        response = model_obj.generate_content(prompt)
        if not response or not response.text:
            raise Exception("Received empty response from Gemini.")
        return response.text.strip()
        
    elif provider == "Anthropic (Claude)":
        headers = {
            "x-api-key": api_key_or_url,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        body = {
            "model": model,
            "max_tokens": max_tokens or 4000,
            "messages": [{"role": "user", "content": prompt}]
        }
        r = requests.post("https://api.anthropic.com/v1/messages", json=body, headers=headers, timeout=60)
        if r.status_code != 200:
            raise Exception(f"Anthropic API Error {r.status_code}: {r.text}")
        return r.json()["content"][0]["text"].strip()
        
    else:
        headers = {
            "Content-Type": "application/json"
        }
        if provider == "OpenRouter":
            headers["Authorization"] = f"Bearer {api_key_or_url}"
            headers["HTTP-Referer"] = "https://skillwise.ai"
            headers["X-Title"] = "SkillWise"
        elif provider != "Ollama (Local)":
            headers["Authorization"] = f"Bearer {api_key_or_url}"

        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        url_map = {
            "OpenAI (ChatGPT)": "https://api.openai.com/v1/chat/completions",
            "Groq": "https://api.groq.com/openai/v1/chat/completions",
            "OpenRouter": "https://openrouter.ai/api/v1/chat/completions",
            "xAI (Grok)": "https://api.x.ai/v1/chat/completions",
            "Mistral": "https://api.mistral.ai/v1/chat/completions"
        }
        
        if provider == "Ollama (Local)":
            base = api_key_or_url.rstrip("/")
            if not base.endswith("/v1"):
                url = f"{base}/v1/chat/completions"
            else:
                url = f"{base}/chat/completions"
        else:
            url = url_map.get(provider)
            if not url:
                raise Exception(f"Unknown provider: {provider}")

        r = requests.post(url, json=body, headers=headers, timeout=60)
        if r.status_code != 200:
            raise Exception(f"{provider} API Error {r.status_code}: {r.text}")
        return r.json()["choices"][0]["message"]["content"].strip()
