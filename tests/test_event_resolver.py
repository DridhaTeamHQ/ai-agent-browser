import json
import os
import unittest

from core.pipeline.event_resolver import EventResolver
from core.pipeline.models import IngestedArticle


class EventResolverTests(unittest.TestCase):
    def test_clusters_duplicate_story(self):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "duplicate_stories.json")
        with open(fixture_path, "r", encoding="utf-8-sig") as f:
            rows = json.load(f)

        articles = [IngestedArticle(**row) for row in rows]
        resolver = EventResolver(title_similarity=0.4, content_similarity=0.1, time_window_minutes=90)
        clusters = resolver.cluster(articles)

        self.assertEqual(len(clusters), 2)
        sizes = sorted([len(c.articles) for c in clusters], reverse=True)
        self.assertEqual(sizes, [3, 1])


if __name__ == "__main__":
    unittest.main()
