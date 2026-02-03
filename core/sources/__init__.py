"""
Sources package - Pure HTML scraping only.
"""

from .bbc import BBCScraper, Article
from .aljazeera import AlJazeeraScraper

__all__ = ["BBCScraper", "AlJazeeraScraper", "Article"]
