"""
BBC News Scraper - Pure HTML scraping only.

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
    source: str = "BBC"


class BBCScraper:
    """
    BBC News scraper using pure HTTP requests.
    
    NO BROWSER REQUIRED.
    """
    
    BASE_URL = "https://www.bbc.com"
    NEWS_URL = "https://www.bbc.com/news"
    
    def __init__(self):
        self.logger = get_logger("bbc_scraper")
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    def get_article_links(self, limit: int = 20) -> List[str]:
        """Get article links from BBC News homepage."""
        try:
            response = self.client.get(self.NEWS_URL)
            response.raise_for_status()
            html = response.text
            
            # Extract article links
            pattern = r'href="(/news/articles/[^"]+)"'
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
                source="BBC"
            )
            
            self.logger.info(f"✅ Scraped: {title[:50]}...")
            return article
            
        except Exception as e:
            self.logger.error(f"Failed to scrape {url}: {e}")
            return None
    
    def _extract_title(self, html: str) -> Optional[str]:
        """Extract article title."""
        patterns = [
            r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
            r'<title>([^<]+)</title>',
            r'<h1[^>]*>([^<]+)</h1>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up BBC suffix
                title = re.sub(r'\s*[-|]\s*BBC.*$', '', title)
                return title
        return None
    
    def _extract_body(self, html: str) -> Optional[str]:
        """Extract article body text."""
        # Method 1: og:description
        desc_pattern = r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(desc_pattern, html, re.IGNORECASE)
        if match:
            desc = match.group(1).strip()
            if len(desc) > 100:
                self.logger.debug("Extracted body from og:description")
                return desc
        
        # Method 2: Generic Paragraphs (filtered)
        # Match standard <p> tags
        p_pattern = r'<p\b[^>]*>(.*?)</p>'
        paragraphs = re.findall(p_pattern, html, re.DOTALL)
        
        valid_paragraphs = []
        for p in paragraphs:
            # Clean HTML tags from content
            text = re.sub(r'<[^>]+>', '', p).strip()
            # Filter menu items/copyright/short text
            if len(text) > 60 and not any(x in text.lower() for x in ["copyright", "rights reserved", "browser", "please"]):
                valid_paragraphs.append(text)
        
        if valid_paragraphs:
            # Join up to 5 paragraphs
            body = ' '.join(valid_paragraphs[:6])
            self.logger.debug(f"Extracted body from {len(valid_paragraphs)} paragraphs")
            return body
            
        # Method 3: JSON-LD (Schema.org)
        json_ld_pattern = r'<script type="application/ld\+json">({.*?})</script>'
        scripts = re.findall(json_ld_pattern, html, re.DOTALL)
        for script in scripts:
            if '"articleBody"' in script:
                try:
                    # Simple string extraction to avoid full JSON parsing if possible, or use regex
                    body_match = re.search(r'"articleBody":\s*"([^"]+)"', script)
                    if body_match:
                        # Unescape unicode
                        return body_match.group(1).encode('utf-8').decode('unicode_escape')
                except Exception:
                    pass
        
        return None
    
    def _extract_og_image(self, html: str) -> Optional[str]:
        """Extract OG image URL."""
        patterns = [
            r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
            r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
            r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']',
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
        pattern = r'<time[^>]+datetime=["\']([^"\']+)["\']'
        match = re.search(pattern, html)
        if match:
            return match.group(1)
        return None
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
