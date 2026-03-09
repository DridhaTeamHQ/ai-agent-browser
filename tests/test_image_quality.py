import os
import unittest
from unittest.mock import patch

from core.media.image_quality import ImageCandidate, ImageQualityPipeline


class ImageQualityPipelineTests(unittest.TestCase):
    def setUp(self):
        self.thresholds = {
            "min_width": 800,
            "min_height": 450,
            "min_file_size_bytes": 50000,
            "min_aspect_ratio": 0.4,
            "max_aspect_ratio": 2.8,
            "min_sharpness": 18.0,
        }
        self.pipeline = ImageQualityPipeline(thresholds=self.thresholds)

    def test_candidate_extraction_priority(self):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "image_fixture.html")
        with open(fixture_path, "r", encoding="utf-8") as f:
            html = f.read()

        candidates = self.pipeline._extract_candidates(html, "https://example.com/news/story")
        self.assertGreaterEqual(len(candidates), 4)
        self.assertEqual(candidates[0].source, "og:image")
        self.assertEqual(candidates[1].source, "twitter:image")


    def test_blocked_image_url_rejects_indiatoday_screenshot_assets(self):
        self.assertTrue(
            self.pipeline._is_blocked_image_url(
                "https://akm-img-a-in.tosshub.com/indiatoday/styles/medium_crop_simple/public/2026-03/screenshot_2026-03-07_145159.png"
            )
        )

    def test_blocked_image_url_rejects_toi_representational_assets(self):
        self.assertTrue(
            self.pipeline._is_blocked_image_url(
                "https://static.toiimg.com/thumb/msid-129306105,imgsize-2032116,width-400,resizemode-4/ai-generated-image-used-only-for-representational-purpose.jpg"
            )
        )

    def test_extract_candidates_includes_source_specific_hero_first(self):
        html = '''
        <html>
          <meta property="og:image" content="https://example.com/generic.jpg" />
          <img src="https://static.toiimg.com/thumb/msid-129310476,width-1280,height-720,imgsize-169964,resizemode-6/photo.jpg" />
        </html>
        '''
        candidates = self.pipeline._extract_candidates(
            html,
            "https://timesofindia.indiatimes.com/world/story/example/articleshow/129310476.cms",
        )
        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(candidates[0].source, "source:toi")
        self.assertIn("msid-129310476", candidates[0].url)

    def test_toi_source_candidates_ignore_non_article_msid(self):
        html = '''
        <html>
          <img src="https://static.toiimg.com/thumb/msid-999999,width-1280,height-720,resizemode-6/photo.jpg" />
          <img src="https://static.toiimg.com/thumb/msid-129310476,width-1280,height-720,resizemode-6/photo.jpg" />
        </html>
        '''
        candidates = self.pipeline._extract_source_specific_candidates(
            html,
            "https://timesofindia.indiatimes.com/world/story/example/articleshow/129310476.cms",
        )
        self.assertEqual(len(candidates), 1)
        self.assertIn("129310476", candidates[0].url)
    def test_blur_rejection_sets_needs_image(self):
        with patch.object(ImageQualityPipeline, "_fetch_html", return_value="<html></html>"), \
            patch.object(ImageQualityPipeline, "_extract_candidates", return_value=[ImageCandidate("https://x/a.jpg", "og:image", 1)]), \
            patch.object(ImageQualityPipeline, "_probe", return_value={"ok": False, "reason": "blur_detected"}):
            result = self.pipeline.select_best("https://example.com/a", "title")

        self.assertFalse(result.passed)
        self.assertTrue(result.needs_image)
        self.assertIn("blur_detected", result.rejection_reasons)


if __name__ == "__main__":
    unittest.main()



