"""CMS publisher with state-aware navigation and resilient selectors."""

import asyncio
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import httpx

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from core.cms.image_finder import GoogleImageFinder
from utils.image_utils import meets_minimum_resolution
from utils.logger import get_logger


@dataclass
class ArticleData:
    english_title: str
    english_body: str
    telugu_title: str
    telugu_body: str
    category: str
    image_search_query: str = ""
    image_alt: str = ""
    hashtag: str = "#news #trending"
    image_path: Optional[str] = None
    needs_image: bool = False
    image_url: Optional[str] = None
    image_metadata: Dict[str, Any] = field(default_factory=dict)


class CMSPublisher:
    CATEGORY_ALIASES = {
        "Technology": ["Tech"],
        "Tech": ["Technology"],
        "Business": ["Finance"],
        "Finance": ["Business"],
        "Environment": ["Lifestyle", "International"],
        "Lifestyle": ["Environment"],
        "National": ["State"],
        "State": ["National"],
    }

    SCREENSHOT_DIR = Path("screenshots")
    DEBUG_DIR = Path("screenshots/debug")
    TIMEOUT = 30000

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

        self.SCREENSHOT_DIR.mkdir(exist_ok=True)
        self.DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False, slow_mo=200)
        self.context = await self.browser.new_context(viewport={"width": 1400, "height": 900})
        self.page = await self.context.new_page()
        self.image_finder = GoogleImageFinder(self.page)
        self.page.set_default_timeout(self.TIMEOUT)

    async def stop(self):
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as exc:
            self.logger.warning(f"Error stopping browser: {exc}")

    async def _wait_stable(self):
        if self.page is None:
            return
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await asyncio.sleep(0.8)

    async def _dump_debug(self, name: str):
        if self.page is None:
            return
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        png = self.DEBUG_DIR / f"{safe}.png"
        html = self.DEBUG_DIR / f"{safe}.html"
        try:
            await self.page.screenshot(path=str(png), full_page=True)
            content = await self.page.content()
            html.write_text(content, encoding="utf-8")
            self.logger.warning(f"Debug captured: {png} and {html}")
        except Exception as exc:
            self.logger.warning(f"Debug capture failed ({name}): {exc}")

    async def _is_authenticated_view(self) -> bool:
        if self.page is None:
            return False

        if "/login" not in self.page.url.lower():
            return True

        signals = [
            self.page.locator("text='Dashboard'").first,
            self.page.locator("text='Content'").first,
            self.page.locator("text='Report a Bug'").first,
            self.page.locator("text='Welcome back'").first,
        ]
        count = 0
        for loc in signals:
            try:
                if await loc.is_visible(timeout=1500):
                    count += 1
            except Exception:
                pass
        return count >= 2

    async def _is_article_form_open(self) -> bool:
        if self.page is None:
            return False

        checks = [
            self.page.locator("#title_en").first,
            self.page.locator("#content_en").first,
            self.page.locator("textarea[data-testid='rt-input-component']").first,
            self.page.locator("text='Media *'").first,
            self.page.locator("input[type='file']").first,
        ]
        for loc in checks:
            try:
                if await loc.count() > 0 and await loc.is_visible(timeout=900):
                    return True
            except Exception:
                pass
        return False

    async def _is_articles_page(self) -> bool:
        if self.page is None:
            return False

        if await self._is_article_form_open():
            return False

        url = self.page.url.lower()
        if "/articles" in url and "create" not in url and "new" not in url:
            return True

        checks = [
            self.page.locator("text='Articles Management'").first,
            self.page.locator("text='Create Article'").first,
            self.page.locator("table").first,
        ]
        visible_count = 0
        for loc in checks:
            try:
                if await loc.count() > 0 and await loc.is_visible(timeout=900):
                    visible_count += 1
            except Exception:
                pass
        return visible_count >= 2

    async def _find_first_visible(self, selectors, timeout_ms: int = 1200):
        if self.page is None:
            return None

        for selector in selectors:
            try:
                loc = self.page.locator(selector).first
                if await loc.count() > 0 and await loc.is_visible(timeout=timeout_ms):
                    return loc
            except Exception:
                continue
        return None

    async def _click_first(self, selectors, name: str, timeout_ms: int = 1200) -> bool:
        loc = await self._find_first_visible(selectors, timeout_ms=timeout_ms)
        if loc is None:
            return False
        try:
            await loc.scroll_into_view_if_needed()
        except Exception:
            pass
        try:
            await loc.click(force=True)
            await asyncio.sleep(0.5)
            return True
        except Exception as exc:
            self.logger.warning(f"Failed clicking {name}: {exc}")
            return False

    async def login(self) -> bool:
        if self.page is None:
            return False

        try:
            await self.page.goto(self.cms_url, wait_until="networkidle")
            await self._wait_stable()
            if await self._is_authenticated_view():
                self.logged_in = True
                return True

            dropdown = self.page.locator("button[role='combobox']").first
            await dropdown.click()
            await asyncio.sleep(0.8)
            await self.page.locator(f"[role='option']:has-text('{self.cms_role}')").click()

            await self.page.locator("#email").fill(self.cms_email)
            await self.page.locator("#password").fill(self.cms_password)
            await self.page.locator("button[type='submit']").click()

            await self._wait_stable()
            self.logged_in = await self._is_authenticated_view()
            return self.logged_in
        except Exception as exc:
            self.logger.error(f"Login error: {exc}")
            await self._dump_debug("login_error")
            return False

    async def _open_create_route_from_link(self) -> bool:
        if self.page is None:
            return False
        try:
            href = await self.page.evaluate(
                """() => {
                    const links = [...document.querySelectorAll('a[href]')];
                    const byText = links.find((a) => {
                        const txt = (a.textContent || '').trim();
                        const href = a.getAttribute('href') || '';
                        return /create|new/i.test(txt) && /article/i.test(`${txt} ${href}`);
                    });
                    if (byText) return new URL(byText.getAttribute('href'), window.location.href).toString();

                    const byHref = links.find((a) => {
                        const href = a.getAttribute('href') || '';
                        return /article/i.test(href) && /create|new/i.test(href);
                    });
                    if (byHref) return new URL(byHref.getAttribute('href'), window.location.href).toString();
                    return null;
                }"""
            )
            if href:
                await self.page.goto(href, wait_until="networkidle")
                await self._wait_stable()
                return await self._is_article_form_open()
        except Exception:
            pass
        return False

    async def _open_create_route_direct(self) -> bool:
        if self.page is None:
            return False
        try:
            current = self.page.url or self.cms_url
            from urllib.parse import urlparse

            parsed = urlparse(current)
            base = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else self.cms_url.rstrip("/")
            candidates = [
                f"{base}/content/articles/create",
                f"{base}/content/articles/new",
                f"{base}/articles/create",
                f"{base}/articles/new",
            ]
            for target in candidates:
                try:
                    await self.page.goto(target, wait_until="domcontentloaded")
                    await self._wait_stable()
                    if await self._is_article_form_open():
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    async def create_article(self) -> bool:
        if self.page is None:
            return False

        if await self._is_article_form_open():
            return True

        for attempt in range(3):
            await self._wait_stable()

            await self._click_first(
                [
                    "button:has-text('Content')",
                    "a:has-text('Content')",
                    "text='Content'",
                ],
                "Content menu",
            )

            await self._click_first(
                [
                    "a:has-text('Articles')",
                    "button:has-text('Articles')",
                    "text='Articles'",
                ],
                "Articles menu",
            )
            await self._wait_stable()

            if await self._is_article_form_open():
                return True

            if await self._is_articles_page():
                clicked = await self._click_first(
                    [
                        "button:has-text('Create Article')",
                        "a:has-text('Create Article')",
                        "button:has-text('Create')",
                        "a:has-text('Create')",
                        "button:has-text('New Article')",
                        "a:has-text('New Article')",
                        "text='Create Article'",
                    ],
                    "Create Article button",
                    timeout_ms=2000,
                )
                if clicked:
                    await self._wait_stable()
                    if await self._is_article_form_open():
                        return True

                if await self._open_create_route_from_link():
                    return True
                if await self._open_create_route_direct():
                    return True

            await self._dump_debug(f"create_article_attempt_{attempt + 1}")
            if self.page:
                await self.page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(1)

        self.logger.error("Navigation error: unable to reach Create Article form")
        return False

    async def _fill_react_input(self, locator, value: str) -> bool:
        try:
            await locator.focus()
            await locator.evaluate(
                """(input, v) => {
                    const proto = (input instanceof HTMLTextAreaElement)
                        ? window.HTMLTextAreaElement.prototype
                        : window.HTMLInputElement.prototype;
                    const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                    nativeSetter.call(input, v);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.dispatchEvent(new Event('blur', { bubbles: true }));
                }""",
                value,
            )
            await asyncio.sleep(0.3)
            return (await locator.input_value()).strip() == value.strip()
        except Exception:
            return False

    async def _select_category(self, category: str) -> bool:
        if self.page is None:
            return False

        async def _open_dropdown():
            candidates = [
                self.page.locator("//label[contains(normalize-space(), 'Category')]/following::button[@role='combobox'][1]").first,
                self.page.locator("button:has-text('Select category')").first,
                self.page.locator("button:has-text('Select')").last,
                self.page.locator("[role='combobox']").last,
            ]
            for c in candidates:
                try:
                    if await c.count() > 0 and await c.is_visible(timeout=1200):
                        await c.click(force=True)
                        await asyncio.sleep(0.4)
                        return c
                except Exception:
                    continue
            return None

        try:
            target = (category or "").strip()
            if not target:
                return False

            desired = [target]
            desired.extend(self.CATEGORY_ALIASES.get(target, []))

            for _attempt in range(3):
                dropdown = await _open_dropdown()
                if dropdown is None:
                    return False

                chosen = None

                for name in desired:
                    exact = self.page.get_by_role("option", name=re.compile(rf"^\\s*{re.escape(name)}\\s*$", re.I)).first
                    if await exact.count() > 0:
                        try:
                            await exact.scroll_into_view_if_needed()
                        except Exception:
                            pass
                        await exact.click(force=True)
                        chosen = name
                        break

                if chosen is None:
                    for name in desired:
                        try:
                            await self.page.keyboard.press("Control+A")
                            await self.page.keyboard.type(name)
                            await asyncio.sleep(0.25)
                            await self.page.keyboard.press("Enter")
                            chosen = name
                            break
                        except Exception:
                            continue

                await asyncio.sleep(0.6)

                try:
                    selected_text = (await dropdown.inner_text()).strip().lower()
                    if chosen and chosen.lower() in selected_text:
                        self.logger.info(f"Category selected: {chosen}")
                        return True
                except Exception:
                    pass

            self.logger.error(f"Category verify failed. target={target} selected=unknown")
            return False
        except Exception:
            return False

    async def _upload_image(self, image_path: str) -> bool:
        if self.page is None:
            return False

        try:
            chooser = self.page.locator("input[type='file']").first
            if await chooser.count() == 0:
                await self._click_first(["text='Choose File'", "button:has-text('Choose File')"], "Choose File")
                await asyncio.sleep(0.8)
                chooser = self.page.locator("input[type='file']").first

            if await chooser.count() == 0:
                self.logger.error("File input not found in CMS form")
                return False

            await chooser.set_input_files(image_path)
            await asyncio.sleep(1.5)

            files_count = await chooser.evaluate("el => (el.files && el.files.length) ? el.files.length : 0")
            if not isinstance(files_count, int) or files_count < 1:
                self.logger.error("Image upload did not attach a file")
                return False

            crop_btn = self.page.locator("button:has-text('Crop')").first
            try:
                if await crop_btn.count() > 0 and await crop_btn.is_visible(timeout=1200):
                    await crop_btn.click(force=True)
                    await asyncio.sleep(1.0)
            except Exception:
                pass

            return True
        except Exception as exc:
            self.logger.error(f"Image upload failed: {exc}")
            await self._dump_debug("image_upload_error")
            return False


    async def _download_article_image(self, image_url: str, title: str) -> Optional[str]:
        """Fallback download using the article-selected image URL only."""
        if not image_url:
            return None

        low = image_url.lower().strip()
        # Reject known branded/watermarked URL patterns in fallback path.
        if "ichef.bbci.co.uk/news/" in low and "/branded_news/" in low:
            self.logger.warning("Rejected fallback image URL: BBC branded_news watermark pattern")
            return None
        if "static.files.bbci.co.uk" in low:
            self.logger.warning("Rejected fallback image URL: BBC static branded asset")
            return None
        if low.startswith("data:image") or low.endswith(".svg"):
            return None

        try:
            safe_name = re.sub(r"[^\w\s-]", "", (title or "article_image"))[:40].strip().replace(" ", "_")
            out_path = Path("downloads/images") / f"{safe_name}.jpg"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(image_url)
                if resp.status_code != 200:
                    return None

                final_url = str(resp.url).lower()
                if "ichef.bbci.co.uk/news/" in final_url and "/branded_news/" in final_url:
                    self.logger.warning("Rejected fallback image URL after redirect: BBC branded_news watermark pattern")
                    return None
                if "static.files.bbci.co.uk" in final_url:
                    self.logger.warning("Rejected fallback image URL after redirect: BBC static branded asset")
                    return None
                if any(tok in final_url for tok in ("watermark", "channelbug", "branding", "overlay-toi_sw")):
                    self.logger.warning("Rejected fallback image URL after redirect: branded/overlay token detected")
                    return None

                content_type = (resp.headers.get("content-type") or "").lower()
                if content_type and "image" not in content_type:
                    return None

                data = resp.content
                if not meets_minimum_resolution(data):
                    self.logger.warning("Rejected fallback image after download: below minimum resolution")
                    return None

                out_path.write_bytes(data)
                return str(out_path.resolve())
        except Exception:
            return None
    async def _find_hashtag_field(self):
        if self.page is None:
            return None

        selectors = [
            "#hashtag",
            "input[name='hashtag']",
            "textarea[name='hashtag']",
            "xpath=//label[contains(normalize-space(), 'Hashtag')]/following::input[1]",
            "xpath=//label[contains(normalize-space(), 'Hashtag')]/following::textarea[1]",
        ]
        for selector in selectors:
            try:
                loc = self.page.locator(selector).first
                if await loc.count() > 0 and await loc.is_visible(timeout=900):
                    return loc
            except Exception:
                continue
        return None

    async def _fill_hashtag(self, hashtag: str) -> bool:
        field = await self._find_hashtag_field()
        if field is None:
            return False

        normalized = " ".join((hashtag or "").split()).strip()
        if not normalized.startswith("#"):
            normalized = f"#news {normalized}".strip()

        if len(normalized) > 120:
            normalized = normalized[:120].rstrip()

        if await self._fill_react_input(field, normalized):
            self.logger.info(f"Hashtag set: {normalized}")
            return True

        try:
            await field.fill("")
            await field.fill(normalized)
            await asyncio.sleep(0.3)
            value = await field.input_value()
            ok = normalized in value or value.strip() == normalized
            if ok:
                self.logger.info(f"Hashtag set: {value.strip()}")
            return ok
        except Exception:
            return False

    async def fill_form(self, data: ArticleData) -> bool:
        if self.page is None:
            return False

        try:
            if not await self._is_article_form_open():
                self.logger.error("Form not open before fill")
                return False

            if not await self._fill_react_input(self.page.locator("input[data-testid='rt-input-component']").first, data.telugu_title):
                return False
            if not await self._fill_react_input(self.page.locator("#title_en").first, data.english_title):
                return False
            if not await self._fill_react_input(self.page.locator("textarea[data-testid='rt-input-component']").first, data.telugu_body):
                return False
            if not await self._fill_react_input(self.page.locator("#content_en").first, data.english_body):
                return False

            if not await self._select_category(data.category):
                self.logger.error("Category selection failed")
                return False

            if not await self._fill_hashtag(data.hashtag):
                self.logger.error("Hashtag fill failed")
                return False

            image_path = data.image_path if data.image_path and os.path.exists(data.image_path) else None
            if not image_path and data.image_url:
                self.logger.info("Image path missing, trying article image URL fallback")
                image_path = await self._download_article_image(data.image_url, data.english_title)

            if not image_path or not os.path.exists(image_path):
                self.logger.warning("Image path missing while filling form")
                return False

            data.image_path = image_path
            if not await self._upload_image(image_path):
                return False

            return True
        except Exception as exc:
            self.logger.error(f"Form error: {exc}")
            await self._dump_debug("form_fill_error")
            return False
    async def _find_publish_button(self):
        if self.page is None:
            return None

        selectors = [
            "button:has-text('Publish')",
            "button:has-text('Publish Article')",
            "button:has-text('Submit')",
            "button:has-text('Save')",
            "button[type='submit']:has-text('Publish')",
            "[data-testid='publish-button']",
        ]

        for sel in selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=800):
                    return loc
            except Exception:
                continue

        try:
            role_button = self.page.get_by_role("button", name=re.compile(r"publish|submit|save", re.I)).first
            if await role_button.count() > 0 and await role_button.is_visible(timeout=800):
                return role_button
        except Exception:
            pass

        return None

    async def _wait_publish_success(self) -> bool:
        if self.page is None:
            return False

        for _ in range(24):
            await asyncio.sleep(1)
            try:
                if await self._is_articles_page() and not await self._is_article_form_open():
                    return True

                if await self.page.locator("text=/published|success|created/i").first.is_visible(timeout=200):
                    return True
            except Exception:
                pass

        return False

    async def publish(self) -> bool:
        if self.page is None:
            return False

        try:
            if await self._is_articles_page() and not await self._is_article_form_open():
                return True

            btn = None
            for _ in range(8):
                btn = await self._find_publish_button()
                if btn is not None:
                    break
                await self.page.mouse.wheel(0, 900)
                await asyncio.sleep(0.4)

            if btn is None:
                await self._dump_debug("publish_button_missing")
                self.logger.error("Publish button not found")
                return False

            await btn.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            await btn.click(force=True)

            if await self._wait_publish_success():
                return True

            await self._dump_debug("publish_no_success_signal")
            self.logger.error("Publish click done but no success signal")
            return False
        except Exception as exc:
            self.logger.error(f"Publish failed: {exc}")
            await self._dump_debug("publish_exception")
            return False

    async def verify_publish(self) -> bool:
        return await self._wait_publish_success()

























