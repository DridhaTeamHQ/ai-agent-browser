"""
Al Jazeera News Scraper - Pure HTML scraping only.

NO BROWSER. Uses httpx to fetch HTML directly.
Extracts: title, body, og:image, published time.
"""

import httpx
import re
from typing import Optional, Dict, List
from dataclasses import dataclass
from utils.logger import get_logger


@dataclass
class Article:
    """Article data container."""
    url: str
    title: str
    body: str
    og_image: Optional[str]
    published_time: Optional[str]
    source: str = "AlJazeera"


class AlJazeeraScraper:
    """
    Al Jazeera scraper using pure HTTP requests.
    
    NO BROWSER REQUIRED.
    """
    
    BASE_URL = "https://www.aljazeera.com"
    NEWS_URL = "https://www.aljazeera.com/news"
    
    def __init__(self):
        self.logger = get_logger("aljazeera_scraper")
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    def get_article_links(self, limit: int = 20) -> List[str]:
        """Get article links from Al Jazeera News page."""
        try:
            response = self.client.get(self.NEWS_URL)
            response.raise_for_status()
            html = response.text
            
            # Extract article links - Al Jazeera uses /news/YYYY/M/DD/ format
            pattern = r'href="(/news/\d{4}/\d{1,2}/\d{1,2}/[^"]+)"'
            matches = re.findall(pattern, html)
            
            # Deduplicate and limit
            unique_links = list(dict.fromkeys(matches))[:limit]
            full_urls = [f"{self.BASE_URL}{link}" for link in unique_links]
            
            self.logger.info(f"Found {len(full_urls)} article links")
            return full_urls
            
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
            if not body or len(body) < 200:
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
                source="AlJazeera"
            )
            
            self.logger.info(f"✅ Scraped: {title[:50]}...")
            return article
            
        except Exception as e:
            self.logger.error(f"Failed to scrape {url}: {e}")
            return None
    
    def _extract_title(self, html: str) -> Optional[str]:
        """Extract article title."""
        # Method 1: JSON-LD (most reliable for Al Jazeera)
        json_ld_pattern = r'"headline"\s*:\s*"([^"]+)"'
        match = re.search(json_ld_pattern, html)
        if match:
            return match.group(1).strip()
        
        # Method 2: og:title meta tags (various formats)
        patterns = [
            r'<meta\s+property="og:title"\s+content="([^"]+)"',
            r'<meta\s+content="([^"]+)"\s+property="og:title"',
            r'property="og:title"[^>]*content="([^"]+)"',
            r'content="([^"]+)"[^>]*property="og:title"',
            r'"name"\s*:\s*"([^"]+)"',  # JSON-LD name field
            r'<title>([^<]+)</title>',
            r'<h1[^>]*>([^<]+)</h1>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up Al Jazeera suffix
                title = re.sub(r'\s*[-|]\s*Al Jazeera.*$', '', title)
                if len(title) > 20:  # Basic sanity check
                    return title
        return None
    
    def _extract_body(self, html: str) -> Optional[str]:
        """Extract article body text."""
        # Method 1: JSON-LD description/articleBody (most reliable)
        json_patterns = [
            r'"description"\s*:\s*"([^"]{100,})"',
            r'"articleBody"\s*:\s*"([^"]+)"',
        ]
        for pattern in json_patterns:
            match = re.search(pattern, html)
            if match:
                body = match.group(1).strip()
                # Unescape if needed
                body = body.replace('\\n', ' ').replace('\\u0027', "'")
                if len(body) > 100:
                    return body
        
        # Method 2: og:description meta tags
        desc_patterns = [
            r'<meta\s+property="og:description"\s+content="([^"]+)"',
            r'<meta\s+content="([^"]+)"\s+property="og:description"',
            r'property="og:description"[^>]*content="([^"]+)"',
            r'content="([^"]+)"[^>]*property="og:description"',
        ]
        for pattern in desc_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 100:
                    return desc
        
        # Method 3: Article paragraphs
        p_pattern = r'<p\b[^>]*>(.*?)</p>'
        paragraphs = re.findall(p_pattern, html, re.DOTALL)
        
        valid_paragraphs = []
        for p in paragraphs:
            text = re.sub(r'<[^>]+>', '', p).strip()
            if len(text) > 60 and not any(x in text.lower() for x in ["copyright", "rights reserved", "browser", "javascript"]):
                valid_paragraphs.append(text)
        
        if valid_paragraphs:
            body = ' '.join(valid_paragraphs[:5])
            return body
        
        return None
    
    def _extract_og_image(self, html: str) -> Optional[str]:
        """Extract OG image URL."""
        # Method 1: JSON-LD image
        json_pattern = r'"image"\s*:\s*\{\s*[^}]*"url"\s*:\s*"([^"]+)"'
        match = re.search(json_pattern, html)
        if match:
            url = match.group(1)
            if url.startswith('http'):
                return url
        
        # Simpler JSON-LD image
        json_pattern2 = r'"image"\s*:\s*"([^"]+)"'
        match = re.search(json_pattern2, html)
        if match:
            url = match.group(1)
            if url.startswith('http'):
                return url
        
        # Method 2: Meta tags
        patterns = [
            r'<meta\s+property="og:image"\s+content="([^"]+)"',
            r'<meta\s+content="([^"]+)"\s+property="og:image"',
            r'property="og:image"[^>]*content="([^"]+)"',
            r'content="([^"]+)"[^>]*property="og:image"',
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
            r'<time[^>]+datetime=["\']([^"\']+)["\']',
            r'"datePublished":\s*"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
