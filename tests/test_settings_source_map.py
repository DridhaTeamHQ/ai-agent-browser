import unittest

from config.settings import DEFAULT_CATEGORY_SOURCES


class SettingsSourceMapTests(unittest.TestCase):
    def test_business_sources_include_reuters(self):
        names = [row["name"] for row in DEFAULT_CATEGORY_SOURCES["business"]]
        self.assertEqual(names, ["Reuters", "TOI", "India Today", "BBC"])

    def test_tech_sources_include_reuters(self):
        names = [row["name"] for row in DEFAULT_CATEGORY_SOURCES["tech"]]
        self.assertEqual(names, ["Reuters", "TOI", "India Today", "BBC"])


    def test_international_stack_keeps_ndtv_and_adds_reuters(self):
        names = [row["name"] for row in DEFAULT_CATEGORY_SOURCES["international"]]
        self.assertIn("NDTV", names)
        self.assertIn("Reuters", names)
    def test_environment_sources_use_working_stack(self):
        names = [row["name"] for row in DEFAULT_CATEGORY_SOURCES["environment"]]
        self.assertEqual(names, ["India Today", "TOI", "AlJazeera"])

    def test_national_sources_include_the_hindu(self):
        names = [row["name"] for row in DEFAULT_CATEGORY_SOURCES["national"]]
        self.assertIn("The Hindu", names)


if __name__ == "__main__":
    unittest.main()


