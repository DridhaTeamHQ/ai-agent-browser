import unittest

from core.orchestrator import HardenedOrchestrator


class _Decider:
    def __init__(self, result: str):
        self.result = result

    def decide(self, **kwargs):
        return self.result


class _Memory:
    def __init__(self, seen: bool = False):
        self.seen = seen

    def is_story_success(self, story_key: str, within_hours: int = 48):
        return self.seen and bool(story_key)


class OrchestratorCategoryRoutingTests(unittest.TestCase):
    def test_world_section_from_indian_source_stays_international(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        orchestrator.category_decider = _Decider("Politics")
        article = type("Article", (), {
            "category": "international",
            "source": "Times of India",
            "source_url": "https://timesofindia.indiatimes.com/world",
            "url": "https://timesofindia.indiatimes.com/world/middle-east/dubai-announces-eid-al-fitr-2026-holiday-for-public-sector-employees-four-day-break-confirmed/articleshow/129497390.cms",
        })()
        category = orchestrator._decide_cms_category(
            article,
            "Dubai confirms four-day Eid break for public sector",
            "Dubai Government confirms a four-day Eid Al Fitr holiday for public sector workers.",
        )
        self.assertEqual(category, "International")

    def test_non_india_story_never_maps_to_politics(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        orchestrator.category_decider = _Decider("Politics")
        article = type("Article", (), {
            "category": "international",
            "source": "BBC",
            "source_url": "https://www.bbc.com/news",
            "url": "https://www.bbc.com/news/articles/example",
        })()
        category = orchestrator._decide_cms_category(
            article,
            "Dubai confirms four-day Eid break for public sector",
            "Dubai Government confirms a four-day Eid Al Fitr holiday for public sector workers.",
        )
        self.assertEqual(category, "International")
    def test_priority_keyword_score_prefers_named_big_story(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        big = type("Article", (), {
            "title": "Donald Trump meets NATO leaders in Dubai summit",
            "body": "The White House says Donald Trump will meet NATO leaders in Dubai.",
            "url": "https://example.com/trump-dubai",
        })()
        generic = type("Article", (), {
            "title": "Regional tensions continue amid talks",
            "body": "Diplomatic talks are continuing in the region.",
            "url": "https://example.com/talks",
        })()
        self.assertGreater(
            orchestrator._article_priority_score(big, "international"),
            orchestrator._article_priority_score(generic, "international"),
        )
    def test_breaking_fallback_skips_low_signal_soft_story(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        article = type("Article", (), {
            "title": "Dubai Miracle Garden offers free entry",
            "url": "https://timesofindia.indiatimes.com/world/middle-east/dubai-miracle-garden-offers-free-entry/articleshow/123.cms",
        })()
        self.assertTrue(orchestrator._is_low_signal_story(article, "international", True))
        self.assertFalse(orchestrator._is_low_signal_story(article, "international", False))

    def test_degraded_ingestion_caps_single_category_publish_volume(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        self.assertEqual(orchestrator._effective_publish_targets(5, 3, 1), (2, 1))
        self.assertEqual(orchestrator._effective_publish_targets(5, 3, 2), (3, 1))
        self.assertEqual(orchestrator._effective_publish_targets(5, 3, 4), (5, 3))

    def test_story_already_published_checks_run_and_memory(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        orchestrator.memory = _Memory(seen=False)
        orchestrator.settings = type("Settings", (), {"story_dedupe_hours": 48})()
        self.assertTrue(orchestrator._story_already_published("abc123", {"abc123"}))
        self.assertFalse(orchestrator._story_already_published("abc123", set()))

        orchestrator.memory = _Memory(seen=True)
        self.assertTrue(orchestrator._story_already_published("abc123", set()))

    def test_cluster_story_key_uses_cluster_value_when_present(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        cluster = type("Cluster", (), {"story_key": "story-001", "canonical_title": "Title"})()
        self.assertEqual(orchestrator._cluster_story_key(cluster), "story-001")

    def test_build_image_query_prefers_story_terms_over_source_name(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        article = type("Article", (), {
            "title": "Judge blocks Pentagon from labeling Anthropic AI a supply chain risk",
            "body": (
                "A federal judge has temporarily blocked the Pentagon from labeling Anthropic a supply chain risk "
                "in a dispute over limits on using its AI in weapons or surveillance."
            ),
            "source": "BBC",
        })()
        query = orchestrator._build_image_query(article, article.title, "Technology")
        self.assertIn("anthropic", query)
        self.assertIn("pentagon", query)
        self.assertNotIn("bbc", query.lower())


if __name__ == "__main__":
    unittest.main()


