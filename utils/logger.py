import logging
import os
from typing import Optional


_configured = False


def _configure_logging(log_path: str) -> None:
    global _configured
    if _configured:
        return
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    _configured = True


def get_logger(name: str, log_path: Optional[str] = None) -> logging.Logger:
    if not log_path:
        log_path = os.path.join("artifacts", "logs", "automation.log")
    _configure_logging(log_path)
    return logging.getLogger(name)
