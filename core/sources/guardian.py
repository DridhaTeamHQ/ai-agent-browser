"""
The Guardian News Scraper - Pure HTML scraping only.

NO BROWSER. Uses httpx to fetch HTML directly.
Extracts: title, body, og:image, published time.

The Guardian has clean images without watermarks.
"""

import httpx
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from utils.logger import get_logger

# Month name -> number for sorting (newest first)
_MONTH = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


@dataclass
class Article:
    """Article data container."""
    url: str
    title: str
    body: str
    og_image: Optional[str]
    published_time: Optional[str]
    source: str = "Guardian"


class GuardianScraper:
    """
    The Guardian scraper using pure HTTP requests.
    
    NO BROWSER REQUIRED.
    Clean images without watermarks.
    """
    
    BASE_URL = "https://www.theguardian.com"
    NEWS_URL = "https://www.theguardian.com/world"
    
    def __init__(self):
        self.logger = get_logger("guardian_scraper")
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    def _date_from_guardian_url(self, url: str) -> Optional[Tuple[int, int, int]]:
        """Extract (year, month, day) from Guardian URL for sorting. Returns None if no date."""
        m = re.search(r'/world/(\d{4})/([a-z]{3})/(\d{1,2})/', url)
        if not m:
            return None
        year, mon_str, day = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mon = _MONTH.get(mon_str)
        if mon is None:
            return None
        return (year, mon, day)

    def get_article_links(self, limit: int = 20) -> List[str]:
        """Get article links from The Guardian World News page, newest first."""
        try:
            response = self.client.get(self.NEWS_URL)
            response.raise_for_status()
            html = response.text
            
            # Guardian article pattern - /world/2026/jan/28/article-slug
            pattern = r'href="(https://www\.theguardian\.com/world/\d{4}/[a-z]{3}/\d{1,2}/[^"]+)"'
            matches = re.findall(pattern, html)
            unique_links = list(dict.fromkeys(matches))
            
            # Sort newest first (by date in URL)
            def sort_key(url: str):
                d = self._date_from_guardian_url(url)
                return d if d else (0, 0, 0)
            unique_links.sort(key=sort_key, reverse=True)
            unique_links = unique_links[:limit]
            
            self.logger.info(f"Found {len(unique_links)} article links (newest first)")
            return unique_links
            
        except Exception as e:
            self.logger.error(f"Failed to get article links: {e}")
            return []
    
    def scrape_article(self, url: str) -> Optional[Article]:
        """
        Scrape a single article.
        
        Returns Article if all required fields present, else None.
        """
        try:
            response = self.client.get(url)
            response.raise_for_status()
            html = response.text
            
            # Extract title
            title = self._extract_title(html)
            if not title or len(title) < 20:
                self.logger.warning(f"No valid title found: {url}")
                return None
            
            # Extract body
            body = self._extract_body(html)
            if not body or len(body) < 100:
                self.logger.warning(f"No valid body found: {url}")
                return None
            
            # Extract OG image (REQUIRED)
            og_image = self._extract_og_image(html)
            if not og_image:
                self.logger.warning(f"No OG image found: {url}")
                return None
            
            # Extract published time (optional)
            published_time = self._extract_published_time(html)
            
            article = Article(
                url=url,
                title=title.strip(),
                body=body.strip(),
                og_image=og_image,
                published_time=published_time,
                source="Guardian"
            )
            
            self.logger.info(f"✅ Scraped: {title[:50]}...")
            return article
            
        except Exception as e:
            self.logger.error(f"Failed to scrape {url}: {e}")
            return None
    
    def _extract_title(self, html: str) -> Optional[str]:
        """Extract article title."""
        patterns = [
            r'<meta\s+property="og:title"\s+content="([^"]+)"',
            r'<meta\s+content="([^"]+)"\s+property="og:title"',
            r'"headline"\s*:\s*"([^"]+)"',
            r'<title>([^<]+)</title>',
            r'<h1[^>]*>([^<]+)</h1>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up Guardian suffix
                title = re.sub(r'\s*\|\s*.*$', '', title)
                if len(title) > 15:
                    return title
        return None
    
    def _extract_body(self, html: str) -> Optional[str]:
        """Extract article body text."""
        # Method 1: og:description
        patterns = [
            r'<meta\s+property="og:description"\s+content="([^"]+)"',
            r'<meta\s+content="([^"]+)"\s+property="og:description"',
            r'<meta\s+name="description"\s+content="([^"]+)"',
            r'"description"\s*:\s*"([^"]{50,})"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                body = match.group(1).strip()
                if len(body) > 100:
                    return body
        
        # Method 2: Article paragraphs
        p_pattern = r'<p[^>]*>(.*?)</p>'
        paragraphs = re.findall(p_pattern, html, re.DOTALL)
        
        valid_paragraphs = []
        for p in paragraphs:
            text = re.sub(r'<[^>]+>', '', p).strip()
            if len(text) > 50 and not any(x in text.lower() for x in ["copyright", "rights reserved", "cookie", "javascript"]):
                valid_paragraphs.append(text)
        
        if valid_paragraphs:
            return ' '.join(valid_paragraphs[:4])
        
        return None
    
    def _extract_og_image(self, html: str) -> Optional[str]:
        """Extract OG image URL."""
        patterns = [
            r'<meta\s+property="og:image"\s+content="([^"]+)"',
            r'<meta\s+content="([^"]+)"\s+property="og:image"',
            r'"image"\s*:\s*"([^"]+)"',
            r'<meta\s+name="twitter:image"\s+content="([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                url = match.group(1)
                if url.startswith('http'):
                    return url
        return None
    
    def _extract_published_time(self, html: str) -> Optional[str]:
        """Extract published time."""
        patterns = [
            r'"datePublished"\s*:\s*"([^"]+)"',
            r'<time[^>]+datetime="([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
