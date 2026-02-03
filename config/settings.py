import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


def _get_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _get_image_mode(value: str | None) -> str:
    """IMAGE_MODE: 'api' (default) or 'browser'. Invalid values fall back to 'api'."""
    if not value:
        return "api"
    v = value.strip().lower()
    return "browser" if v == "browser" else "api"


@dataclass(frozen=True)
class Settings:
    cms_url: str
    cms_email: str
    cms_password: str
    cms_role: str  # Login role like "State Sub Editor"
    source_url: str
    gemini_api_key: str | None
    openai_api_key: str | None
    ai_provider: str
    headless: bool
    slow_mo: int  # Milliseconds to wait between browser actions (for visibility)
    user_data_dir: str
    screenshots_dir: str
    downloads_dir: str
    image_mode: str  # "api" | "browser" — default "api"
    headline_max: int = 80
    summary_max: int = 400
    navigation_timeout_ms: int = 30000
    selector_timeout_ms: int = 10000


def get_settings() -> Settings:
    return Settings(
        cms_url=os.getenv("CMS_URL", "").strip(),
        cms_email=os.getenv("CMS_EMAIL", "").strip(),
        cms_password=os.getenv("CMS_PASSWORD", "").strip(),
        cms_role=os.getenv("CMS_ROLE", "State Sub Editor").strip(),
        source_url=os.getenv("SOURCE_URL", "").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ai_provider=os.getenv("AI_PROVIDER", "gemini").strip().lower(),
        headless=_get_bool(os.getenv("HEADLESS"), False),
        slow_mo=int(os.getenv("SLOW_MO", "0")),  # Milliseconds between actions
        user_data_dir=os.getenv("USER_DATA_DIR", ".playwright").strip(),
        screenshots_dir=os.getenv("SCREENSHOTS_DIR", "artifacts/screenshots").strip(),
        downloads_dir=os.getenv("DOWNLOADS_DIR", "artifacts/downloads").strip(),
        image_mode=_get_image_mode(os.getenv("IMAGE_MODE")),
    )
