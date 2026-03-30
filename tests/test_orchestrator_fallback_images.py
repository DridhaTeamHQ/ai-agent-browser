import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from core.media.image_quality import ImageDecision
from core.orchestrator import HardenedOrchestrator
from core.validator import ValidationResult


class OrchestratorFallbackImageTests(unittest.TestCase):
    def test_allows_indiatoday_fallback_url_when_not_blocked(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        orchestrator.image_pipeline = SimpleNamespace(_is_blocked_image_url=lambda url: False)
        article = type("Article", (), {
            "source": "India Today",
            "main_image": "https://akm-img-a-in.tosshub.com/indiatoday/images/story/202603/example-16x9_0.jpg",
            "og_image": "",
        })()
        self.assertEqual(orchestrator._select_fallback_image_url(article), article.main_image)

    def test_blocks_ndtv_fallback_url(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        article = type("Article", (), {
            "source": "NDTV",
            "main_image": "https://c.ndtvimg.com/2026-03/example.jpg",
            "og_image": "",
        })()
        self.assertIsNone(orchestrator._select_fallback_image_url(article))


class OrchestratorPublishSearchFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_article_proceeds_with_search_fallback_when_image_missing(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        orchestrator.logger = Mock()
        orchestrator.summarizer = Mock(
            summarize=Mock(return_value={"title": "Spain closes airspace to US military planes", "body": "A" * 320})
        )
        orchestrator.telugu_writer = Mock(
            write=Mock(return_value={"title": "TT", "body": "TB" * 160})
        )
        orchestrator.image_pipeline = Mock(
            select_best=Mock(
                return_value=ImageDecision(
                    passed=False,
                    needs_image=True,
                    rejection_reasons=["vision_irrelevant"],
                )
            )
        )
        orchestrator.validator = Mock(validate=Mock(return_value=ValidationResult(is_valid=True)))
        orchestrator._decide_cms_category = Mock(return_value="International")
        orchestrator._build_image_query = Mock(return_value="spain us military planes photo")
        orchestrator._build_hashtags = Mock(return_value="#breaking #news")
        orchestrator._execute_browser_workflow = AsyncMock(return_value=True)

        article = type(
            "Article",
            (),
            {
                "title": "Spain shuts airspace to US planes linked to Iran strikes",
                "body": "Source body " * 80,
                "url": "https://example.com/story",
                "main_image": "",
                "og_image": "",
                "source": "India Today",
            },
        )()
        metrics = SimpleNamespace(record_image_result=lambda *args, **kwargs: None)

        ok, reason = await HardenedOrchestrator._publish_article(orchestrator, article, False, metrics)

        self.assertTrue(ok)
        self.assertEqual(reason, "")
        sent_data = orchestrator._execute_browser_workflow.await_args.args[0]
        self.assertEqual(sent_data.image_search_query, "spain us military planes photo")
        self.assertIsNone(sent_data.image_path)
        self.assertIsNone(sent_data.image_url)


if __name__ == "__main__":
    unittest.main()
