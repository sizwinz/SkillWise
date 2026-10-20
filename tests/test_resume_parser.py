import unittest
from resume_parser import parse_linkedin_json, is_valid_pdf

class TestResumeParser(unittest.TestCase):
    def test_is_valid_pdf_nonexistent(self):
        self.assertFalse(is_valid_pdf("nonexistent_file_path.pdf"))
        self.assertFalse(is_valid_pdf("test.txt"))

    def test_parse_linkedin_json_standard(self):
        sample_json = {
            "profile": {
                "firstName": "Alex",
                "lastName": "Rivera",
                "headline": "Staff AI Engineer",
                "summary": "Specializing in distributed model training and inference optimization."
            },
            "experience": [
                {
                    "title": "Senior ML Engineer",
                    "companyName": "Tech Corp",
                    "description": "Built low-latency model serving pipelines.",
                    "startDate": "2023",
                    "endDate": "2026"
                }
            ],
            "skills": [
                {"name": "Python"},
                {"name": "PyTorch"},
                {"name": "CUDA"}
            ]
        }
        text = parse_linkedin_json(sample_json)
        self.assertIn("Alex Rivera", text)
        self.assertIn("Staff AI Engineer", text)
        self.assertIn("Tech Corp", text)
        self.assertIn("PyTorch", text)

    def test_parse_linkedin_json_jsonresume_format(self):
        sample_json = {
            "basics": {
                "name": "Jordan Smith",
                "label": "Backend Developer",
                "summary": "Distributed systems specialist."
            },
            "work": [
                {
                    "position": "Software Engineer",
                    "name": "Cloud Systems",
                    "summary": "Designed event-driven microservices."
                }
            ],
            "skills": [
                {"name": "Go"},
                {"name": "Kubernetes"}
            ]
        }
        text = parse_linkedin_json(sample_json)
        self.assertIn("Jordan Smith", text)
        self.assertIn("Backend Developer", text)
        self.assertIn("Cloud Systems", text)
        self.assertIn("Kubernetes", text)

    def test_parse_linkedin_json_list_export(self):
        sample_list = [
            {"profile": {"firstName": "Sam", "lastName": "Lee"}},
            {"skills": [{"name": "Rust"}]}
        ]
        text = parse_linkedin_json(sample_list)
        self.assertIn("Sam Lee", text)
        self.assertIn("Rust", text)

if __name__ == "__main__":
    unittest.main()
