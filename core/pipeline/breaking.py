from __future__ import annotations

from datetime import timedelta
from typing import Dict, List

from .models import BreakingDecision, EventCluster


class BreakingNewsClassifier:
    def __init__(
        self,
        source_credibility: Dict[str, float],
        min_sources: int = 3,
        max_window_minutes: int = 30,
        confidence_threshold: float = 0.6,
        min_high_cred_sources: int = 1,
        high_cred_threshold: float = 0.85,
        min_avg_credibility: float = 0.70,
    ):
        self.source_credibility = source_credibility
        self.min_sources = min_sources
        self.max_window_minutes = max_window_minutes
        self.max_window = timedelta(minutes=max_window_minutes)
        self.confidence_threshold = confidence_threshold
        self.min_high_cred_sources = min_high_cred_sources
        self.high_cred_threshold = high_cred_threshold
        self.min_avg_credibility = min_avg_credibility

    def classify(self, cluster: EventCluster) -> BreakingDecision:
        unique_sources = len(cluster.source_groups.keys())
        reasons: List[str] = []

        if unique_sources < self.min_sources:
            reasons.append(f"sources={unique_sources} < {self.min_sources}")

        window = cluster.end_time - cluster.start_time
        if window > self.max_window:
            reasons.append(f"outside_{self.max_window_minutes}m_window")

        source_weights = [self.source_credibility.get(src, 0.4) for src in cluster.source_groups.keys()]
        avg_cred = (sum(source_weights) / len(source_weights)) if source_weights else 0.0
        high_cred_count = sum(1 for weight in source_weights if weight >= self.high_cred_threshold)

        if avg_cred < self.min_avg_credibility:
            reasons.append(f"avg_cred={avg_cred:.2f} < {self.min_avg_credibility:.2f}")

        if high_cred_count < self.min_high_cred_sources:
            reasons.append(f"high_cred_sources={high_cred_count} < {self.min_high_cred_sources}")

        confidence = self._compute_confidence(cluster)
        if confidence < self.confidence_threshold:
            reasons.append(f"confidence={confidence:.2f} < {self.confidence_threshold:.2f}")

        is_breaking = len(reasons) == 0
        return BreakingDecision(is_breaking=is_breaking, confidence=confidence, reasons=reasons)

    def _compute_confidence(self, cluster: EventCluster) -> float:
        sources = list(cluster.source_groups.keys())
        if not sources:
            return 0.0

        weights = [self.source_credibility.get(src, 0.4) for src in sources]
        weighted = sum(weights) / len(weights)

        source_factor = min(1.0, len(sources) / max(1, self.min_sources))

        span_minutes = max(0.0, (cluster.end_time - cluster.start_time).total_seconds() / 60.0)
        time_factor = max(0.0, 1.0 - (span_minutes / max(1.0, float(self.max_window_minutes))))

        return round((weighted * 0.5) + (source_factor * 0.35) + (time_factor * 0.15), 4)
