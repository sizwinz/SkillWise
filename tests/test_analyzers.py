import unittest
from roadmap_generator import validate_prompt, RoadmapGenerationError, generate_roadmap
from smart_gap_analyzer import get_smart_gap_analysis, SmartGapAnalysisError
from goal_analyzer import analyze_goals

class TestAnalyzers(unittest.TestCase):
    def test_validate_prompt(self):
        self.assertFalse(validate_prompt(""))
        self.assertFalse(validate_prompt("Too short"))
        self.assertTrue(validate_prompt("This is a detailed prompt that contains more than thirty characters for validation."))

    def test_roadmap_generation_error_on_empty_prompt(self):
        with self.assertRaises(RoadmapGenerationError):
            generate_roadmap("Short")

    def test_smart_gap_analysis_validation(self):
        with self.assertRaises(SmartGapAnalysisError):
            get_smart_gap_analysis("", "AI Engineer")
        with self.assertRaises(SmartGapAnalysisError):
            get_smart_gap_analysis("Resume with enough text content", "Select a tech role")

    def test_analyze_goals_validation(self):
        result = analyze_goals("")
        self.assertIn("Please provide a valid career goal text", result)

if __name__ == "__main__":
    unittest.main()
