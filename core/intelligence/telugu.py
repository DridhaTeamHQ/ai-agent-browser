"""
STRICT TELUGU GENERATOR (INTELLIGENCE AGENT)
Model: GPT-4o (MANDATORY)
Role: Senior Staff Editor

Enforces:
- Native Telugu phrasing
- 85% Unicode purity
- Zero tolerance for English words
- Strict character limits
"""

import os
import json
import re
from openai import OpenAI
from typing import Optional, Dict
from utils.logger import get_logger

class TeluguWriter:
    """
    Produces ORIGINAL Telugu content using GPT-4o.
    Refuses to output if quality standards are not met.
    """
    
    def __init__(self):
        self.logger = get_logger("telugu_writer")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def write(self, english_title: str, english_body: str, max_retries: int = 3) -> Optional[Dict[str, str]]:
        """
        Generate Telugu newsroom content.
        """
        prompt = f"""You are a senior editor at EENADU/SAKSHI (Telugu News).

        TRAINING EXAMPLES (Study this style carefully):
        
        HEADLINES (Short, Punchy, Dramatic):
        - "ఓయూకు పోయే దమ్ములేని దద్దమ్మ కేటీఆర్: సాయికుమార్"
        - "ప్రధాని తర్వాత అత్యంత కఠినమైన జాబ్ గంభీర్దే: శశి థరూర్"
        - "నేను లవ్ లో ఉన్నాను: జాతి రత్నాలు హీరోయిన్"
        - "నిర్మోహమాటంగా చెప్పేసెయ్: ఐశ్వర్యరాయ్"
        - "బాలుడిపై శునకం దాడి... వీడియో"
        - "భారీ అలెర్ట్... నాలుగు రోజులూ వర్షాలు"
        - "WHO నుంచి వైదొలిగిన అమెరికా"
        - "అమెజాన్ ఉద్యోగులకు భారీ షాక్"
        - "'బైబై.. టాటా.. గుడ్బై'"
        
        BODY EXAMPLES (Concise, Factual, Active Voice):
        - "ట్రంప్ ప్రభుత్వం తాజాగా సంచలన నిర్ణయం తీసుకుంది. ప్రపంచ ఆరోగ్య సంస్థ నుంచి తాము వైదొలుగుతున్నట్లు ప్రకటించింది."
        - "అమెజాన్ సంస్థ మరోసారి ఉద్యోగాల కోతకు సిద్ధమవుతోంది. ఈసారి 15 వేల మంది ఉద్యోగులను తొలగించేందుకు ఏర్పాట్లు చేస్తోంది."
        - "హైదరాబాద్ లోని సూరారంలో దారుణం చోటుచేసుకుంది. వీధిలో ఆడుకుంటున్న ఐదేళ్ల బాలుడిపై శునకం దాడి చేసింది."
        
        YOUR TASK: Write Telugu news based on this English source.
        
        SOURCE:
        Title: {english_title}
        Body: {english_body}
        
        STRICT RULES:
        1. HEADLINE: Short, dramatic, up to 80 chars. Use colons, ellipses, quotes for impact.
        2. BODY: 2-3 short sentences, up to 380 chars. Start with main event. Add details. End with impact/next steps.
        3. NO ENGLISH WORDS except proper nouns (names, places).
        4. STYLE: Active voice, present tense for ongoing, past tense for completed.
        5. TONE: Eenadu/Sakshi local news style - punchy, dramatic, engaging.
        
        OUTPUT FORMAT (JSON only):
        {{
          "title": "up to 80 char headline",
          "body": "up to 380 char summary"
        }}
        """

        for attempt in range(max_retries):
            try:
                # COST CONTROL: Telugu uses GPT-4o
                response = self.client.chat.completions.create(
                    model="gpt-4o",  # STRICT: 4o ONLY
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5, 
                    max_tokens=600
                )
                
                content = response.choices[0].message.content.strip()
                
                # Parse JSON
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                
                result = json.loads(content)
                title = result.get("title", "")
                body = result.get("body", "")
                
                # ---------------------------------------------------------
                # VALIDATION GATE
                # ---------------------------------------------------------
                
                # 1. Unicode Purity (Hard 85%)
                t_pct_title = self._telugu_percentage(title)
                t_pct_body = self._telugu_percentage(body)
                
                if t_pct_title < 85 or t_pct_body < 85:
                    self.logger.warning(f"Attempt {attempt+1} Rejected: Low Purity (T={t_pct_title:.0f}%, B={t_pct_body:.0f}%)")
                    continue
                
                # 2. English Infection Check
                if self._has_english_words(body):
                    self.logger.warning(f"Attempt {attempt+1} Rejected: Contains English words")
                    continue
                
                # 3. Truncation (CMS: 80 title, 380 content)
                if len(title) > 80: title = title[:80]
                if len(body) > 380: body = body[:377] + "..."
                
                self.logger.info(f"✅ Telugu Generated (GPT-4o): T={len(title)} B={len(body)}")
                
                return {
                    "title": title,
                    "body": body
                }
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt+1} failed: {e}")
                continue
        
        self.logger.error("❌ Telugu generation failed all strict checks")
        return None

    def _telugu_percentage(self, text: str) -> float:
        if not text: return 0.0
        telugu_chars = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
        total_chars = sum(1 for c in text if not c.isspace())
        return (telugu_chars / total_chars * 100) if total_chars > 0 else 0.0

    def _has_english_words(self, text: str) -> bool:
        """Reject if contains significant ASCII letters (>2 chars length words)."""
        english_words = re.findall(r'[a-zA-Z]{3,}', text)
        return len(english_words) > 0
