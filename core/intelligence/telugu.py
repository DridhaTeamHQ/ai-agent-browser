"""Telugu news writer with strict language-quality checks."""

from __future__ import annotations

import json
import os
import re
from typing import Dict, Optional

from openai import OpenAI

from utils.logger import get_logger


class TeluguWriter:
    """Generates Telugu newsroom copy from English summary."""

    ALLOWED_ENGLISH = {
        "us", "uk", "un", "ai", "pm", "cm", "bjp", "congress", "g20", "who", "isro", "nato",
        "iran", "israel", "india", "modi", "trump", "rahul", "gandhi", "bbc", "rbi", "mea", "icc",
    }

    LEXICAL_REPLACEMENTS = {
        "restraint": "\u0c38\u0c02\u0c2f\u0c2e\u0c28\u0c02",
        "dialogue": "\u0c38\u0c02\u0c2d\u0c3e\u0c37\u0c23",
        "tension": "\u0c09\u0c26\u0c4d\u0c30\u0c3f\u0c15\u0c4d\u0c24\u0c24",
        "impact": "\u0c2a\u0c4d\u0c30\u0c2d\u0c3e\u0c35\u0c02",
        "escalation": "\u0c24\u0c40\u0c35\u0c4d\u0c30\u0c24 \u0c2a\u0c46\u0c30\u0c41\u0c17\u0c41\u0c26\u0c32",
    }

    def __init__(self):
        self.logger = get_logger("telugu_writer")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def write(self, english_title: str, english_body: str, max_retries: int = 3) -> Optional[Dict[str, str]]:
        target_body_chars = 360
        min_body_chars = 345
        max_body_chars = 365

        prompt = f"""You are a senior Telugu newsroom editor.

Source English Title: {english_title}
Source English Body: {english_body}

Write Telugu output with this style:
- Strong factual hook in sentence 1.
- Clear, natural, publication-grade Telugu.
- Neutral tone, no sensational exaggeration.
- Include what happened, who is involved, and why it matters.
- Prefer short, punchy sentence rhythm used in mobile news cards.
- If source includes a quote, render it naturally in Telugu quotes.

Rules:
1) Title: Telugu headline up to 80 chars.
2) Body: 345-365 chars, ideally near 360, in 4-5 full sentences.
3) No English lexical words in the final Telugu copy.
4) Only unavoidable proper nouns/acronyms may remain in English.
5) Avoid bland filler transitions unless essential.
6) Keep facts faithful to source.

Return JSON only:
{{
  "title": "...",
  "body": "..."
}}
"""

        system_msg = (
            "You are a Telugu news editor. "
            "Body should be 345-365 characters and read like a professional newsroom write-up. "
            "Do not leave generic English words such as restraint, dialogue, tension, impact, escalation in output."
        )

        last_content = ""
        last_body = ""
        best_candidate: Optional[Dict[str, str]] = None
        best_score = -1.0

        for attempt in range(max_retries):
            try:
                messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
                if attempt > 0:
                    messages.append({"role": "assistant", "content": last_content})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Rewrite. Body must be {min_body_chars}-{max_body_chars} chars with 4-5 complete sentences. "
                                f"Previous body length: {len(last_body)}. "
                                "Remove all unnecessary English words and fix Telugu sentence flow. "
                                "Return JSON only."
                            ),
                        }
                    )

                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.3,
                    max_tokens=800,
                )

                last_content = (response.choices[0].message.content or "").strip()
                raw = last_content
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]

                result = json.loads(raw)
                title = self._sanitize_text((result.get("title") or "").strip())
                body = self._sanitize_text((result.get("body") or "").strip())
                last_body = body

                if self._has_disallowed_english(title) or self._has_disallowed_english(body):
                    purified = self._purify_telugu_copy(title, body, english_title, english_body)
                    if purified:
                        title = self._sanitize_text(purified.get("title", title))
                        body = self._sanitize_text(purified.get("body", body))

                if len(body) < min_body_chars:
                    self.logger.warning(f"Attempt {attempt + 1}: Body too short ({len(body)} chars), trying expansion...")
                    expanded = self._expand_telugu_body(body, title, english_body)
                    if expanded:
                        body = self._fit_body_length(self._sanitize_text(expanded), min_body_chars, max_body_chars)
                        self.logger.info(f"Expanded to {len(body)} chars")

                if len(title) > 80:
                    title = title[:80].rstrip(" ,.-")

                body = self._fit_body_length(body, min_body_chars, max_body_chars)

                title_pct = self._telugu_percentage(title)
                body_pct = self._telugu_percentage(body)
                body_eng_count, body_eng_ratio = self._english_token_stats(body)
                title_eng_count, _title_eng_ratio = self._english_token_stats(title)

                score = (body_pct * 0.6) + (title_pct * 0.25) + (max(0.0, 100.0 - (body_eng_ratio * 400.0)) * 0.15)
                if min_body_chars <= len(body) <= max_body_chars and score > best_score:
                    best_score = score
                    best_candidate = {"title": title, "body": body}

                if title_pct < 78 or body_pct < 78:
                    self.logger.warning(
                        f"Attempt {attempt + 1} rejected: low Telugu purity (title={title_pct:.0f}%, body={body_pct:.0f}%)"
                    )
                    continue

                if title_eng_count > 2 or body_eng_count > 4 or body_eng_ratio > 0.06:
                    self.logger.warning(
                        f"Attempt {attempt + 1} rejected: too many English words (title={title_eng_count}, body={body_eng_count}, ratio={body_eng_ratio:.2f})"
                    )
                    continue

                if self._has_disallowed_english(title) or self._has_disallowed_english(body):
                    self.logger.warning(f"Attempt {attempt + 1} rejected: disallowed English lexical words present")
                    continue

                if len(body) < min_body_chars or len(body) > max_body_chars:
                    continue
                if not body.endswith((".", "!", "?", "\u0964")):
                    self.logger.warning(f"Attempt {attempt + 1} rejected: body ends mid-sentence")
                    continue

                self.logger.info(f"Telugu generated: title={len(title)} body={len(body)}")
                return {"title": title, "body": body}

            except Exception as exc:
                self.logger.warning(f"Attempt {attempt + 1} failed: {exc}")
                continue

        if best_candidate:
            self.logger.warning("Strict checks exhausted; trying one final Telugu-only rewrite")
            forced = self._purify_telugu_copy(
                best_candidate.get("title", ""),
                best_candidate.get("body", ""),
                english_title,
                english_body,
            )
            if forced:
                title = self._sanitize_text((forced.get("title") or "").strip())
                body = self._sanitize_text((forced.get("body") or "").strip())
                if len(body) < min_body_chars:
                    expanded = self._expand_telugu_body(body, title, english_body)
                    if expanded:
                        body = self._fit_body_length(self._sanitize_text(expanded), min_body_chars, max_body_chars)
                else:
                    body = self._fit_body_length(body, min_body_chars, max_body_chars)

                title_pct = self._telugu_percentage(title)
                body_pct = self._telugu_percentage(body)
                body_eng_count, body_eng_ratio = self._english_token_stats(body)
                title_eng_count, _ = self._english_token_stats(title)

                if (
                    title_pct >= 78
                    and body_pct >= 78
                    and title_eng_count <= 2
                    and body_eng_count <= 4
                    and body_eng_ratio <= 0.06
                    and not self._has_disallowed_english(title)
                    and not self._has_disallowed_english(body)
                    and min_body_chars <= len(body) <= max_body_chars
                    and body.endswith((".", "!", "?", "\u0964"))
                ):
                    self.logger.info(f"Telugu generated (final rewrite): title={len(title)} body={len(body)}")
                    return {"title": title, "body": body}

            self.logger.error("Telugu generation failed strict validation after final rewrite")
            return None

        self.logger.error("Telugu generation failed all checks")
        return None

    def _expand_telugu_body(self, short_body: str, title: str, english_context: str) -> Optional[str]:
        if not short_body:
            return None
        if len(short_body) >= 345:
            return short_body

        try:
            safe_title = title[:80].replace('"', "'")
            expand_prompt = f"""Expand this Telugu paragraph to 345-365 characters, ideally near 360.
Keep the same facts and meaning. Write in natural Telugu newsroom style.

Title: {safe_title}
Current Paragraph: {short_body}
English Context: {english_context[:700]}

Return JSON only with keys: title, body.
"""
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": expand_prompt}],
                temperature=0.25,
                max_tokens=820,
            )
            raw = (response.choices[0].message.content or "").strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw)
            expanded = (parsed.get("body") or "").strip()
            return expanded if expanded else None
        except Exception as exc:
            self.logger.warning(f"Expand failed: {exc}")
            return None

    def _fit_body_length(self, body: str, min_chars: int, max_chars: int) -> str:
        text = self._sanitize_text(body)
        if len(text) < min_chars:
            text = self._pad_short_body(text, min_chars, max_chars)
        if len(text) <= max_chars:
            text = self._ensure_complete_ending(text, min_chars, max_chars)
            if len(text) < min_chars:
                text = self._pad_short_body(text, min_chars, max_chars)
            return self._ensure_complete_ending(text, min_chars, max_chars)

        clipped = text[:max_chars]
        stop = self._last_sentence_stop(clipped)
        if stop >= min_chars - 30:
            text = self._ensure_complete_ending(clipped[: stop + 1].rstrip(), min_chars, max_chars)
            if len(text) < min_chars:
                text = self._pad_short_body(text, min_chars, max_chars)
            return self._ensure_complete_ending(text, min_chars, max_chars)

        cut = clipped.rfind(" ")
        trimmed = (clipped[:cut] if cut > 0 else clipped).rstrip(" ,.-")
        text = self._ensure_complete_ending(trimmed, min_chars, max_chars)
        if len(text) < min_chars:
            text = self._pad_short_body(text, min_chars, max_chars)
        return self._ensure_complete_ending(text, min_chars, max_chars)

    def _last_sentence_stop(self, text: str) -> int:
        return max(text.rfind("."), text.rfind("!"), text.rfind("?"), text.rfind("\u0964"))

    def _ensure_complete_ending(self, body: str, min_chars: int, max_chars: int) -> str:
        text = self._sanitize_text(body).rstrip(" ,:-")
        if not text:
            return text

        if text.endswith((".", "!", "?", "\u0964")):
            return text

        stop = self._last_sentence_stop(text)
        if stop >= min_chars - 25:
            return text[: stop + 1].rstrip()

        closure = " వివరాలు ఇంకా వెలుగులోకి వస్తున్నాయి."
        if len(text) + len(closure) <= max_chars:
            return self._sanitize_text(text + closure)

        shorter_closure = " పరిస్థితిపై నిఘా కొనసాగుతోంది."
        if len(text) + len(shorter_closure) <= max_chars:
            return self._sanitize_text(text + shorter_closure)

        cut = text.rfind(" ")
        trimmed = (text[:cut] if cut > 0 else text).rstrip(" ,:-")
        if trimmed and not trimmed.endswith((".", "!", "?", "\u0964")):
            trimmed = trimmed + "."
        return trimmed
    def _pad_short_body(self, body: str, min_chars: int, max_chars: int) -> str:
        text = self._sanitize_text(body)
        if len(text) >= min_chars:
            return text

        tails = [
            " పరిణామాలపై నిఘా కొనసాగుతోంది.",
            " అధికారుల పర్యవేక్షణ కొనసాగుతోంది.",
            " తాజా వివరాలు ఇంకా వెలుగులోకి వస్తున్నాయి.",
            " దీనిపై స్పందనలు పెరుగుతున్నాయి.",
            " పరిస్థితి మార్పులపై దృష్టి నిలిచింది.",
            " సంబంధిత వర్గాలు అప్రమత్తంగా ఉన్నాయి.",
        ]
        idx = 0
        while len(text) < min_chars and idx < 12:
            tail = tails[idx % len(tails)]
            if len(text) + len(tail) > max_chars:
                break
            text = self._sanitize_text(text + tail)
            idx += 1
        return text

    def _sanitize_text(self, text: str) -> str:
        out = " ".join((text or "").split())
        out = out.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
        out = re.sub(r"\s+([,.;:!?\u0964])", r"\1", out)
        out = re.sub(r"\s+", " ", out)
        out = self._replace_english_lexical(out)
        return out

    def _replace_english_lexical(self, text: str) -> str:
        out = text
        for source, target in self.LEXICAL_REPLACEMENTS.items():
            out = re.sub(rf"\b{re.escape(source)}\b", target, out, flags=re.IGNORECASE)
        return out

    def _purify_telugu_copy(
        self,
        title: str,
        body: str,
        english_title: str,
        english_body: str,
    ) -> Optional[Dict[str, str]]:
        try:
            prompt = f"""Rewrite the Telugu copy into pure, natural Telugu.

English title: {english_title}
English context: {english_body[:700]}
Current Telugu title: {title}
Current Telugu body: {body}

Rules:
- Remove all unnecessary English words.
- Keep only essential acronyms/proper nouns (US, UK, UN, BJP, Congress, PM, CM).
- Keep facts unchanged.
- Keep title <= 80 chars and body 345-365 chars.
- Keep Telugu newsroom style, with natural punctuation.

Return JSON only: {{\"title\":\"...\",\"body\":\"...\"}}
"""
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=700,
            )
            raw = (response.choices[0].message.content or "").strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw)
            return {
                "title": (parsed.get("title") or title).strip(),
                "body": (parsed.get("body") or body).strip(),
            }
        except Exception as exc:
            self.logger.warning(f"Telugu purify pass failed: {exc}")
            return None

    def _has_disallowed_english(self, text: str) -> bool:
        tokens = re.findall(r"[a-zA-Z]{3,}", text)
        return any(token.lower() not in self.ALLOWED_ENGLISH for token in tokens)

    def _english_token_stats(self, text: str) -> tuple[int, float]:
        tokens = re.findall(r"[a-zA-Z]{2,}", text)
        if not tokens:
            return (0, 0.0)
        filtered = [t for t in tokens if t.lower() not in self.ALLOWED_ENGLISH]
        words = re.findall(r"\S+", text)
        ratio = len(filtered) / max(1, len(words))
        return (len(filtered), ratio)

    def _telugu_percentage(self, text: str) -> float:
        if not text:
            return 0.0
        telugu_chars = sum(1 for ch in text if "\u0C00" <= ch <= "\u0C7F")
        total_chars = sum(1 for ch in text if not ch.isspace())
        return (telugu_chars / total_chars * 100.0) if total_chars > 0 else 0.0







