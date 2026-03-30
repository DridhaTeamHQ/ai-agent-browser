import unittest
from unittest.mock import AsyncMock, Mock, patch

from core.cms.publish import ArticleData, CMSPublisher


class TestCMSPublishCandidateRank(unittest.TestCase):
    def test_rejects_approval_status_combobox(self):
        score = CMSPublisher._publish_candidate_rank(
            {
                "text": "Publish",
                "role": "combobox",
                "aria_has_popup": "listbox",
                "ancestor_text": "Approval Status Publish",
                "top": 240,
                "left": 100,
                "bottom": 280,
                "viewport_height": 900,
                "viewport_width": 1400,
            }
        )
        self.assertLess(score, 0)

    def test_publish_article_footer_button_scores_highest(self):
        footer_score = CMSPublisher._publish_candidate_rank(
            {
                "text": "Publish Article",
                "type": "submit",
                "within_dialog": True,
                "in_form": True,
                "top": 780,
                "left": 1120,
                "bottom": 840,
                "viewport_height": 900,
                "viewport_width": 1400,
            }
        )
        plain_publish_score = CMSPublisher._publish_candidate_rank(
            {
                "text": "Publish",
                "within_dialog": True,
                "top": 250,
                "left": 110,
                "bottom": 290,
                "viewport_height": 900,
                "viewport_width": 1400,
            }
        )
        self.assertGreater(footer_score, plain_publish_score)

    def test_nearby_approval_status_penalty_drops_generic_publish(self):
        score = CMSPublisher._publish_candidate_rank(
            {
                "text": "Publish",
                "ancestor_text": "Approval Status Publish Draft",
                "within_dialog": True,
                "top": 260,
                "left": 120,
                "bottom": 300,
                "viewport_height": 900,
                "viewport_width": 1400,
            }
        )
        self.assertLess(score, 20)


class _DummyLocator:
    @property
    def first(self):
        return self


class _DummyPage:
    def locator(self, _selector):
        return _DummyLocator()


class TestCMSImageFallback(unittest.IsolatedAsyncioTestCase):
    async def test_fill_form_uses_image_search_when_direct_image_missing(self):
        publisher = object.__new__(CMSPublisher)
        publisher.page = _DummyPage()
        publisher.logger = Mock()
        publisher.image_finder = Mock()
        publisher.image_finder.find_and_download = AsyncMock(return_value="C:\\searched.jpg")
        publisher.ensure_live_page = AsyncMock(return_value=True)
        publisher._is_article_form_open = AsyncMock(return_value=True)
        publisher._fill_react_input = AsyncMock(return_value=True)
        publisher._select_category = AsyncMock(return_value=True)
        publisher._fill_hashtag = AsyncMock(return_value=True)
        publisher._download_article_image = AsyncMock(return_value=None)
        publisher._upload_image = AsyncMock(return_value=True)

        data = ArticleData(
            english_title="Title",
            english_body="Body",
            telugu_title="TT",
            telugu_body="TB",
            category="International",
            hashtag="#news",
            image_search_query="spain airspace military plane photo",
            image_path=None,
            image_url=None,
        )

        with patch("core.cms.publish.os.path.exists", side_effect=lambda p: p == "C:\\searched.jpg"):
            ok = await publisher.fill_form(data)

        self.assertTrue(ok)
        publisher.image_finder.find_and_download.assert_awaited_once_with("spain airspace military plane photo")
        publisher._upload_image.assert_awaited_once_with("C:\\searched.jpg")


if __name__ == "__main__":
    unittest.main()
