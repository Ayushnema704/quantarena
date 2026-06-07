"""HdrHistogram-based latency tracking — actual + intended (coordinated omission aware)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from hdrh.histogram import HdrHistogram


@dataclass
class LatencyTracker:
    """Tracks actual and intended latency in microseconds."""

    lowest_trackable: int = 1
    highest_trackable: int = 60_000_000  # 60s in µs
    significant_digits: int = 3

    actual: HdrHistogram = field(init=False)
    intended: HdrHistogram = field(init=False)
    event_count: int = 0
    window_start: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.actual = HdrHistogram(
            self.lowest_trackable,
            self.highest_trackable,
            self.significant_digits,
        )
        self.intended = HdrHistogram(
            self.lowest_trackable,
            self.highest_trackable,
            self.significant_digits,
        )

    def record(self, actual_us: float | None, intended_us: float | None) -> None:
        self.event_count += 1
        if actual_us is not None and actual_us >= 0:
            self.actual.record_value(int(actual_us))
        if intended_us is not None and intended_us >= 0:
            self.intended.record_value(int(intended_us))

    def percentile(self, hist: HdrHistogram, p: float) -> float:
        if hist.get_total_count() == 0:
            return 0.0
        return float(hist.get_value_at_percentile(p))

    def snapshot(self) -> dict[str, float]:
        elapsed = max(time.time() - self.window_start, 0.001)
        rps = self.event_count / elapsed
        return {
            "p50_us": self.percentile(self.actual, 50),
            "p90_us": self.percentile(self.actual, 90),
            "p99_us": self.percentile(self.actual, 99),
            "p50_intended_us": self.percentile(self.intended, 50),
            "p90_intended_us": self.percentile(self.intended, 90),
            "p99_intended_us": self.percentile(self.intended, 99),
            "event_count": float(self.event_count),
            "rps": rps,
        }

    def reset_window(self) -> None:
        self.event_count = 0
        self.window_start = time.time()
