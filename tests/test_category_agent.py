import unittest

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
            body="Officials issued a policy update today.",
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


if __name__ == "__main__":
    unittest.main()
