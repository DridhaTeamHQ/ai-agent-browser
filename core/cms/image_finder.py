"""
Google Image Finder - Finds images using Browser.

IMAGE_MODE:
- "api" (default): OG image download via HTTP; optional search query used in fill_form (legacy).
- "browser": Open a SECOND Playwright tab for Google Images, search, click one image,
  wait for full-res load, collect candidates, use GPT vision to pick best, download.

- Waits for images to fully load before capturing (networkidle + delay).
- Uses GPT-4o-mini vision to select the best-quality image from multiple candidates.
"""

import asyncio
import base64
import os
import re
from pathlib import Path
from typing import Optional, List, Any, cast

from playwright.async_api import Page, BrowserContext
import httpx

from utils.logger import get_logger
from utils.image_utils import meets_minimum_resolution


def get_image_mode() -> str:
    """IMAGE_MODE: 'api' | 'browser'. Default 'api'."""
    v = (os.getenv("IMAGE_MODE") or "").strip().lower()
    return "browser" if v == "browser" else "api"


# Wait for full-res image to load (many CDNs load thumbnail first, then high-res)
IMAGE_LOAD_WAIT_NETWORKIDLE_MS = 4000
IMAGE_LOAD_EXTRA_SEC = 6
MAX_VISION_CANDIDATES = 5


