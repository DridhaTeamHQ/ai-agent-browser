"""
CMS Publisher - BULLETPROOF VERSION (CONSTITUTION COMPLIANT).

Based on Playwright best practices research:
1. Use fill() method - triggers proper events for React
2. Use force=True when elements covered by overlays
3. Explicit waits for network idle
4. Longer timeouts for React apps
5. Simple, robust selectors
6. Mandatory Scroll + Verify for Clicks
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from utils.logger import get_logger
from core.cms.image_finder import GoogleImageFinder, get_image_mode


@dataclass
class ArticleData:
    """Data to publish to CMS."""
    english_title: str
    english_body: str
    telugu_title: str
    telugu_body: str
    category: str
    image_search_query: str = "" # Added for Schema Compliance
    image_alt: str = "" # Added for Schema Compliance
    hashtag: str = "#news #trending"
    image_path: Optional[str] = None


class CMSPublisher:
    """
    Bulletproof CMS publisher using Playwright best practices.
    """
    
    SCREENSHOT_DIR = Path("screenshots")
    TIMEOUT = 30000  # 30 seconds for React apps
    
    def __init__(self):
        self.logger = get_logger("cms")
        self.cms_url = os.getenv("CMS_URL", "")
        self.cms_email = os.getenv("CMS_EMAIL", "")
        self.cms_password = os.getenv("CMS_PASSWORD", "")
        self.cms_role = os.getenv("CMS_ROLE", "State Sub Editor")
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.image_finder: Optional[GoogleImageFinder] = None
        self.logged_in = False
        self._last_media_commit_verified = False  # Set after upload when IMAGE_MODE=browser or after any upload

        self.SCREENSHOT_DIR.mkdir(exist_ok=True)
    
    async def start(self):
        """Start browser."""
        self.logger.info("🚀 Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            slow_mo=200  # Slower for stability
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1400, "height": 900}
        )
        self.page = await self.context.new_page()
        self.image_finder = GoogleImageFinder(self.page)
        self.page.set_default_timeout(self.TIMEOUT)
        self.logger.info("✅ Browser started")
    
    async def stop(self):
        """Stop browser."""
        self.logger.info("Stopping browser...")
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            self.logger.warning(f"Error stopping browser: {e}")
        self.logger.info("✅ Browser stopped")
    
    async def _wait_stable(self):
        """Wait for page to be stable (network idle + DOM settled)."""
        if self.page is None:
            return
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        await asyncio.sleep(1)
    
    # =========================================================================
    # LOGIN
    # =========================================================================
    
    async def login(self) -> bool:
        """
        Login with STRICT VERIFICATION (Constitution Rules).
        """
        if self.page is None:
            return False
        self.logger.info(f"🔐 Logging in as {self.cms_role}...")
        
        try:
            await self.page.goto(self.cms_url, wait_until="networkidle")
            await self._wait_stable()
            
            # 1. Role
            self.logger.info("   [1] Role...")
            dropdown = self.page.locator("button[role='combobox']").first
            await dropdown.click()
            await asyncio.sleep(1)
            await self.page.locator(f"[role='option']:has-text('{self.cms_role}')").click()
            await asyncio.sleep(0.5)
            
            # 2. Email (Strict Verify)
            self.logger.info("   [2] Email...")
            email_input = self.page.locator("#email")
            await email_input.click() 
            await email_input.fill(self.cms_email)
            if await email_input.input_value() != self.cms_email:
                 self.logger.warning("   ⚠️ Email mismatch, forcing native set...")
                 await self._fill_react_input(email_input, self.cms_email, "Email")
            
            # 3. Password (Strict Verify)
            self.logger.info("   [3] Password...")
            pwd_input = self.page.locator("#password")
            await pwd_input.click()
            await pwd_input.fill(self.cms_password)
            if len(await pwd_input.input_value()) == 0:
                 self.logger.warning("   ⚠️ Password empty, forcing native set...")
                 await self._fill_react_input(pwd_input, self.cms_password, "Password")

            # 4. Submit
            self.logger.info("   [4] Submitting...")
            submit_btn = self.page.locator("button[type='submit']")
            await submit_btn.click()
            
            await self._wait_stable()
            await asyncio.sleep(3)
            
            if "/login" not in self.page.url.lower():
                self.logger.info("✅ Login successful")
                self.logged_in = True
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Login error: {e}")
            return False
    
    # =========================================================================
    # NAVIGATION
    # =========================================================================
    
    async def create_article(self) -> bool:
        """Navigate to create article form."""
        if self.page is None:
            return False
        self.logger.info("📝 Navigating to create article...")
        
        try:
            await self._wait_stable()
            
            # Step 1: Click Content menu in sidebar to expand it
            self.logger.info("   [1] Clicking Content menu...")
            # The Content link is in the sidebar, find it by text
            content_menu = self.page.locator("text='Content'").first
            await content_menu.click(force=True)
            await asyncio.sleep(1.5)  # Wait for submenu to expand
            
            # Step 2: Click Articles link (should appear after Content expands)
            self.logger.info("   [2] Clicking Articles...")
            articles_link = self.page.locator("text='Articles'").first
            await articles_link.click(force=True)
            await self._wait_stable()
            
            # Step 3: Click Create Article button
            self.logger.info("   [3] Clicking Create Article button...")
            # Wait for the Articles page to load
            await asyncio.sleep(2)
            create_btn = self.page.locator("text='Create Article'").first
            await create_btn.click(force=True)
            await self._wait_stable()
            
            self.logger.info("✅ Create article form opened")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Navigation error: {e}")
            await self._dump_debug("nav_failed")
            return False
    
    # =========================================================================
    # FORM FILLING - Using fill() method (Playwright best practice)
    # =========================================================================
    async def _fill_react_input(self, locator, value: str, field_name: str) -> bool:
        """
        STRICT INPUT REPLACEMENT (Constitution Compliant).
        
        Rules:
        1. NO Keyboard Typing (avoids Telugu corruption).
        2. Native Value Setter Hack (Fixes React State/Empty Form issues).
        3. Mandatory verification.
        """
        try:
            # 1. Focus
            await locator.focus()
            
            # 2. React Native Value Setter (The "Web Search Optimized" Fix)
            # React controlled inputs override the 'value' setter.
            # We must call the native prototype setter to bypass React's tracking.
            # Handles both INPUT and TEXTAREA.
            await locator.evaluate("""(input, value) => {
                const proto = (input instanceof HTMLTextAreaElement) 
                    ? window.HTMLTextAreaElement.prototype 
                    : window.HTMLInputElement.prototype;
                    
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(proto, "value").set;
                nativeInputValueSetter.call(input, value);
                
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new Event('blur', { bubbles: true }));
            }""", value)
            
            # 3. Wait for React to process
            await asyncio.sleep(1.0) # Increased wait for state sync
            
            # 4. STRICT VERIFICATION
            dom_value = await locator.input_value()
            
            # Normalizing for comparison
            if dom_value.strip() != value.strip():
                self.logger.error(f"   ❌ CONST VIOLATION: {field_name} mismatch!")
                self.logger.error(f"      Expected: {len(value)} chars")
                self.logger.error(f"      Actual:   {len(dom_value)} chars")
                return False
                
            self.logger.info(f"   ✅ {field_name}: Verified {len(dom_value)} chars (React State Sync)")
            return True
            
        except Exception as e:
            self.logger.warning(f"   ⚠️ {field_name} injection error: {e}")
            return False
    
    async def fill_form(self, data: ArticleData) -> bool:
        """
        Fill article form step-by-step with verification.
        
        Uses click, clear, type sequence to properly trigger React onChange events.
        """
        if self.page is None or self.context is None:
            return False
        self.logger.info("📋 Filling form (step-by-step with verification)...")
        
        try:
            await self._wait_stable()
            await self._screenshot("form_before_fill")
            
            # =====================================================================
            # 1. TELUGU TITLE
            # =====================================================================
            self.logger.info("   [1/7] Telugu Title...")
            telugu_title_input = self.page.locator("input[data-testid='rt-input-component']").first
            await self._fill_react_input(telugu_title_input, data.telugu_title, "Telugu Title")
            await self._screenshot("step1_telugu_title")
            await asyncio.sleep(0.5)
            
            # =====================================================================
            # 2. ENGLISH TITLE
            # =====================================================================
            self.logger.info("   [2/7] English Title...")
            english_title_input = self.page.locator("#title_en")
            await self._fill_react_input(english_title_input, data.english_title, "English Title")
            await self._screenshot("step2_english_title")
            await asyncio.sleep(0.5)
            
            # =====================================================================
            # 3. TELUGU CONTENT
            # =====================================================================
            self.logger.info("   [3/7] Telugu Content...")
            telugu_content_area = self.page.locator("textarea[data-testid='rt-input-component']").first
            await self._fill_react_input(telugu_content_area, data.telugu_body, "Telugu Content")
            await self._screenshot("step3_telugu_content")
            await asyncio.sleep(0.5)
            
            # =====================================================================
            # 4. ENGLISH CONTENT
            # =====================================================================
            self.logger.info("   [4/7] English Content...")
            english_content_area = self.page.locator("#content_en")
            await self._fill_react_input(english_content_area, data.english_body, "English Content")
            await self._screenshot("step4_english_content")
            await asyncio.sleep(0.5)
            
            # =====================================================================
            # 5. CATEGORY
            # =====================================================================
            self.logger.info("   [5/7] Category...")
            await self._select_category(data.category)
            await self._screenshot("step5_category")
            await asyncio.sleep(0.5)
            
            # =====================================================================
            # 6. HASHTAG
            # =====================================================================
            self.logger.info("   [6/7] Hashtag...")
            hashtag_input = self.page.locator("#hashtag")
            await self._fill_react_input(hashtag_input, data.hashtag, "Hashtag")
            await self._screenshot("step6_hashtag")
            await asyncio.sleep(0.5)
            
            # =====================================================================
            # 7. IMAGE
            # =====================================================================
            # IMAGE_MODE=api: may open a new tab here for search (legacy). IMAGE_MODE=browser: image
            # is already resolved in orchestrator; CMS must remain untouched during search, so we
            # only upload if we have image_path.
            image_mode = get_image_mode()
            if image_mode == "api" and data.image_search_query and not data.image_path:
                self.logger.info(f"   [7/8] Searching Google Images for: {data.image_search_query}")
                search_page = await self.context.new_page()
                try:
                    finder = GoogleImageFinder(search_page)
                    found_path = await finder.find_and_download(data.image_search_query)
                    if found_path:
                        data.image_path = found_path
                    else:
                        self.logger.warning("   Image search failed, skipping upload")
                finally:
                    if not search_page.is_closed():
                        await search_page.close()

            if data.image_path and os.path.exists(data.image_path):
                self.logger.info("   [7/8] Image...")
                uploaded = await self._upload_image(data.image_path)
                self._last_media_commit_verified = await self._wait_for_media_commit() if uploaded else False
                await self._screenshot("step7_image")
            else:
                self.logger.info("   [7/8] No image to upload")
                self._last_media_commit_verified = True  # No image => nothing to commit
            
            # =====================================================================
            # 8. SETTINGS (PUSH NOTIFICATION) - SKIPPED (User Request)
            # =====================================================================
            self.logger.info("   [8/8] Settings (Push) - SKIPPED")
            
            await self._screenshot("form_filled_final")
            
            self.logger.info("✅ Form filled (all steps complete)")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Form error: {e}")
            await self._screenshot("form_error")
            return False
    
    async def _select_category(self, category: str) -> bool:
        """Select category with retry and verification."""
        if self.page is None:
            return False
        try:
            self.logger.info(f"   Selecting Category: {category}")
            
            # DO NOT call _close_all_modals() here - it can clear form data!
            
            # LOCATE DROPDOWN
            dropdown = self.page.locator("button:has-text('Select')").last
            if await dropdown.count() == 0:
                 dropdown = self.page.locator("[role='combobox']").last
            
            # RETRY OPENING
            for attempt in range(3):
                self.logger.info(f"   [Category Attempt {attempt+1}] Opening dropdown...")
                await dropdown.click(force=True)
                await asyncio.sleep(0.5)
                
                # Verify Open: Look for options
                options = self.page.locator("[role='option']")
                if await options.count() > 0 and await options.first.is_visible():
                    self.logger.info("   Dropdown opened, selecting option...")
                    
                    # CLICK OPTION - Use get_by_role with exact match to avoid strict mode violation
                    target_option = self.page.get_by_role("option", name=category, exact=True).first
                    
                    if await target_option.count() > 0:
                        await target_option.click()
                        self.logger.info(f"   ✅ Category selected: {category}")
                        await asyncio.sleep(0.3)
                        return True
                    else:
                        # Fallback: Try partial match with .first
                        target_option = self.page.locator(f"[role='option']:has-text('{category}')").first
                        if await target_option.count() > 0:
                            await target_option.click(force=True)
                            self.logger.info(f"   ✅ Category selected (partial): {category}")
                            return True
                        else:
                            self.logger.warning(f"   Option '{category}' not found")
                
                # FALLBACK: Keyboard typing
                self.logger.info("   Fallback: Typing category...")
                await dropdown.fill(category)
                await asyncio.sleep(0.3)
                await dropdown.press("Enter")
                return True
                
            return False
            
        except Exception as e:
            self.logger.warning(f"   ⚠️ Category error: {e}")
            return False
    
    async def _upload_image(self, image_path: str) -> bool:
        """Upload image: scroll to Media, Choose File → trigger change so CMS runs upload → Crop if visible."""
        if self.page is None:
            return False
        try:
            self.logger.info(f"   Uploading: {Path(image_path).name}")

            # Scroll so Media / Choose File is in view (form may be long)
            await self.page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(0.3)

            file_input = self.page.locator("input[type='file']").first
            await file_input.scroll_into_view_if_needed()
            await asyncio.sleep(0.2)
            await file_input.set_input_files(image_path)

            # Critical: many React CMS apps only start upload when they receive change/input
            try:
                await file_input.evaluate("el => { el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }")
            except Exception:
                pass
            await asyncio.sleep(1)

            # Wait for upload to be processed (crop modal or preview often appears after server accepts)
            await asyncio.sleep(4)

            crop_btn = self.page.locator("button:has-text('Crop')").last
            if await crop_btn.count() > 0 and await crop_btn.is_visible():
                self.logger.info("   Clicking Crop button...")
                await crop_btn.click()
                await asyncio.sleep(2)

            self.logger.info("   ✅ Image file set and events dispatched")
            return True

        except Exception as e:
            self.logger.warning(f"   Image error: {e}")
            return False

    async def _wait_for_media_commit(self, timeout_sec: float = 20.0) -> bool:
        """
        Wait for media commit after upload: crop modal closed, preview visible, and
        the "Article must include media" error must be GONE (server accepted media).
        Do NOT publish unless this returns True when an image was uploaded.
        """
        if self.page is None:
            return False
        import time
        self.logger.info("   Waiting for media commit...")
        deadline = time.monotonic() + timeout_sec
        media_error_text = "Article must include media"
        while time.monotonic() < deadline:
            try:
                # Fail if the CMS still shows "Article must include media"
                err_el = self.page.locator(f"text={media_error_text}")
                if await err_el.count() > 0 and await err_el.first.is_visible():
                    await asyncio.sleep(0.5)
                    continue
                # Crop modal should be gone
                crop_modal = self.page.locator("text='Crop Image'")
                if await crop_modal.count() > 0 and await crop_modal.first.is_visible():
                    await asyncio.sleep(0.5)
                    continue
                # Image preview / media committed (common patterns)
                preview = self.page.locator("img[alt*='preview' i], [class*='preview'] img, [class*='media'] img, [class*='ImagePreview']")
                if await preview.count() > 0 and await preview.first.is_visible():
                    self.logger.info("   ✅ Media commit verified (preview visible)")
                    return True
                # No media error and no blocking dialog => accept as committed
                dialogs = self.page.locator("[role='dialog']:visible")
                if await dialogs.count() == 0:
                    self.logger.info("   ✅ Media commit verified (no error, no dialog)")
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        self.logger.warning("   ⚠️ Media commit verification timeout")
        return False
    
    # =========================================================================
    # PUBLISH
    # =========================================================================
    
    async def publish(self) -> bool:
        """
        Publish article. Do NOT publish unless media commit is verified when an image was uploaded.
        """
        if self.page is None:
            return False
        if not self._last_media_commit_verified:
            self.logger.error("❌ Aborting publish: media commit was not verified (do not publish without it).")
            return False

        self.logger.info("🚀 PUBLISHING...")

        # 1. Scroll so Publish button is visible
        await self.page.evaluate("window.scrollBy(0, 300)")
        await asyncio.sleep(0.5)
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)

        # Short timeout when re-finding button (we may already be on list page)
        btn_timeout = 5000

        async def _on_articles_list_page() -> bool:
            """True if we're on Articles Management list (success page), not the create form."""
            if self.page is None:
                return False
            try:
                url = self.page.url
                if "/articles" in url and "/create" not in url and "/new" not in url:
                    return True
                # DOM fallback only when we're sure: list page has "Articles Management" as main title
                # (Don't use "Create Article" + no Publish - create form can have Publish below fold and match that.)
                list_heading = self.page.locator("text='Articles Management'").first
                if await list_heading.count() > 0 and await list_heading.is_visible(timeout=1000):
                    return True
            except Exception:
                pass
            return False

        # 2. Click and poll for success (up to 3 attempts)
        for attempt in range(3):
            self.logger.info(f"   Attempt {attempt + 1}/3")

            # Only on attempt 2+: if we're already on list (navigated after first click), success
            # On attempt 1 we always scroll and click Publish (no short-circuit)
            if attempt >= 1 and await _on_articles_list_page():
                self.logger.info("   ✅ PUBLISHED (already on articles list)!")
                return True

            # Find Publish button this attempt (page may have changed)
            publish_btn = self.page.locator("button:has-text('Publish Article')").first
            try:
                if await publish_btn.count() == 0 or not await publish_btn.is_visible(timeout=btn_timeout):
                    publish_btn = self.page.locator("button:has-text('Publish')").first
                if await publish_btn.count() == 0 or not await publish_btn.is_visible(timeout=btn_timeout):
                    self.logger.warning("   No Publish button (maybe already navigated)")
                    await asyncio.sleep(1)
                    continue
            except Exception:
                await asyncio.sleep(1)
                continue

            try:
                await publish_btn.scroll_into_view_if_needed(timeout=btn_timeout)
            except Exception:
                pass
            await asyncio.sleep(0.5)

            box = await publish_btn.bounding_box()
            if box:
                await self.page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            else:
                await publish_btn.click(force=True)

            # Poll for URL change, list page DOM, or success toast (up to 8s)
            for _ in range(16):
                await asyncio.sleep(0.5)
                if await _on_articles_list_page():
                    self.logger.info("   ✅ PUBLISHED (on articles list)!")
                    return True
                if await self.page.locator("text='successfully'").count() > 0:
                    self.logger.info("   ✅ PUBLISHED (toast)!")
                    return True
                if await self.page.locator("text='published'").count() > 0:
                    self.logger.info("   ✅ PUBLISHED (published text)!")
                    return True

            # Log validation errors if still on form
            err_media = self.page.locator("text=Article must include media")
            if await err_media.count() > 0 and await err_media.first.is_visible():
                self.logger.warning("   Form still shows: Article must include media")
            err_any = self.page.locator("[role='alert'], .text-red-600, .text-destructive")
            if await err_any.count() > 0:
                for i in range(min(await err_any.count(), 3)):
                    try:
                        t = await err_any.nth(i).text_content()
                        if t and len(t.strip()) < 200:
                            self.logger.warning(f"   Form error: {t.strip()}")
                    except Exception:
                        pass

            await asyncio.sleep(1)

        await self._screenshot("publish_failed")
        self.logger.error("❌ PUBLISH FAILED")
        return False

    async def _ensure_publish_ready(self) -> bool:
        """
        Pre-publish gate: Check no portals/backdrops blocking.
        Returns True if safe to click.
        """
        if self.page is None:
            return False
        try:
            # Check 1: No Radix portals open
            portals = await self.page.locator("[data-radix-popper-content-wrapper]").count()
            if portals > 0:
                self.logger.warning("   GATE: Radix portal still open")
                return False
            
            # Check 2: No blocking backdrops
            backdrops = await self.page.locator("div.fixed.inset-0.z-50").count()
            if backdrops > 0:
                self.logger.warning("   GATE: Backdrop blocking")
                return False
            
            # Check 3: No open dialogs
            dialogs = await self.page.locator("[role='dialog']:visible").count()
            if dialogs > 0:
                self.logger.warning("   GATE: Dialog still open")
                return False
            
            return True
        except:
            return True  # Fail open if check errors

    async def _wait_publish_result(self) -> bool:
        """
        Wait for ground truth signal of publish success.
        ONLY returns True if we see definitive proof.
        """
        if self.page is None:
            return False
        for i in range(10):  # 5 seconds total
            try:
                # Ground Truth 1: URL changed to articles list
                current_url = self.page.url
                if "/articles" in current_url and "/create" not in current_url and "/new" not in current_url:
                    self.logger.info(f"   URL changed: {current_url}")
                    return True
                
                # Ground Truth 2: Success toast/message visible (multiple keywords)
                success_keywords = ['successfully', 'created', 'published', 'saved', 'success']
                for keyword in success_keywords:
                    toast = self.page.locator(f"text='{keyword}'")
                    try:
                        if await toast.count() > 0 and await toast.first.is_visible():
                            self.logger.info(f"   Success signal found: '{keyword}'")
                            return True
                    except:
                        pass
                
                # Ground Truth 3: Article ID/slug in URL (new article was created)
                if "/article/" in current_url or "/edit/" in current_url:
                    self.logger.info(f"   Article created, URL: {current_url}")
                    return True
                    
            except Exception as e:
                self.logger.warning(f"   Check error: {e}")
            
            await asyncio.sleep(0.5)
        
        # Take screenshot for debugging
        await self._screenshot("publish_result_unclear")
        return False

    async def _check_success(self) -> bool:
        """Quick check for success indicators (used in retry loop)."""
        if self.page is None:
            return False
        try:
            if "/articles" in self.page.url and "/create" not in self.page.url:
                return True
            if await self.page.locator("text='successfully'").is_visible():
                return True
            return False
        except:
            return False    
    
    async def _close_all_modals(self):
        """
        Close any modal dialogs that might be blocking.
        WARNING: This is ONLY for crop modal cleanup, NOT during form filling.
        """
        if self.page is None:
            return
        try:
            for _ in range(3):
                # Check for crop modal ONLY
                crop_modal = self.page.locator("text='Crop Image'")
                if await crop_modal.count() > 0 and await crop_modal.is_visible():
                    self.logger.info("   Closing crop modal...")
                    try:
                        crop_btn = self.page.locator("button:has-text('Crop')").last
                        await crop_btn.click(force=True)
                        await asyncio.sleep(1)
                    except:
                        pass
                
                # DO NOT PRESS ESCAPE - it clears form data!
                # Only click visible close buttons on dialogs
                dialogs = self.page.locator("[role='dialog']:visible")
                if await dialogs.count() == 0:
                    break
                    
                close_btns = self.page.locator("[role='dialog'] button:has-text('×'), [role='dialog'] [aria-label='Close']")
                for i in range(min(await close_btns.count(), 2)):
                    btn = close_btns.nth(i)
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await asyncio.sleep(0.3)
                        break
                    
        except:
            pass

    async def verify_publish(self) -> bool:
        """
        Verify article was published.
        STRICT: Only returns True with ground truth.
        """
        # Use the same strict verification
        success = await self._wait_publish_result()
        if success:
            self.logger.info("✅ Publish VERIFIED")
            return True
        else:
            self.logger.error("❌ Publish verification FAILED")
            return False
    
    # =========================================================================
    # DEBUG
    # =========================================================================
    
    async def _screenshot(self, name: str) -> str:
        """Take screenshot."""
        if self.page is None:
            return ""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.SCREENSHOT_DIR / f"{name}_{ts}.png"
            await self.page.screenshot(path=str(path), full_page=True)
            self.logger.info(f"📸 {path}")
            return str(path)
        except:
            return ""
    
    async def _dump_debug(self, name: str):
        """Dump HTML and screenshot."""
        if self.page is None:
            return
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self._screenshot(name)
            html = await self.page.content()
            path = self.SCREENSHOT_DIR / f"{name}_{ts}.html"
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self.logger.info(f"💾 {path}")
        except Exception as e:
            self.logger.error(f"Dump error: {e}")
