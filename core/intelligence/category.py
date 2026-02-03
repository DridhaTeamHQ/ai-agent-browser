"""
Category Decider - Determines article category from text analysis.

No UI interaction. Pure text classification.
"""

import os
import json
from openai import OpenAI
from typing import Optional
from utils.logger import get_logger


class CategoryDecider:
    """
    Category classifier for news articles.
    
    Categories (CMS mapping):
    - National
    - International
    - Politics
    - Business
    - Sports
    - Entertainment
    - Technology
    - Health
    """
    
    VALID_CATEGORIES = [
        "National",
        "International", 
        "Politics",
        "Business",
        "Sports",
        "Entertainment",
        "Technology",
        "Health"
    ]
    
    def __init__(self):
        self.logger = get_logger("category")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def decide(self, title: str, body: str, source: str = "BBC") -> str:
        """
        Decide category based on article content.
        
        Returns: Category string (guaranteed to be valid)
        """
        prompt = f"""Classify this news article into exactly ONE category.

ARTICLE:
Title: {title}
Body: {body[:500]}
Source: {source}

CATEGORIES (pick exactly one):
- National (India domestic news)
- International (world news, foreign affairs)
- Politics (elections, government, policy)
- Business (economy, markets, companies)
- Sports (any sports news)
- Entertainment (movies, music, celebrities)
- Technology (tech companies, gadgets, AI)
- Health (medical, health policy, diseases)

RULES:
- Anything related to another country and NOT India = International
- If about India = National or Politics
- If about USA/UK/foreign = International
- If unclear = International

Return ONLY the category name, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=20
            )
            
            category = response.choices[0].message.content.strip()
            
            # Validate category
            for valid in self.VALID_CATEGORIES:
                if valid.lower() in category.lower():
                    self.logger.info(f"✅ Category: {valid}")
                    return valid
            
            # Default fallback
            self.logger.warning(f"Invalid category '{category}', defaulting to International")
            return "International"
            
        except Exception as e:
            self.logger.error(f"Category decision failed: {e}, defaulting to International")
            return "International"
