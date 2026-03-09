import unittest

from core.orchestrator import HardenedOrchestrator


class OrchestratorFallbackImageTests(unittest.TestCase):
    def test_blocks_indiatoday_fallback_url(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        article = type('Article', (), {
            'source': 'India Today',
            'main_image': 'https://akm-img-a-in.tosshub.com/indiatoday/images/story/202603/example-16x9_0.jpg',
            'og_image': '',
        })()
        self.assertIsNone(orchestrator._select_fallback_image_url(article))

    def test_blocks_ndtv_fallback_url(self):
        orchestrator = object.__new__(HardenedOrchestrator)
        article = type('Article', (), {
            'source': 'NDTV',
            'main_image': 'https://c.ndtvimg.com/2026-03/example.jpg',
            'og_image': '',
        })()
        self.assertIsNone(orchestrator._select_fallback_image_url(article))


if __name__ == '__main__':
    unittest.main()
