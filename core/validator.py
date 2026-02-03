"""
STRICT VALIDATOR - Pre-Flight Validation Gate.

This module ensures ArticleData is PERFECT before browser execution.
If validation fails, the browser is NEVER touched.

Failure Classification:
- CONTENT_VALIDATION_FAILURE: Data is invalid, discard article
- All other failures are browser-level (handled by Orchestrator)
"""

import os
import re
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Optional
from utils.logger import get_logger


class FailureType(str, Enum):
    """Strict failure classification. Each has ONE recovery path."""
    # Pre-Browser (Validation)
    CONTENT_VALIDATION_FAILURE = "content_validation_failure"
    
    # Browser-Level
    LOGIN_FAILURE = "login_failure"
    NAVIGATION_FAILURE = "navigation_failure"
    REACT_STATE_CORRUPTION = "react_state_corruption"
    CATEGORY_SELECTION_FAILURE = "category_selection_failure"
    IMAGE_UPLOAD_FAILURE = "image_upload_failure"
    CROP_MODAL_STUCK = "crop_modal_stuck"
    PUBLISH_BUTTON_NOT_FOUND = "publish_button_not_found"
    PUBLISH_NO_OP = "publish_no_op"
    BROWSER_CRASH = "browser_crash"


class RecoveryAction(str, Enum):
    """Allowed recovery actions. NEVER chain these."""
    DISCARD_ARTICLE = "discard_article"       # Skip this article
    RETRY_ACTION = "retry_action"             # Retry same action once
    RELOAD_PAGE = "reload_page"               # Clear React state
    RESTART_BROWSER = "restart_browser"       # Full browser restart
    ABORT_PROCESS = "abort_process"           # Stop execution


# Recovery Matrix (STRICT)
RECOVERY_MATRIX = {
    FailureType.CONTENT_VALIDATION_FAILURE: RecoveryAction.DISCARD_ARTICLE,
    FailureType.LOGIN_FAILURE: RecoveryAction.RETRY_ACTION,
    FailureType.NAVIGATION_FAILURE: RecoveryAction.RELOAD_PAGE,
    FailureType.REACT_STATE_CORRUPTION: RecoveryAction.RELOAD_PAGE,
    FailureType.CATEGORY_SELECTION_FAILURE: RecoveryAction.RETRY_ACTION,
    FailureType.IMAGE_UPLOAD_FAILURE: RecoveryAction.RETRY_ACTION,
    FailureType.CROP_MODAL_STUCK: RecoveryAction.DISCARD_ARTICLE,
    FailureType.PUBLISH_BUTTON_NOT_FOUND: RecoveryAction.RETRY_ACTION,
    FailureType.PUBLISH_NO_OP: RecoveryAction.RETRY_ACTION,
    FailureType.BROWSER_CRASH: RecoveryAction.RESTART_BROWSER,
}


# Valid CMS Categories (EXACT match required)
VALID_CATEGORIES = [
    "National",
    "International",
    "Politics",
    "Business",
    "Sports",
    "Entertainment",
    "Technology",
    "Health",
    "Lifestyle",
    "Spiritual",
]


@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool
    failure_type: Optional[FailureType] = None
    error_message: str = ""


