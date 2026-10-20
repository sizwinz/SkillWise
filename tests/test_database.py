import unittest
import os
import tempfile
from utils.database import (
    roadmap_id,
    load_roadmaps_db,
    save_roadmaps_db,
    get_active_roadmap,
    set_active_roadmap,
    sync_progress_from_active_roadmap
)

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_roadmaps.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_roadmap_id_deterministic(self):
        id1 = roadmap_id("Python dev resume", "AI Engineer", "AI Engineer")
        id2 = roadmap_id("Python dev resume", "AI Engineer", "AI Engineer")
        id3 = roadmap_id("Different resume", "AI Engineer", "AI Engineer")
        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)
        self.assertEqual(len(id1), 16)

    def test_load_save_roadmaps_db(self):
        roadmaps = [
            {"id": "abc1", "role": "AI Engineer", "goal": "Lead AI", "active": True, "roadmap": "Phase 1"},
            {"id": "abc2", "role": "Backend", "goal": "Staff", "active": False, "roadmap": "Phase 2"}
        ]
        self.assertTrue(save_roadmaps_db(roadmaps, self.db_path))
        loaded = load_roadmaps_db(self.db_path)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["id"], "abc1")

    def test_get_and_set_active_roadmap(self):
        roadmaps = [
            {"id": "r1", "active": True},
            {"id": "r2", "active": False}
        ]
        self.assertEqual(get_active_roadmap(roadmaps)["id"], "r1")
        
        set_active_roadmap(roadmaps, "r2")
        self.assertFalse(roadmaps[0]["active"])
        self.assertTrue(roadmaps[1]["active"])
        self.assertEqual(get_active_roadmap(roadmaps)["id"], "r2")

    def test_sync_progress(self):
        roadmaps = [{
            "id": "r1",
            "active": True,
            "roadmap": "## Phase 1\n- Task 1\n- Task 2",
            "progress": {"Phase 1::Task 1": True}
        }]
        
        def mock_extract(text):
            return ["Phase 1::Task 1", "Phase 1::Task 2"]

        progress = sync_progress_from_active_roadmap(roadmaps, mock_extract)
        self.assertTrue(progress["Phase 1::Task 1"])
        self.assertFalse(progress["Phase 1::Task 2"])

if __name__ == "__main__":
    unittest.main()
