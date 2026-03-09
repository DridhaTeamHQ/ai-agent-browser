import unittest
from datetime import datetime, timezone

from core.pipeline.breaking import BreakingNewsClassifier
from core.pipeline.models import EventCluster, IngestedArticle


class BreakingClassifierTests(unittest.TestCase):
    def _article(self, source, ts):
        return IngestedArticle(
            category="international",
            source=source,
            source_url="https://example.com",
            url=f"https://example.com/{source}/{ts}",
            title="Emergency talks after border clash",
            body="Leaders held emergency talks after a border clash and multiple governments confirmed details.",
            published_time=ts,
        )

    def test_breaking_true_with_3_sources_inside_window(self):
        a1 = self._article("Reuters", "2026-03-05T10:00:00Z")
        a2 = self._article("BBC", "2026-03-05T10:12:00Z")
        a3 = self._article("Guardian", "2026-03-05T10:20:00Z")
        cluster = EventCluster(
            id="c1",
            canonical_title=a1.title,
            articles=[a1, a2, a3],
            source_groups={"Reuters": [a1], "BBC": [a2], "Guardian": [a3]},
            start_time=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 3, 5, 10, 20, tzinfo=timezone.utc),
            dominant_category="international",
        )
        classifier = BreakingNewsClassifier(
            source_credibility={"Reuters": 0.95, "BBC": 0.9, "Guardian": 0.88},
            min_sources=3,
            max_window_minutes=30,
            confidence_threshold=0.6,
        )
        result = classifier.classify(cluster)
        self.assertTrue(result.is_breaking)

    def test_breaking_false_if_window_exceeds(self):
        a1 = self._article("Reuters", "2026-03-05T10:00:00Z")
        a2 = self._article("BBC", "2026-03-05T11:15:00Z")
        a3 = self._article("Guardian", "2026-03-05T11:20:00Z")
        cluster = EventCluster(
            id="c2",
            canonical_title=a1.title,
            articles=[a1, a2, a3],
            source_groups={"Reuters": [a1], "BBC": [a2], "Guardian": [a3]},
            start_time=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 3, 5, 11, 20, tzinfo=timezone.utc),
            dominant_category="international",
        )
        classifier = BreakingNewsClassifier(
            source_credibility={"Reuters": 0.95, "BBC": 0.9, "Guardian": 0.88},
            min_sources=3,
            max_window_minutes=30,
            confidence_threshold=0.6,
        )
        result = classifier.classify(cluster)
        self.assertFalse(result.is_breaking)
        self.assertTrue(any("outside_30m_window" in reason for reason in result.reasons))


if __name__ == "__main__":
    unittest.main()
