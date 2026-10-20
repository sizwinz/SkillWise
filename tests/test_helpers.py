import unittest
from datetime import timedelta
from utils.helpers import (
    clean_task_text,
    generate_task_key,
    is_task_line,
    parse_duration,
    extract_roadmap_tasks
)

class TestHelpers(unittest.TestCase):
    def test_clean_task_text(self):
        self.assertEqual(clean_task_text("- Master Python basics (2 weeks)"), "Master Python basics")
        self.assertEqual(clean_task_text("* [ ] Complete SQL indexing project (3 days)"), "Complete SQL indexing project")
        self.assertEqual(clean_task_text("1. Build Docker containers"), "Build Docker containers")
        self.assertEqual(clean_task_text("2) Deploy to Kubernetes (Weeks 1-4)"), "Deploy to Kubernetes")
        self.assertEqual(clean_task_text("**Learn PyTorch**"), "Learn PyTorch")
        self.assertEqual(clean_task_text("- Task with brackets [1-2 weeks]"), "Task with brackets")

    def test_is_module_header(self):
        from utils.helpers import is_module_header
        self.assertTrue(is_module_header("### Module 1.1: Foundations"))
        self.assertTrue(is_module_header("**Module 1: Architecture**"))
        self.assertFalse(is_module_header("**- Task inside bold markers (2 weeks)**"))
        self.assertFalse(is_module_header("## Phase 1: Core Systems"))
        self.assertFalse(is_module_header("- Standard task"))

    def test_is_task_line(self):
        self.assertTrue(is_task_line("- Build REST API"))
        self.assertTrue(is_task_line("* Implement JWT authentication"))
        self.assertTrue(is_task_line("+ Setup CI/CD pipeline"))
        self.assertTrue(is_task_line("1. Study database internals"))
        self.assertTrue(is_task_line("2) Learn Terraform"))
        self.assertFalse(is_task_line("---"))
        self.assertFalse(is_task_line("## Phase 1"))
        self.assertFalse(is_task_line(""))

    def test_parse_duration(self):
        self.assertEqual(parse_duration("(2 weeks)"), timedelta(weeks=2))
        self.assertEqual(parse_duration("(5 days)"), timedelta(days=5))
        self.assertEqual(parse_duration("(Weeks 1-4)"), timedelta(weeks=4))
        self.assertEqual(parse_duration(""), timedelta(weeks=1))

    def test_extract_roadmap_tasks(self):
        roadmap = """
## Phase 1: Core Systems (Weeks 1-4)
### Module 1.1: Concurrency
- Master Python asyncio (1 week)
- [ ] Understand threading and GIL (3 days)

### Module 1.2: Networking
1. HTTP/2 and gRPC fundamentals
2. WebSockets implementation

## Phase 2: Distributed Data (Weeks 5-8)
**Module 2.1: Storage Engines**
* LSM-tree vs B-Tree architectures (2 weeks)
+ Sharding and replication strategies
"""
        tasks = extract_roadmap_tasks(roadmap)
        self.assertGreaterEqual(len(tasks), 6)
        self.assertTrue(any("Master Python asyncio" in t for t in tasks))
        self.assertTrue(any("HTTP/2 and gRPC" in t for t in tasks))
        self.assertTrue(any("LSM-tree vs B-Tree" in t for t in tasks))

if __name__ == "__main__":
    unittest.main()
