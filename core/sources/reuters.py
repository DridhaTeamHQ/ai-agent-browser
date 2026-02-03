"""
Reuters News Scraper - Pure HTML scraping only.

NO BROWSER. Uses httpx to fetch HTML directly.
Extracts: title, body, og:image, published time.

Reuters has clean images without watermarks.
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
    source: str = "Reuters"


class ReutersScraper:
    """
    Reuters scraper using pure HTTP requests.
    
    NO BROWSER REQUIRED.
    Clean images without watermarks.
    """
    
    BASE_URL = "https://www.reuters.com"
    NEWS_URL = "https://www.reuters.com/world/"
    
    def __init__(self):
        self.logger = get_logger("reuters_scraper")
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
    
    def get_article_links(self, limit: int = 20) -> List[str]:
        """Get article links from Reuters World News page."""
        try:
            response = self.client.get(self.NEWS_URL)
            response.raise_for_status()
            html = response.text
            
            # Reuters article pattern
            patterns = [
                r'href="(/world/[^"]+/[a-z0-9-]+-[A-Z0-9]+/)"',
                r'href="(/world/[^"]+)"',
            ]
            
            all_matches = []
            for pattern in patterns:
                matches = re.findall(pattern, html)
                all_matches.extend(matches)
            
            # Filter and deduplicate
            unique_links = []
            seen = set()
            for link in all_matches:
                # Skip category pages and duplicates
                if link not in seen and link.count('/') >= 3:
                    seen.add(link)
                    unique_links.append(link)
                    if len(unique_links) >= limit:
                        break
            
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
                source="Reuters"
            )
            
            self.logger.info(f"✅ Scraped: {title[:50]}...")
            return article
            
        except Exception as e:
            self.logger.error(f"Failed to scrape {url}: {e}")
            return None
    
    def _extract_title(self, html: str) -> Optional[str]:
        """Extract article title using JSON-LD first."""
        # Method 1: JSON-LD headline (most reliable)
        patterns = [
            r'"headline"\s*:\s*"([^"]+)"',
            r'<meta\s+property="og:title"\s+content="([^"]+)"',
            r'<meta\s+content="([^"]+)"\s+property="og:title"',
            r'<title>([^<]+)</title>',
            r'<h1[^>]*>([^<]+)</h1>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up Reuters suffix
                title = re.sub(r'\s*[-|]\s*Reuters.*$', '', title)
                if len(title) > 15:
                    return title
        return None
    
    def _extract_body(self, html: str) -> Optional[str]:
        """Extract article body text."""
        # Method 1: JSON-LD description
        patterns = [
            r'"description"\s*:\s*"([^"]{50,})"',
            r'"articleBody"\s*:\s*"([^"]+)"',
            r'<meta\s+property="og:description"\s+content="([^"]+)"',
            r'<meta\s+content="([^"]+)"\s+property="og:description"',
            r'<meta\s+name="description"\s+content="([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                body = match.group(1).strip()
                body = body.replace('\\n', ' ').replace('\\u0027', "'")
                if len(body) > 100:
                    return body
        
        # Method 2: Article paragraphs
        p_pattern = r'<p[^>]*>(.*?)</p>'
        paragraphs = re.findall(p_pattern, html, re.DOTALL)
        
        valid_paragraphs = []
        for p in paragraphs:
            text = re.sub(r'<[^>]+>', '', p).strip()
            if len(text) > 50 and not any(x in text.lower() for x in ["copyright", "rights reserved", "browser", "javascript", "cookie"]):
                valid_paragraphs.append(text)
        
        if valid_paragraphs:
            body = ' '.join(valid_paragraphs[:4])
            return body
        
        return None
    
    def _extract_og_image(self, html: str) -> Optional[str]:
        """Extract OG image URL."""
        patterns = [
            r'"image"\s*:\s*\{[^}]*"url"\s*:\s*"([^"]+)"',
            r'"image"\s*:\s*"([^"]+)"',
            r'<meta\s+property="og:image"\s+content="([^"]+)"',
            r'<meta\s+content="([^"]+)"\s+property="og:image"',
            r'<meta\s+name="twitter:image"\s+content="([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                url = match.group(1)
                if url.startswith('http') and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    return url
                elif url.startswith('http'):
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
