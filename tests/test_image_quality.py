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
    def test_limit_probe_candidates_caps_work_per_article(self):
        self.pipeline.max_probe_candidates = 3
        candidates = [
            ImageCandidate(f"https://example.com/{idx}.jpg", "body", 5, width_hint=100 + idx)
            for idx in range(6)
        ]
        limited = self.pipeline._limit_probe_candidates(candidates)
        self.assertEqual(len(limited), 3)
    def test_extract_candidates_filters_unrelated_toi_static_assets(self):
        html = '''
        <html>
          <meta property="og:image" content="https://static.toiimg.com/thumb/msid-129498409,width-1280,height-720,resizemode-6/photo.jpg" />
          <img src="https://static.toiimg.com/thumb/msid-122244803,width-1280,height-720,resizemode-6/photo.jpg" />
          <img src="https://static.toiimg.com/thumb/msid-118390705,width-1280,height-720,resizemode-6/photo.jpg" />
        </html>
        '''
        candidates = self.pipeline._extract_candidates(
            html,
            "https://timesofindia.indiatimes.com/sports/badminton/he-is-definitely-a-medal-prospect-former-cwg-medallist-backs-lakshya-sen-for-la-olympics-medal/articleshow/129498409.cms",
        )
        urls = [cand.url for cand in candidates]
        self.assertTrue(any("msid-129498409" in url for url in urls))
        self.assertFalse(any("msid-122244803" in url for url in urls))
        self.assertFalse(any("msid-118390705" in url for url in urls))

    def test_extract_candidates_filters_unrelated_indiatoday_story_assets(self):
        html = '''
        <html>
          <img src="https://akm-img-a-in.tosshub.com/indiatoday/images/story/202603/oil-tankers-attacked-iran-iraqi-crude-persian-gulf-hormuz-us-israel-war-tensions-16x9_0.jpg" />
          <img src="https://akm-img-a-in.tosshub.com/indiatoday/images/story/202603/zomato-swiggy-hit-due-to-lpg-crisis-amid-war-deliveries-down-16x9_0.jpg" />
        </html>
        '''
        candidates = self.pipeline._extract_candidates(
            html,
            "https://www.indiatoday.in/world/story/oil-tankers-attacked-iran-iraqi-crude-persian-gulf-hormuz-us-israel-war-tensions-2880683-2026-03-12",
        )
        urls = [cand.url for cand in candidates]
        self.assertTrue(any("oil-tankers-attacked-iran-iraqi-crude-persian-gulf-hormuz" in url for url in urls))
        self.assertFalse(any("zomato-swiggy-hit-due-to-lpg-crisis" in url for url in urls))
    def test_blur_rejection_sets_needs_image(self):
        with patch.object(ImageQualityPipeline, "_fetch_html", return_value="<html></html>"), \
            patch.object(ImageQualityPipeline, "_extract_candidates", return_value=[ImageCandidate("https://x/a.jpg", "og:image", 1)]), \
            patch.object(ImageQualityPipeline, "_probe", return_value={"ok": False, "reason": "blur_detected"}):
            result = self.pipeline.select_best("https://example.com/a", "title")

        self.assertFalse(result.passed)
        self.assertTrue(result.needs_image)
        self.assertIn("blur_detected", result.rejection_reasons)

    def test_static_image_is_used_when_vision_rejects_all_candidates(self):
        static_probe = {
            "ok": True,
            "score": 0.82,
            "width": 1280,
            "height": 720,
            "bytes_len": 60000,
            "content_type": "image/jpeg",
            "sharpness": 28.0,
            "relevance": 0.42,
            "bytes": b"fake-image-bytes",
        }
        with patch.object(ImageQualityPipeline, "_fetch_html", return_value="<html></html>"), \
            patch.object(ImageQualityPipeline, "_extract_candidates", return_value=[ImageCandidate("https://x/a.jpg", "og:image", 1)]), \
            patch.object(ImageQualityPipeline, "_probe", return_value=static_probe), \
            patch.object(ImageQualityPipeline, "_vision_assess", return_value={"usable": False, "reason": "vision_low_quality"}), \
            patch.object(ImageQualityPipeline, "_store_image", return_value="C:\\fake.jpg"):
            result = self.pipeline.select_best("https://example.com/a", "title")

        self.assertTrue(result.passed)
        self.assertEqual(result.local_path, "C:\\fake.jpg")
        self.assertIn("vision_low_quality", result.rejection_reasons)

    def test_static_fallback_is_allowed_when_vision_marks_image_irrelevant(self):
        static_probe = {
            "ok": True,
            "score": 0.82,
            "width": 1280,
            "height": 720,
            "bytes_len": 60000,
            "content_type": "image/jpeg",
            "sharpness": 28.0,
            "relevance": 0.42,
            "bytes": b"fake-image-bytes",
        }
        with patch.object(ImageQualityPipeline, "_fetch_html", return_value="<html></html>"), \
            patch.object(ImageQualityPipeline, "_extract_candidates", return_value=[ImageCandidate("https://x/a.jpg", "og:image", 1)]), \
            patch.object(ImageQualityPipeline, "_probe", return_value=static_probe), \
            patch.object(ImageQualityPipeline, "_vision_assess", return_value={"usable": False, "reason": "vision_irrelevant"}), \
            patch.object(ImageQualityPipeline, "_store_image", return_value="C:\\fake.jpg"):
            result = self.pipeline.select_best("https://example.com/a", "Damaged aircraft at Saudi base")

        self.assertTrue(result.passed)
        self.assertEqual(result.local_path, "C:\\fake.jpg")
        self.assertIn("vision_irrelevant", result.rejection_reasons)


if __name__ == "__main__":
    unittest.main()






