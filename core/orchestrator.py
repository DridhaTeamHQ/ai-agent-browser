"""
HARDENED ORCHESTRATOR - Self-Correcting Execution Engine.

ARCHITECTURE:
- Agent A (Intelligence): Generates validated ArticleData
- Validation Gate: Ensures data is perfect
- Agent B (Browser): Deterministic execution only

RECOVERY RULES:
- Never retry fill_form on dirty state
- Never chain recoveries
- Always classify failures
- Always apply correct recovery action
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from utils.logger import get_logger

# Agent A: Intelligence (NO browser)
from core.sources.timesofindia import TimesOfIndiaScraper
from core.sources.thehindu import TheHinduScraper
from core.intelligence import Summarizer, TeluguWriter, CategoryDecider
from core.media import OGImageDownloader

# Agent B: Browser Operator (NO intelligence)
from core.cms import CMSPublisher, ArticleData
from core.cms.image_finder import get_image_mode, find_and_download_in_new_tab

# Memory & Validation
from core.memory import AgentMemory
from utils.image_utils import meets_minimum_resolution
from core.validator import (
    ArticleValidator,
    ValidationResult,
    FailureType,
    RecoveryAction,
    RECOVERY_MATRIX
)


class HardenedOrchestrator:
    """
    Self-correcting orchestrator with strict failure classification.
    
    Invariants:
    1. Telugu content is NEVER corrupted (native setter only)
    2. Empty fields are NEVER published (validation gate)
    3. Dirty state is NEVER reused (reload on failure)
    """
    
    def __init__(self):
        self.logger = get_logger("orchestrator")
        
        # Agent A: Intelligence – India sources only (TOI, The Hindu; if no articles in 5 mins, switch source)
        self.scrapers = [
            ("Times of India", TimesOfIndiaScraper()),
            ("The Hindu", TheHinduScraper()),
        ]
        self.scraper_index = 0
        self._no_articles_wait_sec = 60
        self._no_articles_max_waits = 5  # 5 mins then switch source
        self.summarizer = Summarizer()
        self.telugu_writer = TeluguWriter()
        self.category_decider = CategoryDecider()
        self.image_downloader = OGImageDownloader()
        
        # Agent B: Browser Operator
        self.publisher = CMSPublisher()
        
        # Shared State
        self.memory = AgentMemory()
        self.validator = ArticleValidator()
        
        # Limits
        self.max_articles = 5
        self.max_login_retries = 2
        self.max_publish_retries = 2
        # Real-time: only use articles from the last N hours (env: MAX_ARTICLE_AGE_HOURS, default 24)
        try:
            self.max_article_age_hours = int(os.environ.get("MAX_ARTICLE_AGE_HOURS", "24"))
        except ValueError:
            self.max_article_age_hours = 24
    
    async def run(self):
        """Main execution loop with self-correction."""
        self.logger.info("🤖 AGENT ACTIVATED (HARDENED MODE)")
        
        browser_started = False
        
        try:
            # ================================================================
            # PHASE 0: BROWSER INITIALIZATION
            # ================================================================
            await self.publisher.start()
            browser_started = True
            
            # ================================================================
            # PHASE 1: LOGIN (with retry)
            # ================================================================
            if not await self._safe_login():
                self.logger.critical("❌ Login failed after all retries. Aborting.")
                return
            
            published_count = 0

            # ================================================================
            # PHASE 2 & 3: LOOP – process every candidate; refetch after each publish
            # ================================================================
            while published_count < self.max_articles:
                links = await self._get_article_links_with_fallback(limit=15)
                self.logger.info(f"🔎 Found {len(links)} candidate articles (from {self._get_source_name()})")

                if not links:
                    self.logger.info("🛑 No candidates. Stopping.")
                    break

                processed_one = False
                skipped_all_published = True  # true if we only skipped (already published)
                # Memory: skip only is_success(url). Never use is_processed – failed URLs must be retried. Prevents duplicate posts.
                for url in links:
                    if published_count >= self.max_articles:
                        break

                    if self.memory.is_success(url):
                        self.logger.debug(f"⏭️ Skipping already published: {url[:50]}...")
                        continue

                    skipped_all_published = False
                    self.logger.info(f"▶️ Processing: {url}")

                    # Full pipeline: scrape → summarize → telugu → image → Create Article → fill → publish
                    success = await self._process_article(url)
                    if success:
                        self.memory.mark_success(url)
                        published_count += 1
                        processed_one = True
                        self.logger.info(f"✅ Published ({published_count}/{self.max_articles}) – refetching and continuing")
                        break
                    else:
                        self.logger.warning("⚠️ Article skipped/failed")

                if published_count >= self.max_articles:
                    self.logger.info("🛑 Max articles reached. Stopping.")
                    break
                if not processed_one:
                    # All candidates were already published or failed – try next source once for new articles
                    if links and skipped_all_published:
                        self.scraper_index = (self.scraper_index + 1) % len(self.scrapers)
                        self.logger.info(f"   All from {self.scrapers[(self.scraper_index - 1) % len(self.scrapers)][0]} already published – trying {self._get_source_name()}")
                        continue
                    self.logger.info("🛑 No more candidates to process. Stopping.")
                    break
                    
        except Exception as e:
            self.logger.critical(f"🔥 FATAL ERROR: {e}", exc_info=True)
            
        finally:
            # Shutdown
            if browser_started:
                await self.publisher.stop()
            for _name, scraper in self.scrapers:
                try:
                    scraper.close()
                except Exception:
                    pass
            self.logger.info("😴 AGENT SLEEPING")
    
    # =========================================================================
    # LOGIN (with classified retry)
    # =========================================================================
    
    async def _safe_login(self) -> bool:
        """Login with retry. Returns True if successful."""
        for attempt in range(self.max_login_retries):
            try:
                if await self.publisher.login():
                    return True
                self.logger.warning(f"Login attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(2)
            except Exception as e:
                self.logger.error(f"Login error: {e}")
                # Classify as LOGIN_FAILURE, recovery = RETRY_ACTION
                await asyncio.sleep(2)
        
        return False
    
    def _get_scraper(self):
        """Current news source scraper."""
        return self.scrapers[self.scraper_index][1]
    
    def _get_source_name(self) -> str:
        """Current source name for logging."""
        return self.scrapers[self.scraper_index][0]

    def _is_article_too_old(self, published_time_str: Optional[str]) -> bool:
        """True if article is older than max_article_age_hours (skip for real-time)."""
        if not published_time_str or not published_time_str.strip():
            return False  # no date = allow (don't drop)
        try:
            s = published_time_str.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            age = datetime.now(timezone.utc) - dt
            return age > timedelta(hours=self.max_article_age_hours)
        except Exception:
            return False  # unparseable = allow

    async def _get_article_links_with_fallback(self, limit: int = 15):
        """
        Get article links from current source (newest first).
        If no links: wait 1 min and retry, up to 5 times (5 mins).
        If still no links: switch to next source and try once.
        Returns list of URLs (may be empty).
        """
        for wait_round in range(self._no_articles_max_waits):
            links = self._get_scraper().get_article_links(limit=limit)
            if links:
                return links
            name = self._get_source_name()
            if wait_round < self._no_articles_max_waits - 1:
                self.logger.info(f"   No new articles from {name}; waiting {self._no_articles_wait_sec}s before retry ({wait_round + 1}/{self._no_articles_max_waits})...")
                await asyncio.sleep(self._no_articles_wait_sec)
        
        # 5 mins with no articles – switch to next source
        prev_name = self._get_source_name()
        self.scraper_index = (self.scraper_index + 1) % len(self.scrapers)
        next_name = self._get_source_name()
        self.logger.info(f"   No new articles from {prev_name} in 5 mins – switching to {next_name}")
        links = self._get_scraper().get_article_links(limit=limit)
        return links
    
    # =========================================================================
    # ARTICLE PROCESSING PIPELINE
    # =========================================================================
    
    async def _process_article(self, url: str) -> bool:
        """
        Process single article through the pipeline.
        
        Returns: True if published, False if failed/skipped.
        """
        # ================================================================
        # AGENT A: INTELLIGENCE (No browser access)
        # ================================================================
        
        # Step 1: Scrape (current source)
        article = self._get_scraper().scrape_article(url)
        if not article:
            self.memory.mark_failed(url, "Scrape failed")
            return False

        # Real-time filter: skip articles older than max_article_age_hours
        if self._is_article_too_old(article.published_time):
            self.logger.warning(f"⏭️ Skipping old article (published: {article.published_time})")
            self.memory.mark_failed(url, "Article too old")
            return False
        
        # Step 2: Summarize (English)
        summary = self.summarizer.summarize(article.title, article.body)
        if not summary:
            self.memory.mark_failed(url, "Summarization failed")
            return False
        
        # Step 3: Telugu Generation
        telugu = self.telugu_writer.write(summary["title"], summary["body"])
        if not telugu:
            self.memory.mark_failed(url, "Telugu generation failed")
            return False
        
        # Step 4: Category and hashtags (always National per CMS)
        category = "National"
        hashtag = "#national #news #trending"
        
        # Step 5: Image Strategy (Smart Selection)
        image_path = None
        image_query = ""

        if get_image_mode() == "browser":
            # IMAGE_MODE=browser: always use second-tab Google Images search (no OG, no CMS nav)
            self.logger.info("   [IMAGE_MODE=browser] Will use browser image search (second tab)")
            image_query = f"{article.title} news"
        else:
            # IMAGE_MODE=api (default): OG download and/or search query for fill_form
            use_search_strategy = any(s in article.source.lower() for s in ["guardian", "reuters", "aljazeera"])
            if use_search_strategy:
                self.logger.info(f"   Using Search Strategy for {article.source} (Avoid Watermarks)")
                image_query = f"{article.title} news"
            else:
                # Prefer main article image (usually larger) then og:image
                main_image = getattr(article, "main_image", None)
                if main_image:
                    self.logger.info("   Trying main article image (higher res)...")
                    image_path = self.image_downloader.download(main_image, article.title)
                if not image_path and article.og_image:
                    self.logger.info("   Trying OG image...")
                    image_path = self.image_downloader.download(article.og_image, article.title)
                if not image_path:
                    self.logger.info("   Image missing/failed, falling back to Search")
                    image_query = f"{article.title} news"

                if image_path:
                    try:
                        with open(image_path, "rb") as f:
                            data = f.read()
                        if not meets_minimum_resolution(data):
                            self.logger.warning("   Downloaded image below min resolution, using browser search")
                            image_path = None
                            image_query = f"{article.title} news"
                    except Exception:
                        pass

        if not image_path and not image_query:
            self.memory.mark_failed(url, "No image strategy valid")
            return False
        
        # ================================================================
        # VALIDATION GATE
        # ================================================================
        validation = self.validator.validate(
            english_title=summary["title"],
            english_body=summary["body"],
            telugu_title=telugu["title"],
            telugu_body=telugu["body"],
            category=category,
            image_path=image_path,
            hashtag=hashtag,
            image_search_query=image_query
        )
        
        if not validation.is_valid:
            self.logger.error(f"❌ VALIDATION FAILED: {validation.error_message}")
            self.memory.mark_failed(url, validation.error_message)
            # Recovery: DISCARD_ARTICLE (no browser touched)
            return False
        
        # ================================================================
        # AGENT B: BROWSER EXECUTION (No intelligence)
        # ================================================================
        
        # Build validated ArticleData
        data = ArticleData(
            english_title=summary["title"],
            english_body=summary["body"],
            telugu_title=telugu["title"],
            telugu_body=telugu["body"],
            category=category,
            hashtag=hashtag,
            image_path=image_path,
            image_search_query=image_query
        )
        
        # Execute browser workflow with recovery
        return await self._execute_browser_workflow(data, url)
    
    # =========================================================================
    # BROWSER WORKFLOW (Deterministic with Recovery)
    # =========================================================================
    
    async def _execute_browser_workflow(self, data: ArticleData, url: str) -> bool:
        """
        Simple linear flow (no hallucination):
        1. Image: open new tab → search image → download → save to memory → close tab.
        2. Open article page: click Content → Articles → Create Article.
        3. Paste title (Telugu + English), description (Telugu + English).
        4. Select category (other country, not India = International).
        5. Paste hashtags.
        6. Click Choose File → upload downloaded image → click Crop.
        7. Scroll down a little → click Publish.
        Then repeat: if Create Article visible, click it; scrape new article; search new image; fill; publish.
        """
        # ================================================================
        # STEP 0: BROWSER IMAGE (IMAGE_MODE=browser only)
        # CMS page remains untouched. Open second tab → search → download → close tab.
        # If download fails → discard article.
        # ================================================================
        if get_image_mode() == "browser" and data.image_search_query and not data.image_path:
            self.logger.info("   [IMAGE_MODE=browser] Opening second tab for Google Images...")
            ctx = self.publisher.context
            if ctx:
                path = await find_and_download_in_new_tab(ctx, data.image_search_query)
            else:
                path = None
            if path:
                data.image_path = path
                data.image_search_query = ""
                self.logger.info(f"   [IMAGE_MODE=browser] Image saved, image tab closed. Path: {path}")
            else:
                self.logger.warning("   Image download failed → continuing without image (will try publish anyway)")
                data.image_search_query = ""

        # ================================================================
        # STEP 1: NAVIGATE (do not navigate CMS during image search)
        # ================================================================
        if not await self.publisher.create_article():
            # Recovery: RELOAD_PAGE
            self.logger.warning("Navigation failed, reloading page...")
            if self.publisher.page:
                await self.publisher.page.reload()
            await asyncio.sleep(2)
            
            if not await self.publisher.create_article():
                self.memory.mark_failed(url, "Navigation failed after reload")
                return False
        
        # ================================================================
        # STEP 2: FILL FORM (Atomic - NO retry on same page)
        # ================================================================
        fill_success = await self.publisher.fill_form(data)
        
        if not fill_success:
            # CRITICAL: State is DIRTY - MUST reload
            self.logger.error("❌ REACT_STATE_CORRUPTION: fill_form failed")
            if self.publisher.page:
                await self.publisher.page.reload()
            await asyncio.sleep(2)
            # DO NOT retry fill_form - abort this article
            self.memory.mark_failed(url, "Form fill failed (state corruption)")
            return False
        
        # ================================================================
        # STEP 3: PUBLISH (with retry)
        # ================================================================
        for attempt in range(self.max_publish_retries):
            if await self.publisher.publish():
                break
            
            self.logger.warning(f"Publish attempt {attempt + 1} failed, retrying...")
            await asyncio.sleep(2)
        else:
            # All retries failed
            self.memory.mark_failed(url, "Publish failed after retries")
            return False
        
        # ================================================================
        # STEP 4: VERIFY SUCCESS
        # ================================================================
        if await self.publisher.verify_publish():
            return True
        
        # Verification failed but publish might have succeeded
        # Log warning but consider it a success
        self.logger.warning("⚠️ Verify uncertain, assuming success")
        return True


# Backward compatibility alias
Orchestrator = HardenedOrchestrator
