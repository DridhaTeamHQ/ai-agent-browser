import unittest

from core.intelligence.category import CategoryDecider


class CategoryDeciderTests(unittest.TestCase):
    def setUp(self):
        self.decider = CategoryDecider()
        # Keep tests deterministic even when API key exists in environment.
        self.decider.client = None

    def test_uk_transport_is_not_national(self):
        category = self.decider.decide(
            title="Easter travel hit: London-Milton Keynes trains halted",
            body="Mainline train services between London Euston and Milton Keynes are suspended in England.",
            source="Guardian",
            pipeline_hint="international",
        )
        self.assertEqual(category, "International")

    def test_wildlife_restoration_prefers_environment(self):
        category = self.decider.decide(
            title="Wildlife Trusts restore Norfolk land for ecology",
            body="Conservation groups are transforming Norfolk farmland into woodland habitat to boost biodiversity.",
            source="Guardian",
            pipeline_hint="environment",
        )
        self.assertEqual(category, "Environment")

    def test_ai_policy_story_prefers_technology(self):
        category = self.decider.decide(
            title="UK peers demand AI halt to protect creative rights",
            body="Lawmakers debate regulation for AI model training and copyright protections for artists.",
            source="Guardian",
            pipeline_hint="tech",
        )
        self.assertEqual(category, "Technology")

    def test_hyderabad_civic_story_prefers_telangana(self):
        category = self.decider.decide(
            title="Hyderabad civic body expands monsoon emergency teams",
            body="The Telangana government and GHMC have expanded emergency teams across Hyderabad ahead of heavy rain alerts.",
            source="The Hindu",
            pipeline_hint="national",
        )
        self.assertEqual(category, "Telangana")


if __name__ == "__main__":
    unittest.main()
