import unittest

from core.sources.indiatoday import IndiaTodayScraper
from core.sources.reuters import ReutersScraper


class SourceBodyExtractionTests(unittest.TestCase):
    def test_indiatoday_prefers_article_paragraphs_over_meta_description(self):
        scraper = object.__new__(IndiaTodayScraper)
        html = """
        <html>
          <meta property="og:description" content="Short preview snippet only." />
          <p>Netflix is set to establish a new office in Hyderabad, marking its second facility in India after Mumbai.</p>
          <p>The 30,000 sq ft centre will be inaugurated on March 12 by CM Revanth Reddy.</p>
          <p>The hub will focus on animation, visual effects and digital content production.</p>
          <p>The move is expected to boost the AVGC sector while creating new job opportunities for skilled youth.</p>
        </html>
        """

        body = scraper._extract_body(html)
        self.assertIn("30,000 sq ft centre", body)
        self.assertIn("animation, visual effects", body)
        self.assertNotEqual(body, "Short preview snippet only.")

    def test_reuters_prefers_multiple_story_paragraphs_over_meta_description(self):
        scraper = object.__new__(ReutersScraper)
        html = """
        <html>
          <meta property="og:description" content="Preview line from metadata." />
          <p>India unveiled a revised semiconductor policy on Wednesday after a cabinet review.</p>
          <p>Officials said the package includes fresh incentives, timeline changes and tighter oversight.</p>
          <p>The move is expected to shape investment decisions in the coming months.</p>
        </html>
        """

        body = scraper._extract_body(html)
        self.assertIn("fresh incentives, timeline changes", body)
        self.assertIn("investment decisions", body)
        self.assertNotEqual(body, "Preview line from metadata.")


if __name__ == "__main__":
    unittest.main()
