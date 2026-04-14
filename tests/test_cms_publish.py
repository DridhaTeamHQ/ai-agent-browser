import unittest
from unittest.mock import AsyncMock, Mock, patch, call

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

    def test_submit_for_review_footer_button_scores_highest(self):
        footer_score = CMSPublisher._publish_candidate_rank(
            {
                "text": "Submit for Review",
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
        publisher._find_english_title_field = AsyncMock(return_value=Mock())
        publisher._find_english_body_field = AsyncMock(return_value=Mock())
        publisher._fill_react_input = AsyncMock(return_value=True)
        publisher._scroll_form_to_section = AsyncMock(return_value=True)
        publisher._select_category = AsyncMock(return_value=True)
        publisher._fill_keywords = AsyncMock(return_value=True)
        publisher._download_article_image = AsyncMock(return_value=None)
        publisher._upload_image = AsyncMock(return_value=True)

        data = ArticleData(
            english_title="Title",
            english_body="Body",
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


class TestCMSNavigationFlow(unittest.IsolatedAsyncioTestCase):
    async def test_create_article_uses_sidebar_articles_then_modal(self):
        publisher = object.__new__(CMSPublisher)
        publisher.page = Mock()
        publisher.page.is_closed.return_value = False
        publisher.logger = Mock()
        publisher.ensure_live_page = AsyncMock(return_value=True)
        publisher._wait_stable = AsyncMock()
        publisher._dump_debug = AsyncMock()
        publisher._is_article_form_open = AsyncMock(side_effect=[False, True])
        publisher._open_articles_management = AsyncMock(return_value=True)
        publisher._open_create_article_modal = AsyncMock(return_value=True)
        publisher._open_create_route_from_link = AsyncMock(return_value=False)
        publisher._open_create_route_direct = AsyncMock(return_value=False)

        ok = await publisher.create_article()

        self.assertTrue(ok)
        publisher._open_articles_management.assert_awaited_once()
        publisher._open_create_article_modal.assert_awaited_once()
        publisher._open_create_route_from_link.assert_not_awaited()
        publisher._open_create_route_direct.assert_not_awaited()
        publisher._dump_debug.assert_not_awaited()


class TestCMSFormSectionScrolling(unittest.IsolatedAsyncioTestCase):
    async def test_fill_form_scrolls_sections_before_interaction(self):
        publisher = object.__new__(CMSPublisher)
        publisher.page = _DummyPage()
        publisher.logger = Mock()
        publisher.image_finder = Mock()
        publisher.ensure_live_page = AsyncMock(return_value=True)
        publisher._is_article_form_open = AsyncMock(return_value=True)
        publisher._find_english_title_field = AsyncMock(return_value=Mock())
        publisher._find_english_body_field = AsyncMock(return_value=Mock())
        publisher._fill_react_input = AsyncMock(return_value=True)
        publisher._scroll_form_to_section = AsyncMock(return_value=True)
        publisher._select_category = AsyncMock(return_value=True)
        publisher._fill_keywords = AsyncMock(return_value=True)
        publisher._upload_image = AsyncMock(return_value=True)

        data = ArticleData(
            english_title="Title",
            english_body="Body",
            category="Andhra Pradesh",
            hashtag="#news #state",
            image_path="C:\\chosen.jpg",
        )

        with patch("core.cms.publish.os.path.exists", return_value=True):
            ok = await publisher.fill_form(data)

        self.assertTrue(ok)
        publisher._scroll_form_to_section.assert_has_awaits(
            [
                call("Category"),
                call("Keywords"),
                call("Media"),
            ]
        )
        publisher._select_category.assert_awaited_once_with("Andhra Pradesh")
        publisher._fill_keywords.assert_awaited_once_with("#news #state")
        publisher._upload_image.assert_awaited_once_with("C:\\chosen.jpg")


class TestCMSKeywordsField(unittest.IsolatedAsyncioTestCase):
    async def test_fill_keywords_uses_field_press_not_global_keyboard(self):
        publisher = object.__new__(CMSPublisher)
        publisher.page = Mock()
        publisher.logger = Mock()
        publisher._scroll_form_to_section = AsyncMock(return_value=True)
        publisher._scroll_locator_into_view = AsyncMock(return_value=True)

        field = Mock()
        field.click = AsyncMock()
        field.fill = AsyncMock()
        field.type = AsyncMock()
        field.press = AsyncMock()

        publisher._find_keywords_field = AsyncMock(return_value=field)

        ok = await publisher._fill_keywords("#breaking #news")

        self.assertTrue(ok)
        self.assertEqual(field.click.await_count, 2)
        self.assertEqual(field.fill.await_count, 2)
        self.assertEqual(field.type.await_count, 2)
        self.assertEqual(field.press.await_count, 2)
        publisher._scroll_form_to_section.assert_awaited_once_with("Keywords")


if __name__ == "__main__":
    unittest.main()
