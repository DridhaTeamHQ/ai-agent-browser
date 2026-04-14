import unittest
from datetime import datetime, timedelta, timezone

from core.pipeline.category_agents import CategoryAgent, SourceConfig
from core.pipeline.models import IngestedArticle


class CategoryAgentTests(unittest.TestCase):
    def _agent(self, category: str) -> CategoryAgent:
        return CategoryAgent(category=category, sources=[])

    def test_single_word_keyword_boundary(self):
        agent = self._agent("international")
        self.assertTrue(agent._has_keyword("The war is escalating", "war"))
        self.assertFalse(agent._has_keyword("reward program expands", "war"))

    def test_business_source_url_hint_matches(self):
        agent = self._agent("business")
        article = IngestedArticle(
            category="business",
            source="Reuters",
            source_url="https://www.reuters.com/business/",
            url="https://www.reuters.com/business/example-idUS123ABC/",
            title="Policy update announced",
            body=(
                "Officials issued a policy update today after the finance ministry and market regulators "
                "reviewed trade and inflation impacts for key business sectors."
            ),
            published_time=None,
        )
        self.assertTrue(agent._matches_category(article))

    def test_international_rejects_india_national_without_theme(self):
        agent = self._agent("international")
        article = IngestedArticle(
            category="international",
            source="TOI",
            source_url="https://timesofindia.indiatimes.com/india",
            url="https://timesofindia.indiatimes.com/india/example/articleshow/123.cms",
            title="State cabinet announces reforms",
            body="The state cabinet approved local reforms in New Delhi.",
            published_time=None,
        )
        self.assertFalse(agent._matches_category(article))

    def test_sports_source_url_needs_real_sports_signal(self):
        agent = self._agent("sports")
        article = IngestedArticle(
            category="sports",
            source="BBC",
            source_url="https://www.bbc.com/sport",
            url="https://www.bbc.com/sport/articles/example",
            title="City council announces road closures",
            body=(
                "Officials announced fresh traffic diversions and parking restrictions around the city center "
                "for infrastructure maintenance and sewage pipeline work this week."
            ),
            published_time=None,
        )
        self.assertFalse(agent._matches_category(article))

    def test_freshness_rejects_old_article(self):
        agent = CategoryAgent(category="business", sources=[], max_article_age_minutes=30, require_published_time=True)
        article = IngestedArticle(
            category="business",
            source="Reuters",
            source_url="https://www.reuters.com/business/",
            url="https://www.reuters.com/business/example-idUS123ABC/",
            title="Policy update announced",
            body="Officials issued a policy update today.",
            published_time=(datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat(),
        )
        self.assertFalse(agent._is_fresh_article(article))

    def test_freshness_accepts_recent_article(self):
        agent = CategoryAgent(category="business", sources=[], max_article_age_minutes=30, require_published_time=True)
        article = IngestedArticle(
            category="business",
            source="Reuters",
            source_url="https://www.reuters.com/business/",
            url="https://www.reuters.com/business/example-idUS123ABC/",
            title="Policy update announced",
            body="Officials issued a policy update today.",
            published_time=(datetime.now(timezone.utc) - timedelta(minutes=12)).isoformat(),
        )
        self.assertTrue(agent._is_fresh_article(article))

    def test_freshness_rejects_missing_timestamp_when_required(self):
        agent = CategoryAgent(category="business", sources=[], max_article_age_minutes=30, require_published_time=True)
        article = IngestedArticle(
            category="business",
            source="Reuters",
            source_url="https://www.reuters.com/business/",
            url="https://www.reuters.com/business/example-idUS123ABC/",
            title="Policy update announced",
            body="Officials issued a policy update today.",
            published_time=None,
        )
        self.assertFalse(agent._is_fresh_article(article))

    def test_rejects_author_page_even_if_source_matches(self):
        agent = self._agent("international")
        article = IngestedArticle(
            category="international",
            source="NDTV",
            source_url="https://www.ndtv.com/world-news",
            url="https://www.ndtv.com/authors/prateek-shukla-24055",
            title="Prateek Shukla | Prateek Shukla News",
            body="Author archive page listing articles and profiles from the site.",
            published_time=None,
        )
        self.assertFalse(agent._matches_category(article))

    def test_rejects_opinion_story(self):
        agent = self._agent("national")
        article = IngestedArticle(
            category="national",
            source="NDTV",
            source_url="https://www.ndtv.com/india",
            url="https://www.ndtv.com/opinion/why-kerala-is-a-do-or-die-battle-for-congress-and-cpi-m-11332536",
            title="Opinion | Why Kerala Is A Do-Or-Die Battle For Congress And CPI-M",
            body="A commentary piece discussing election strategy and party positioning in Kerala.",
            published_time=None,
        )
        self.assertFalse(agent._matches_category(article))


if __name__ == "__main__":
    unittest.main()
