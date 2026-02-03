# Autonomous AI News Editor

A fully autonomous news editor that scrapes articles from trusted sources, translates them to Telugu, and publishes them to a CMS - all in a single browser-based process.

## Quick Start

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browser (use python -m playwright, not just playwright)
python -m playwright install chromium
```

### 2. Setup Environment Variables

Create a `.env` file in the project root:

```env
# CMS Credentials (REQUIRED)
CMS_URL=https://your-cms-url.com
CMS_EMAIL=your-email@example.com
CMS_PASSWORD=your-password
CMS_ROLE=State Sub Editor

# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Browser Settings (OPTIONAL)
HEADLESS=false
SLOW_MO=400
USER_DATA_DIR=.playwright
SCREENSHOTS_DIR=artifacts/screenshots
DOWNLOADS_DIR=artifacts/downloads
```

**Important**: 
- Copy `env.example` to `.env` and fill in your actual values
- `CMS_URL`, `CMS_EMAIL`, `CMS_PASSWORD`, and `OPENAI_API_KEY` are **REQUIRED**
- `HEADLESS=false` means browser will be visible (recommended for first run)
- `SLOW_MO=400` adds 400ms delay between actions (makes it easier to watch)

### 3. Run the Editor

```bash
python main.py
```

## What Happens When You Run

1. **Browser Opens** (visible, headful mode)
2. **CMS Login** - Automatically logs into your CMS
3. **Article Scraping** - Tries to scrape from BBC/Al Jazeera/NBC (in order)
4. **Summarization** - Generates English summary (300-360 chars)
5. **Telugu Translation** - Translates to Telugu (300-360 chars)
6. **Category Selection** - Decides category using keywords
7. **CMS Publishing** - Fills form and publishes article
8. **Success** - Stops when one article is published

The system will try up to **5 articles** until one is successfully published.

## Architecture

**Key Principle**: The Browser Agent is the ONLY decision maker. No external schedulers, databases, or API servers.

### Components

- **main.py**: Controller loop (tries up to 5 articles until one is published)
- **agent/browser_agent.py**: Playwright browser management
- **agent/scraper.py**: News article scraping from BBC/Al Jazeera/NBC
- **agent/summarizer.py**: English summarization (300-360 chars)
- **agent/telugu_writer.py**: Telugu translation with fallbacks
- **agent/category_decider.py**: Simple keyword-based category selection
- **agent/cms_publisher.py**: CMS login, form filling, and publishing

## Features

- **No Database**: All in-memory, no persistence
- **No Scheduler**: Single run, publishes one article
- **No Hard Blockers**: Quality checks warn but never block
- **Visible Browser**: See exactly what's happening
- **Automatic Fallbacks**: Telugu failures → English, publish failures → try next article

## Category Rules

- **Spiritual**: temple, god, puja, astrology
- **Sports**: cricket, match, player, ipl
- **Entertainment**: actor, film, cinema, movie
- **Health**: health, diet, disease, medical
- **International**: Only if clearly foreign (USA, China, etc.)
- **National**: Default for everything else

## Telugu Style

Matches TV9/Eenadu/Sakshi digital news style:
- Natural Telugu (not literal translation)
- Newsroom vocabulary
- Short, punchy sentences
- 300-360 characters for summary

## Troubleshooting

### "OPENAI_API_KEY not found"
- Make sure you created `.env` file (not `env.example`)
- Check that `OPENAI_API_KEY=sk-...` is in `.env`

### "CMS credentials not found"
- Make sure `CMS_URL`, `CMS_EMAIL`, and `CMS_PASSWORD` are in `.env`

### Browser doesn't open
- Make sure Playwright is installed: `playwright install chromium`
- Check that `HEADLESS=false` in `.env`

### "No articles found"
- Check internet connection
- News sources (BBC/Al Jazeera/NBC) might be blocked in your region
- Try running again (different articles may be available)

### CMS login fails
- Verify CMS credentials in `.env`
- Check that `CMS_ROLE` matches exactly (case-sensitive)
- Make sure CMS URL is correct

### Article scraping fails
- Network issues
- News source website structure changed
- Try running again (will try different sources)

## Logs

Check `artifacts/logs/automation.log` for detailed logs of what happened.

## Screenshots

Screenshots are saved to `artifacts/screenshots/` if errors occur.
