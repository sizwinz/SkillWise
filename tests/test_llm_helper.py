import unittest
from llm_helper import is_reasoning_model, DEFAULT_MODELS, fetch_available_models

class TestLLMHelper(unittest.TestCase):
    def test_default_models_coverage(self):
        self.assertIn("Google Gemini", DEFAULT_MODELS)
        self.assertIn("OpenAI (ChatGPT)", DEFAULT_MODELS)
        self.assertIn("Anthropic (Claude)", DEFAULT_MODELS)
        self.assertIn("Groq", DEFAULT_MODELS)
        self.assertIn("xAI (Grok)", DEFAULT_MODELS)

        gemini_models = DEFAULT_MODELS["Google Gemini"]
        self.assertIn("gemini-3.8-flash", gemini_models)
        self.assertIn("gemini-4-argon", gemini_models)

        openai_models = DEFAULT_MODELS["OpenAI (ChatGPT)"]
        self.assertIn("gpt-6-astra", openai_models)
        self.assertIn("gpt-6.1-sol", openai_models)

        claude_models = DEFAULT_MODELS["Anthropic (Claude)"]
        self.assertIn("claude-opus-5-5", claude_models)

    def test_strip_reasoning_thoughts(self):
        from llm_helper import strip_reasoning_thoughts
        raw = "<think>Let me ponder about the learning path.\n- Step 1\n- Step 2</think>Here is the roadmap:\n## Phase 1"
        cleaned = strip_reasoning_thoughts(raw)
        self.assertEqual(cleaned, "Here is the roadmap:\n## Phase 1")
        self.assertNotIn("<think>", cleaned)

    def test_is_reasoning_model(self):
        self.assertTrue(is_reasoning_model("gpt-6-astra"))
        self.assertTrue(is_reasoning_model("gpt-6.1-sol"))
        self.assertTrue(is_reasoning_model("o1"))
        self.assertTrue(is_reasoning_model("o3-mini"))
        self.assertTrue(is_reasoning_model("deepseek-r1"))
        self.assertTrue(is_reasoning_model("grok-4.20-reasoning"))
        
        self.assertFalse(is_reasoning_model("gpt-4o"))
        self.assertFalse(is_reasoning_model("claude-3-5-haiku-latest"))
        self.assertFalse(is_reasoning_model("llama-3.1-8b-instant"))

    def test_fetch_available_models_fallback(self):
        # Empty or invalid key should fall back to DEFAULT_MODELS without crashing
        models = fetch_available_models("Google Gemini", "")
        self.assertEqual(models, DEFAULT_MODELS["Google Gemini"])

        models_openai = fetch_available_models("OpenAI (ChatGPT)", "")
        self.assertEqual(models_openai, DEFAULT_MODELS["OpenAI (ChatGPT)"])

if __name__ == "__main__":
    unittest.main()
