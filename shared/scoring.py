"""Composite leaderboard scoring with documented sub-scores."""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_WEIGHTS = (0.35, 0.25, 0.25, 0.15)


def speed_score(p99_latency_us: float, baseline_us: float = 50_000.0) -> float:
    if p99_latency_us <= 0:
        return 100.0
    ratio = baseline_us / max(p99_latency_us, 1.0)
    return min(100.0, max(0.0, ratio * 50.0))


def throughput_score(rps: float, target_rps: float = 1000.0) -> float:
    return min(100.0, max(0.0, (rps / target_rps) * 100.0))


def correctness_score(fill_match_rate: float) -> float:
    return min(100.0, max(0.0, fill_match_rate * 100.0))


def stability_score(error_rate: float, latency_variance: float) -> float:
    err_penalty = min(100.0, error_rate * 1000.0)
    var_penalty = min(50.0, latency_variance / 1000.0)
    return max(0.0, 100.0 - err_penalty - var_penalty)


@dataclass
class ScoreBreakdown:
    speed: float
    throughput: float
    correctness: float
    stability: float
    composite: float


def score_breakdown(
    p99_us: float,
    rps: float,
    fill_match_rate: float = 1.0,
    error_rate: float = 0.0,
    latency_variance: float = 0.0,
    weights: tuple[float, float, float, float] = DEFAULT_WEIGHTS,
) -> ScoreBreakdown:
    w1, w2, w3, w4 = weights
    s = speed_score(p99_us)
    t = throughput_score(rps)
    c = correctness_score(fill_match_rate)
    st = stability_score(error_rate, latency_variance)
    composite = w1 * s + w2 * t + w3 * c + w4 * st
    return ScoreBreakdown(s, t, c, st, composite)


def composite_score(
    p99_us: float,
    rps: float,
    fill_match_rate: float = 1.0,
    error_rate: float = 0.0,
    latency_variance: float = 0.0,
    weights: tuple[float, float, float, float] = DEFAULT_WEIGHTS,
) -> float:
    return score_breakdown(
        p99_us, rps, fill_match_rate, error_rate, latency_variance, weights
    ).composite
