import unittest
from utils.pdf_exporter import sanitize_pdf_text, generate_pdf

class TestPdfExporter(unittest.TestCase):
    def test_sanitize_pdf_text(self):
        text = "Design — Phase 1 ‘Foundations’ “Advanced” • Task"
        sanitized = sanitize_pdf_text(text)
        self.assertNotIn("—", sanitized)
        self.assertIn("-", sanitized)
        self.assertIn("'Foundations'", sanitized)
        self.assertIn('"Advanced"', sanitized)

    def test_generate_pdf_produces_valid_bytes(self):
        roadmap = """
## Phase 1: Core Systems (Weeks 1-4)
### Module 1.1: Distributed Compute
- Build Raft consensus engine in Python (2 weeks)
- Implement state machine replication (2 weeks)

## Phase 2: Production Scale (Weeks 5-8)
### Module 2.1: Benchmarking & Profiling
- Run load tests with Locust (1 week)
- Profile memory allocations with tracemalloc (1 week)
"""
        job_fit = "Strong foundational alignment in distributed algorithms."
        smart_gap = "Gaps identified in GPU scheduling."
        role = "AI Infrastructure Engineer"

        pdf_bytes = generate_pdf(roadmap, job_fit, smart_gap, role)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        # Verify PDF magic bytes
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

if __name__ == "__main__":
    unittest.main()
