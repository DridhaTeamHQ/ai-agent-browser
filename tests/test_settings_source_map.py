import unittest

from config.settings import DEFAULT_CATEGORY_SOURCES


class SettingsSourceMapTests(unittest.TestCase):
    def test_business_sources_drop_dead_routes(self):
        names = [row["name"] for row in DEFAULT_CATEGORY_SOURCES["business"]]
        self.assertEqual(names, ["TOI", "India Today", "BBC"])

    def test_tech_sources_drop_dead_routes(self):
        names = [row["name"] for row in DEFAULT_CATEGORY_SOURCES["tech"]]
        self.assertEqual(names, ["TOI", "India Today", "BBC"])


    def test_international_stack_keeps_ndtv_but_not_reuters(self):
        names = [row["name"] for row in DEFAULT_CATEGORY_SOURCES["international"]]
        self.assertIn("NDTV", names)
        self.assertNotIn("Reuters", names)
    def test_environment_sources_use_working_stack(self):
        names = [row["name"] for row in DEFAULT_CATEGORY_SOURCES["environment"]]
        self.assertEqual(names, ["India Today", "TOI", "AlJazeera"])


if __name__ == "__main__":
    unittest.main()


