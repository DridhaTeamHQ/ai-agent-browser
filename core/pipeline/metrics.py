from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PipelineMetrics:
    total_scraped_per_category: Dict[str, int] = field(default_factory=dict)
    clusters_formed: int = 0
    breaking_news_count: int = 0
    image_pass_count: int = 0
    image_fail_count: int = 0
    image_fail_reasons: Counter = field(default_factory=Counter)

    def record_category_counts(self, by_category: Dict[str, list]) -> None:
        self.total_scraped_per_category = {k: len(v) for k, v in by_category.items()}

    def record_image_result(self, passed: bool, reason: str = "") -> None:
        if passed:
            self.image_pass_count += 1
            return
        self.image_fail_count += 1
        if reason:
            self.image_fail_reasons[reason] += 1
