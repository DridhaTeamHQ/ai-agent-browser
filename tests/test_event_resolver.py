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

    def test_clusters_cross_source_variants_into_one_story(self):
        resolver = EventResolver()
        articles = [
            IngestedArticle(
                category="international",
                source="NDTV",
                source_url="https://www.ndtv.com/world-news",
                url="https://example.com/iran-grid-1",
                title="Trump delays Iran power-grid strikes until April 6",
                body=(
                    "Trump has delayed threatened strikes on Iran's power grid until April 6. "
                    "The threat was meant to pressure Iran to reopen the Strait of Hormuz."
                ),
                published_time="2026-03-27T12:00:00Z",
            ),
            IngestedArticle(
                category="international",
                source="AlJazeera",
                source_url="https://www.aljazeera.com/news",
                url="https://example.com/iran-grid-2",
                title="US postpones attacks on Iranian power grid to April 6",
                body=(
                    "The US president postponed threatened attacks on Iran's power grid until April 6. "
                    "The move is aimed at pushing Tehran to reopen the Strait of Hormuz."
                ),
                published_time="2026-03-27T12:18:00Z",
            ),
            IngestedArticle(
                category="international",
                source="India Today",
                source_url="https://www.indiatoday.in/world",
                url="https://example.com/iran-grid-3",
                title="White House puts Iran grid strike threat on hold till April 6",
                body=(
                    "The White House has put its Iran power-grid strike threat on hold till April 6. "
                    "Officials still want Tehran to reopen the Strait of Hormuz."
                ),
                published_time="2026-03-27T12:31:00Z",
            ),
            IngestedArticle(
                category="international",
                source="BBC",
                source_url="https://www.bbc.com/news",
                url="https://example.com/iran-war-4",
                title="Lebanon PM says Israeli troop push violates sovereignty",
                body=(
                    "Lebanon's prime minister said Israel's troop expansion into southern Lebanon violates sovereignty. "
                    "The warning followed Israel's decision to send additional troops into the region."
                ),
                published_time="2026-03-27T12:25:00Z",
            ),
        ]

        clusters = resolver.cluster(articles)

        self.assertEqual(len(clusters), 2)
        sizes = sorted(len(cluster.articles) for cluster in clusters)
        self.assertEqual(sizes, [1, 3])
        story_keys = {cluster.story_key for cluster in clusters}
        self.assertEqual(len(story_keys), 2)


if __name__ == "__main__":
    unittest.main()
