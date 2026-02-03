# Setup on a New System

Use this checklist to run the Shortly AI Agent on a **fresh system** (new PC, new VM, or new machine).

---

## 1. Install Python

- **Version:** Python **3.10** or **3.11** (3.9+ may work; 3.12/3.13 tested with current deps).
- **Windows:** Download from [python.org](https://www.python.org/downloads/) and check **“Add Python to PATH”**.
- **macOS/Linux:** Use system package manager or [pyenv](https://github.com/pyenv/pyenv):
  ```bash
  # macOS (Homebrew)
  brew install python@3.11

  # Ubuntu/Debian
  sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip
  ```
- Confirm:
  ```bash
  python --version
  # or
  python3 --version
  ```

---

## 2. Get the Project on the New System

- Copy the whole project folder (e.g. **Shortly AI Agent**) to the new machine, or clone if it’s in Git:
  ```bash
  git clone <your-repo-url>
  cd "Shortly AI Agent"
  ```

---

## 3. Create a Virtual Environment (Recommended)

```bash
# Create venv
python -m venv venv

# Activate:
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Windows (CMD)
.\venv\Scripts\activate.bat
# macOS/Linux
source venv/bin/activate
```

---

## 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Included packages:** `playwright`, `python-dotenv`, `openai`, `requests`, `httpx`.

---

## 5. Install Playwright Browser (Chromium)

The agent uses Playwright to drive the browser. Install Chromium once:

```bash
python -m playwright install chromium
```

**Optional:** Install system libraries Playwright needs (Linux):

```bash
python -m playwright install-deps chromium
```

---

## 6. Configure Environment Variables

- Copy the example env file:
  ```bash
  # Windows (PowerShell)
  Copy-Item env.example .env
  # macOS/Linux
  cp env.example .env
  ```
- Edit **`.env`** and set **at least** these (required):

| Variable           | Description                          |
|--------------------|--------------------------------------|
| `CMS_URL`          | Your CMS base URL (e.g. `https://...`) |
| `CMS_EMAIL`        | CMS login email                      |
| `CMS_PASSWORD`    | CMS login password                   |
| `OPENAI_API_KEY`  | OpenAI API key (for summarization, Telugu, vision) |

- Optional in `.env`:
  - `HEADLESS` – `false` = visible browser (good for first run).
  - `SLOW_MO` – delay in ms (e.g. `500`).
  - `IMAGE_MODE` – `api` (default) or `browser`.
  - `MAX_ARTICLE_AGE_HOURS` – only use articles from last N hours (default `24`).

---

## 7. Run the Agent

From the project root (with venv activated if you use it):

```bash
python __main__.py
```

Or:

```bash
python -m __main__
```

You should see the browser open, login to the CMS, fetch articles (Times of India / The Hindu), summarize, translate to Telugu, and publish.

---

## Quick Checklist

- [ ] Python 3.10+ installed and on PATH  
- [ ] Project folder on the new system  
- [ ] Virtual environment created and activated (optional)  
- [ ] `pip install -r requirements.txt`  
- [ ] `python -m playwright install chromium`  
- [ ] `.env` created from `env.example` with `CMS_URL`, `CMS_EMAIL`, `CMS_PASSWORD`, `OPENAI_API_KEY`  
- [ ] Run: `python __main__.py`  

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| `python` not found | Use `python3` or add Python to PATH. |
| `playwright` not found | Run `pip install -r requirements.txt` and `python -m playwright install chromium`. |
| Browser doesn’t start | Run `python -m playwright install chromium` and, on Linux, `python -m playwright install-deps chromium`. |
| Missing env vars | Ensure `.env` exists and has `CMS_URL`, `CMS_EMAIL`, `CMS_PASSWORD`, `OPENAI_API_KEY`. |
| SSL / network errors | Check firewall, proxy, and that the machine can reach the CMS and OpenAI. |
