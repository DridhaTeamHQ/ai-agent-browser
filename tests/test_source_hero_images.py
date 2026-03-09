import unittest

from core.sources.indiatoday import IndiaTodayScraper
from core.sources.timesofindia import TimesOfIndiaScraper


class SourceHeroImageTests(unittest.TestCase):
    def test_indiatoday_prefers_story_image_over_reporter_asset(self):
        scraper = object.__new__(IndiaTodayScraper)
        html = '''
        <html>
          <meta property="og:image" content="https://akm-img-a-in.tosshub.com/sites/indiatoday/resources/img/default-690x413.png" />
          <img src="https://akm-img-a-in.tosshub.com/images/reporter/201802/Ashraf_Wani.jpeg" />
          <img src="https://akm-img-a-in.tosshub.com/indiatoday/images/story/202603/india-today-in-lebanon-074630965-16x9_0.jpg?VersionId=abc" />
        </html>
        '''
        main_image = scraper._extract_main_image(html)
        self.assertIn('/indiatoday/images/story/', main_image)
        self.assertIn('16x9_0', main_image)

    def test_toi_prefers_thumb_story_image(self):
        scraper = object.__new__(TimesOfIndiaScraper)
        html = '''
        <html>
          <img src="https://static.toiimg.com/thumb/msid-129310476,width-1280,height-720,imgsize-169964,resizemode-6/photo.jpg" />
        </html>
        '''
        main_image = scraper._extract_main_image(html)
        self.assertIn('static.toiimg.com/thumb/msid-129310476', main_image)


if __name__ == "__main__":
    unittest.main()