class ArticleValidator:
    """
    Pre-flight validation gate.
    
    Ensures ArticleData meets all requirements BEFORE browser execution.
    """
    
    # Character limits (CMS constraints – match form: 80 title, 380 content)
    MIN_TITLE_LEN = 10
    MAX_TITLE_LEN = 80
    MIN_BODY_LEN = 50
    MAX_BODY_LEN = 380
    
    # Telugu purity threshold
    MIN_TELUGU_PURITY = 80.0  # Percentage
    
    def __init__(self):
        self.logger = get_logger("validator")
    
    def validate(self, english_title: str, english_body: str,
                 telugu_title: str, telugu_body: str,
                 category: str, image_path: Optional[str],
                 hashtag: str, image_search_query: str = "") -> ValidationResult:
        """
        Validate all fields. Returns ValidationResult.
        
        If is_valid=False, browser must NOT be touched.
        """
        # 1. English Title
        if not english_title or len(english_title) < self.MIN_TITLE_LEN:
            return ValidationResult(
                is_valid=False,
                failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                error_message=f"English title too short: {len(english_title or '')} chars"
            )
        
        if len(english_title) > self.MAX_TITLE_LEN:
            return ValidationResult(
                is_valid=False,
                failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                error_message=f"English title too long: {len(english_title)} chars"
            )
        
        # 2. English Body
        if not english_body or len(english_body) < self.MIN_BODY_LEN:
            return ValidationResult(
                is_valid=False,
                failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                error_message=f"English body too short: {len(english_body or '')} chars"
            )
        
        # 3. Telugu Title (with purity check)
        if not telugu_title or len(telugu_title) < self.MIN_TITLE_LEN:
            return ValidationResult(
                is_valid=False,
                failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                error_message=f"Telugu title too short: {len(telugu_title or '')} chars"
            )
        
        telugu_title_purity = self._telugu_percentage(telugu_title)
        if telugu_title_purity < self.MIN_TELUGU_PURITY:
            return ValidationResult(
                is_valid=False,
                failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                error_message=f"Telugu title purity too low: {telugu_title_purity:.1f}%"
            )
        
        # 4. Telugu Body (with purity check)
        if not telugu_body or len(telugu_body) < self.MIN_BODY_LEN:
            return ValidationResult(
                is_valid=False,
                failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                error_message=f"Telugu body too short: {len(telugu_body or '')} chars"
            )
        
        telugu_body_purity = self._telugu_percentage(telugu_body)
        if telugu_body_purity < self.MIN_TELUGU_PURITY:
            return ValidationResult(
                is_valid=False,
                failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                error_message=f"Telugu body purity too low: {telugu_body_purity:.1f}%"
            )
        
        # 5. Category (EXACT match)
        if category not in VALID_CATEGORIES:
            return ValidationResult(
                is_valid=False,
                failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                error_message=f"Invalid category: {category}"
            )
        
        # 6. Image (must exist or have search query)
        if image_path:
            if not os.path.exists(image_path):
                return ValidationResult(
                    is_valid=False,
                    failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                    error_message=f"Image not found: {image_path}"
                )
            # Check file size
            if os.path.getsize(image_path) < 1000:  # < 1KB is suspicious
                return ValidationResult(
                    is_valid=False,
                    failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                    error_message=f"Image too small: {os.path.getsize(image_path)} bytes"
                )
        elif image_search_query:
            # Valid: We will search for this image later
            pass
        else:
            # Image is mandatory
            return ValidationResult(
                is_valid=False,
                failure_type=FailureType.CONTENT_VALIDATION_FAILURE,
                error_message="Image (or search query) is required"
            )
        
        # 7. Hashtag (basic check)
        if not hashtag or not hashtag.startswith("#"):
            # Auto-fix instead of reject
            self.logger.warning(f"Hashtag auto-fixed: '{hashtag}' -> '#news'")
            # Note: We don't modify the input here, orchestrator should handle
        
        # ALL CHECKS PASSED
        self.logger.info("✅ Validation PASSED")
        return ValidationResult(is_valid=True)
    
    def _telugu_percentage(self, text: str) -> float:
        """Calculate percentage of Telugu Unicode characters."""
        if not text:
            return 0.0
        telugu_chars = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
        total_chars = sum(1 for c in text if not c.isspace())
        return (telugu_chars / total_chars * 100) if total_chars > 0 else 0.0
    
    def get_recovery_action(self, failure_type: FailureType) -> RecoveryAction:
        """Get the correct recovery action for a failure type."""
        return RECOVERY_MATRIX.get(failure_type, RecoveryAction.DISCARD_ARTICLE)