class GoogleImageFinder:
    """
    Finds and downloads images from Google Images using Playwright.
    Waits for images to load, collects candidates, uses GPT vision to pick best.
    """

    def __init__(self, page: Page, download_dir: Optional[Path] = None):
        self.page = page
        self.logger = get_logger("google_images")
        self.download_dir = download_dir or Path("downloads/images")
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def _wait_for_images_loaded(self) -> None:
        """Wait for network to settle and full-res image to load."""
        try:
            await self.page.wait_for_load_state("networkidle", timeout=IMAGE_LOAD_WAIT_NETWORKIDLE_MS)
        except Exception:
            pass
        await asyncio.sleep(IMAGE_LOAD_EXTRA_SEC)

    async def find_and_download(self, query: str) -> Optional[str]:
        """
        Search Google Images (or Bing fallback), click first image, download to disk.
        Returns absolute path to downloaded file, or None on failure.
        """
        short_query = (query or "")[:80].strip()
        if not short_query:
            return None

        # Try Google first
        path = await self._google_images_search(short_query)
        if path:
            return path

        # Fallback: Bing Images (simpler DOM, often more stable)
        self.logger.info("   Google failed, trying Bing Images...")
        return await self._bing_images_search(short_query)

    async def _google_images_search(self, query: str) -> Optional[str]:
        """Google Images: direct search URL, multiple selectors for first thumbnail."""
        try:
            from urllib.parse import quote_plus
            url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=isch"
            self.logger.info(f"🔍 Google Images: {query[:50]}...")
            await self.page.goto(url, timeout=25000)
            await asyncio.sleep(2)

            try:
                await self.page.click("button:has-text('Accept all')", timeout=2000)
                await asyncio.sleep(0.5)
            except Exception:
                pass

            # Wait for result grid: #islrg (current) or .rg_i (legacy)
            first_clickable = None
            for selector in ["#islrg img", "#islrg a", ".rg_i", "#islrg div[data-id] a", "img.rg_i"]:
                try:
                    loc = self.page.locator(selector).first
                    if await loc.count() > 0 and await loc.is_visible(timeout=4000):
                        first_clickable = loc
                        self.logger.info(f"   Found results: {selector}")
                        break
                except Exception:
                    continue

            if not first_clickable:
                self.logger.warning("   No image results (Google)")
                return None

            self.logger.info("   Clicking first image...")
            await first_clickable.click()
            await self._wait_for_images_loaded()

            candidates = await self._get_high_res_candidates()
            if not candidates:
                return None
            return await self._download_best_image(candidates, query)

        except Exception as e:
            self.logger.warning(f"   Google Images failed: {e}")
            return None

    async def _bing_images_search(self, query: str) -> Optional[str]:
        """Bing Images: simpler DOM, often works when Google fails."""
        try:
            from urllib.parse import quote_plus
            url = f"https://www.bing.com/images/search?q={quote_plus(query)}"
            await self.page.goto(url, timeout=20000)
            await asyncio.sleep(2)

            # Try first big image link or thumbnail; if SVG, try next result
            for selector in ["a.mimg", "img.mimg", ".imgpt img", "a[href*='media'] img"]:
                try:
                    loc = self.page.locator(selector)
                    n = await loc.count()
                    if n == 0:
                        continue
                    for idx in range(min(n, 5)):
                        try:
                            el = loc.nth(idx)
                            if not await el.is_visible(timeout=3000):
                                continue
                            self.logger.info("   Clicking first Bing image...")
                            await el.click()
                            await self._wait_for_images_loaded()
                            candidates = await self._get_high_res_candidates()
                            if candidates:
                                path = await self._download_best_image(candidates, query)
                                if path:
                                    return path
                            src = await el.get_attribute("src")
                            if src and src.startswith("http"):
                                path = await self._download_url(src, query)
                                if path:
                                    return path
                        except Exception:
                            continue
                except Exception:
                    continue

            self.logger.warning("   No image URL from Bing")
            return None

        except Exception as e:
            self.logger.warning(f"   Bing Images failed: {e}")
            return None

    async def _get_high_res_candidates(self) -> List[str]:
        """Return up to MAX_VISION_CANDIDATES image URLs: prefer 'Original' link, then top by pixel size."""
        # 1) "Original" / "View image" link = full-res URL (use as sole candidate)
        link_texts = ["original", "view image", "full size", "open original", "full resolution", "see full size"]
        for text in link_texts:
            try:
                link = self.page.locator(f"a:has-text('{text}')").first
                if await link.count() == 0:
                    continue
                href = await link.get_attribute("href")
                if href and href.startswith("http") and ".svg" not in href.lower():
                    # Accept any http link for these labels (often redirect to full-res image)
                    self.logger.info(f"   Using '{text}' link for high-res")
                    return [href]
            except Exception:
                continue

        # 2) Collect visible images, sort by pixel size, return top N
        candidates = self.page.locator("img[src^='http'], img[src^='data:image']")
        count = await candidates.count()
        scored: List[tuple] = []
        for i in range(min(count, 25)):
            try:
                img = candidates.nth(i)
                if not await img.is_visible():
                    continue
                src = await img.get_attribute("src")
                if not src or "google" in src or "gstatic" in src or "favicon" in src:
                    continue
                if ".svg" in src.lower():
                    continue
                if not any(x in src.lower() for x in [".jpg", ".jpeg", ".png", ".webp", "images", "uploads", "bing", "data:image"]):
                    continue
                wh = await img.evaluate("el => (el.naturalWidth || 0) * (el.naturalHeight || 0)")
                if isinstance(wh, (int, float)) and wh > 0:
                    scored.append((int(wh), src))
            except Exception:
                continue
        scored.sort(key=lambda x: -x[0])
        return [src for _, src in scored[:MAX_VISION_CANDIDATES]]

    async def _download_url_to_bytes(self, url: str) -> Optional[bytes]:
        """Download image to bytes (for vision). Reject SVG."""
        if ".svg" in url.lower():
            return None
        try:
            if url.startswith("data:image"):
                if "svg" in url.split(",", 1)[0].lower():
                    return None
                _header, encoded = url.split(",", 1)
                return base64.b64decode(encoded)
            if url.startswith("http"):
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        ct = (resp.headers.get("content-type") or "").lower()
                        if "svg" in ct:
                            return None
                        return resp.content
        except Exception as e:
            self.logger.debug(f"Download to bytes failed: {e}")
        return None

    def _select_best_with_vision(self, image_bytes_list: List[bytes], query: str) -> int:
        """Use GPT-4o-mini vision to pick the best image. Returns 0-based index (or 0 on failure)."""
        if not image_bytes_list or len(image_bytes_list) == 1:
            return 0
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            content: List[Any] = [
                {"type": "text", "text": (
                    f"News headline / context: \"{query[:200]}\". "
                    f"You see {len(image_bytes_list)} candidate images (numbered 1 to {len(image_bytes_list)}). "
                    "Which image is the HIGHEST QUALITY (sharp, well-lit, professional) and best suited for a news article? "
                    "Reply with ONLY one number (1, 2, 3, etc.)."
                )}
            ]
            for data in image_bytes_list[:MAX_VISION_CANDIDATES]:
                b64 = base64.standard_b64encode(data).decode("ascii")
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=cast(Any, [{"role": "user", "content": content}]),
                max_tokens=10,
            )
            raw = (response.choices[0].message.content or "").strip()
            match = re.search(r"[1-9]\d*", raw)
            num = int(match.group()) if match else 1
            idx = max(0, min(num - 1, len(image_bytes_list) - 1))
            self.logger.info(f"   Vision selected image {num} of {len(image_bytes_list)}")
            return idx
        except Exception as e:
            self.logger.warning(f"   Vision selection failed: {e}, using first image")
            return 0

    async def _download_best_image(self, candidate_urls: List[str], query: str) -> Optional[str]:
        """Download candidates, use vision to pick best, save and return path."""
        if not candidate_urls:
            return None
        if len(candidate_urls) == 1:
            return await self._download_url(candidate_urls[0], query)
        # Download each to bytes (limit size for API: ~5MB per image; keep first 5)
        bytes_list: List[bytes] = []
        max_bytes_per_image = 4_000_000  # ~4MB so vision API stays within limits
        for url in candidate_urls[:MAX_VISION_CANDIDATES]:
            data = await self._download_url_to_bytes(url)
            if data and len(data) <= max_bytes_per_image:
                bytes_list.append(data)
        if not bytes_list:
            return await self._download_url(candidate_urls[0], query)
        best_idx = self._select_best_with_vision(bytes_list, query)
        chosen = bytes_list[best_idx]
        if not meets_minimum_resolution(chosen):
            self.logger.warning("   Vision-selected image below min resolution (640x480), skipping")
            return None
        safe_name = re.sub(r"[^\w\s-]", "", query)[:30].strip().replace(" ", "_")
        filename = self.download_dir / f"{safe_name}.jpg"
        filename.write_bytes(chosen)
        self.logger.info(f"✅ Downloaded (vision-selected): {filename.name}")
        return str(filename.resolve())

    async def _download_url(self, url: str, query: str) -> Optional[str]:
        """Download image from URL (http or base64) to disk. Reject SVG (CMS needs JPG/PNG/WEBP)."""
        try:
            if ".svg" in url.lower() or "image/svg" in (url[:50].lower()):
                self.logger.warning("   Skipping SVG URL (CMS needs JPG/PNG/WEBP)")
                return None
            safe_name = re.sub(r"[^\w\s-]", "", query)[:30].strip().replace(" ", "_")
            filename = self.download_dir / f"{safe_name}.jpg"

            if url.startswith("data:image"):
                if "svg" in url.split(",", 1)[0].lower():
                    return None
                import base64
                _header, encoded = url.split(",", 1)
                data = base64.b64decode(encoded)
                filename.write_bytes(data)
                self.logger.info(f"✅ Downloaded (Base64): {filename.name}")
                return str(filename.resolve())

            if url.startswith("http"):
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        ct = (resp.headers.get("content-type") or "").lower()
                        if "svg" in ct:
                            self.logger.warning("   Skipping SVG response (CMS needs JPG/PNG/WEBP)")
                            return None
                        filename.write_bytes(resp.content)
                        self.logger.info(f"✅ Downloaded: {filename.name}")
                        return str(filename.resolve())

            return None
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return None


async def find_and_download_in_new_tab(
    context: BrowserContext,
    query: str,
    download_dir: Optional[Path] = None,
) -> Optional[str]:
    """
    Open a SECOND tab for Google Images, search, click one image, download to disk,
    then close the image tab. CMS page is never used or navigated.

    Constraints:
    - The image tab is fully closed before returning.
    - Caller must use the returned path on the CMS tab only after this returns.

    Returns: Local file path, or None if download failed (caller should discard article).
    """
    logger = get_logger("google_images")
    image_page: Optional[Page] = None
    try:
        image_page = await context.new_page()
        finder = GoogleImageFinder(image_page, download_dir=download_dir)
        path = await finder.find_and_download(query)
        return path
    finally:
        if image_page and not image_page.is_closed():
            try:
                await image_page.close()
                logger.info("   Image tab closed.")
            except Exception as e:
                logger.warning(f"   Error closing image tab: {e}")
