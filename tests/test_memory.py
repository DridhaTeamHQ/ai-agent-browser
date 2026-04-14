import tempfile
import unittest
from pathlib import Path
import shutil

from core.memory import AgentMemory


class AgentMemoryTests(unittest.TestCase):
    def setUp(self):
        self._old_db_path = AgentMemory.DB_PATH
        self._tmpdir = Path(tempfile.mkdtemp())
        AgentMemory.DB_PATH = self._tmpdir / "agent.db"
        self.memory = AgentMemory()

    def tearDown(self):
        AgentMemory.DB_PATH = self._old_db_path
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_success_dedupes_across_query_variants(self):
        self.memory.mark_success("https://example.com/news/story-123?utm_source=abc")
        self.assertTrue(self.memory.is_success("https://example.com/news/story-123"))
        self.assertTrue(self.memory.is_success("https://example.com/news/story-123?pfrom=home"))

    def test_recent_failure_dedupes_across_query_variants(self):
        self.memory.mark_failed("https://example.com/world/update-77?x=1", "image_missing")
        self.assertTrue(
            self.memory.is_recent_failure(
                "https://example.com/world/update-77?x=2",
                within_minutes=60,
            )
        )


if __name__ == "__main__":
    unittest.main()
