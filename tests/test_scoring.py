from shared.scoring import composite_score, score_breakdown, speed_score


def test_speed_lower_latency_scores_higher():
    assert speed_score(1000) > speed_score(50000)


def test_composite_in_range():
    b = score_breakdown(5000, 200, 0.9, 0.01, 1000)
    assert 0 <= b.composite <= 100


def test_weights_sum():
    s = composite_score(10000, 500, 1.0, 0.0, 0.0)
    assert s > 0
