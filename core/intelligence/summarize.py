"""
English Summarizer - Creates English summary from article text.

Uses OpenAI API. Pure text processing, no browser.
"""

import os
from openai import OpenAI
from typing import Optional, Dict
from utils.logger import get_logger


class Summarizer:
    """
    English article summarizer.
    
    Produces:
    - title: up to 80 chars (CMS limit)
    - body: up to 380 chars (CMS limit)
    """
    
    def __init__(self):
        self.logger = get_logger("summarizer")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def summarize(self, title: str, body: str) -> Optional[Dict[str, str]]:
        """
        Summarize article into structured English content.
        
        Returns: {"title": str, "body": str} or None
        """
        prompt = f"""You are a news editor. Create a concise English summary.

ARTICLE TITLE: {title}

ARTICLE TEXT: {body[:2000]}

OUTPUT FORMAT (JSON only):
{{
  "title": "up to 80 character headline",
  "body": "up to 380 character summary paragraph"
}}

CRITICAL RULES:
- Title: Clear, factual headline (max 80 chars)
- Body: 2-3 COMPLETE sentences (max 380 chars)
- NEVER cut off mid-sentence
- ALWAYS end with a complete thought
- No speculation or opinions
- Present tense for ongoing events
- Past tense for completed events

Return ONLY valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON
            import json
            # Handle markdown code blocks
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            
            # Validate
            if "title" not in result or "body" not in result:
                self.logger.error("Missing title or body in response")
                return None
            
            title = result["title"]
            body = result["body"]
            title_len = len(title)
            body_len = len(body)
            
            # Truncate to CMS limits (80 title, 380 content)
            if title_len > 80:
                title = title[:80]
                title_len = 80
                self.logger.info(f"   Truncated title to {title_len} chars")
            
            if body_len > 380:
                truncated = body[:380]
                last_period = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
                if last_period > 200:
                    body = body[:last_period + 1]
                else:
                    body = body[:377] + "..."
                body_len = len(body)
                self.logger.info(f"   Truncated body to {body_len} chars")
            
            result["title"] = title
            result["body"] = body
            
            self.logger.info(f"✅ Summary: title={title_len} chars, body={body_len} chars")
            return result
            
        except Exception as e:
            self.logger.error(f"Summarization failed: {e}")
            return None
