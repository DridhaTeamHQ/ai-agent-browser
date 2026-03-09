import unittest

from core.intelligence.summarize import Summarizer


class SummarizerStyleExampleTests(unittest.TestCase):
    def setUp(self):
        self.summarizer = object.__new__(Summarizer)
        self.summarizer._training_examples = [
            {
                "category": "Technology",
                "style": "policy_regulation",
                "source_title": "UK peers demand AI halt to protect creative rights",
                "target_title": "UK Peers Push AI Curbs to Protect Creative Rights",
                "target_body": "The row is intensifying the debate over AI regulation and intellectual property.",
                "_style_tokens": frozenset({"uk", "peers", "demand", "ai", "halt", "creative", "rights", "regulation", "protect"}),
            },
            {
                "category": "Environment",
                "style": "restoration_conservation",
                "source_title": "Wildlife Trusts restore Norfolk land for ecology",
                "target_title": "Wildlife Trusts Turn Norfolk Land Into New Habitat",
                "target_body": "The project is aimed at boosting biodiversity and rebuilding damaged ecosystems.",
                "_style_tokens": frozenset({"wildlife", "trusts", "restore", "norfolk", "land", "ecology", "biodiversity", "habitat"}),
            },
            {
                "category": "Finance",
                "style": "market_move",
                "source_title": "Gold prices surge sharply in Hyderabad",
                "target_title": "Gold Jumps in Hyderabad as Global Market Swings Bite",
                "target_body": "Analysts say global market volatility is continuing to push domestic bullion prices higher.",
                "_style_tokens": frozenset({"gold", "prices", "surge", "hyderabad", "market", "global", "bullion"}),
            },
        ]

    def test_pick_style_examples_prefers_matching_topic(self):
        picks = self.summarizer._pick_style_examples(
            "UK peers demand AI halt to protect creative rights",
            "Lawmakers are debating whether AI firms can use copyrighted work without consent.",
            limit=2,
        )
        self.assertGreaterEqual(len(picks), 1)
        self.assertEqual(picks[0]["category"], "Technology")

    def test_build_dynamic_style_examples_formats_reference_block(self):
        block = self.summarizer._build_dynamic_style_examples(
            "Wildlife Trusts restore Norfolk land for ecology",
            "The project aims to boost biodiversity through habitat restoration.",
            limit=1,
        )
        self.assertIn("Closest reference examples", block)
        self.assertIn("Category=Environment", block)
        self.assertIn("Better title='Wildlife Trusts Turn Norfolk Land Into New Habitat'", block)

    def test_expand_body_uses_source_specific_context(self):
        body = "Netflix is opening a new office in Hyderabad as its second facility in India after Mumbai."
        source_title = "Netflix to open office in Hyderabad"
        source_body = (
            "Netflix is set to establish a new office in Hyderabad, marking its second facility in India after Mumbai. "
            "The 30,000 sq ft centre will be inaugurated on March 12 by CM Revanth Reddy. "
            "The hub will focus on animation, visual effects and digital content production. "
            "The move is expected to boost the AVGC sector while creating new job opportunities for skilled youth."
        )
        expanded = self.summarizer._expand_body(body, source_title, source_body, target_chars=360, max_chars=365)
        self.assertGreaterEqual(len(expanded), 355)
        self.assertLessEqual(len(expanded), 365)
        self.assertIn("30,000 sq ft centre", expanded)
        self.assertNotIn("follow-up decisions are being prepared", expanded)


    def test_has_title_hook_accepts_active_consequence_headline(self):
        self.assertTrue(self.summarizer._has_title_hook("Airstrikes Empty Beirut Suburbs as Crisis Deepens"))

    def test_boost_title_punch_removes_weak_explainer_phrase(self):
        boosted = self.summarizer._boost_title_punch(
            "Rupee hits all-time low: what it means",
            "Rupee hits all-time low as oil shock rattles markets",
        )
        self.assertNotIn("what it means", boosted.lower())
        self.assertLessEqual(len(boosted), 62)
    def test_fit_body_length_trims_to_target_band(self):
        source_title = "Gold prices surge sharply in Hyderabad"
        source_body = (
            "Gold prices rose sharply in Hyderabad on Saturday, with 24-carat gold jumping by Rs 2,510. "
            "The price of 22-carat gold also increased sharply. "
            "Silver remained around Rs 1.04 lakh per kg. "
            "Analysts say global volatility is influencing domestic bullion prices."
        )
        long_body = (
            "Gold prices rose sharply in Hyderabad on Saturday, with 24-carat rates seeing a major jump. "
            "The move also lifted 22-carat prices and kept silver elevated in local markets. "
            "Traders say global volatility is feeding directly into domestic bullion rates. "
            "The sharp move is now forcing buyers to reassess near-term purchases before the next session opens."
        )
        fitted = self.summarizer._fit_body_length(long_body, source_title, source_body, target_chars=360, min_chars=355, max_chars=365)
        self.assertGreaterEqual(len(fitted), 355)
        self.assertLessEqual(len(fitted), 365)

    def test_fit_body_length_avoids_dangling_tail(self):
        source_title = "Akhtar blasts India, claims cricket imbalance"
        source_body = (
            "Shoaib Akhtar sharply criticized India's T20 World Cup win and said the rivalry is intensifying. "
            "He argued that the gap between teams is widening and warned about long-term balance concerns. "
            "Analysts say the remarks are amplifying debate around competitiveness in major tournaments."
        )
        dangling = (
            "Shoaib Akhtar has sharply criticized India's overwhelming T20 World Cup win, accusing the team "
            "of creating an imbalance in cricket. The former Pakistan pacer compared India's dominance to a "
            "privileged child ruling local games. His remarks underscore the intense cricket rivalry between the "
            "nations. India's victory solidifies their status as a powerhouse in the"
        )
        fitted = self.summarizer._fit_body_length(dangling, source_title, source_body, target_chars=360, min_chars=345, max_chars=365)
        self.assertGreaterEqual(len(fitted), 345)
        self.assertLessEqual(len(fitted), 365)
        self.assertFalse(fitted.lower().endswith("in the."))
        self.assertTrue(fitted.endswith((".", "!", "?")))


if __name__ == "__main__":
    unittest.main()



