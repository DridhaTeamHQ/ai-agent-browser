# IMAGE_MODE: API vs Browser

## Values

| Value    | Default | Behavior |
|----------|---------|----------|
| `api`    | Yes     | OG image download via HTTP. If no OG or search strategy, optional Google Images search in a new tab during form fill (legacy). |
| `browser`| No      | Open a **second** Playwright tab for Google Images → search keywords → click one image → download to disk → **close image tab** → return focus to CMS tab → upload file → wait for media commit → publish. CMS page remains **untouched** during image search. |

Default is **`api`**. Set `IMAGE_MODE=browser` to use browser-based image selection.

## Constraints (browser mode)

- **CMS page must remain untouched and open** during image search.
- **Second tab only** for Google Images; no CMS navigation during search.
- **Image tab MUST be fully closed** before CMS upload.
- **Do NOT publish** unless media commit is verified after upload.
- **If image download fails** → discard article (no retry).

## Flow (browser mode)

1. CMS tab stays on current page (e.g. dashboard).
2. Open second tab → Google Images.
3. Search keywords (e.g. `{article.title} news`).
4. Click one image.
5. Download it to disk.
6. Close the image tab.
7. Focus remains on CMS tab (only one tab left).
8. Navigate to Create Article (if not already there), fill form, upload the downloaded file.
9. Wait for media commit (crop closed / preview visible).
10. Publish only if media commit verified.

## Risks (browser mode)

| Risk | Description |
|------|-------------|
| **DOM breakage** | Google Images markup (e.g. `.rg_i`) can change and break selectors. |
| **CAPTCHA / blocking** | Google may show CAPTCHA or throttle/block automated traffic. |
| **URL/changes** | High-res image URLs and CDN behavior can change; extraction may fail. |
| **Resource usage** | Extra tab increases memory and failure points. |
| **Latency** | Slower than API (network + UI). |
| **Legal** | Scraping images from Google may have copyright/licensing implications. |

## Enabling browser mode

In `.env`:

```bash
IMAGE_MODE=browser
```

Default (API) remains if unset or any value other than `browser`.
