from backend.cognition.confidence.engine import Evidence, score


def test_empty_is_prior():
    assert score([]).score == 50


def test_more_corroboration_raises_confidence():
    one = score([Evidence(0.7, 1, "support", "sleep")])
    five = score([Evidence(0.7, 1, "support", "sleep") for _ in range(5)])
    assert five.score > one.score


def test_contradiction_lowers_confidence():
    mixed = score([Evidence(0.8, 1, "support", "x"), Evidence(0.8, 1, "contradict", "x")])
    pure = score([Evidence(0.8, 1, "support", "x"), Evidence(0.8, 1, "support", "x")])
    assert mixed.score < pure.score


def test_recency_matters():
    fresh = score([Evidence(0.8, 1, "support", "a") for _ in range(3)])
    stale = score([Evidence(0.8, 400, "support", "a") for _ in range(3)])
    assert fresh.score > stale.score


def test_cross_domain_consistency_helps():
    one_topic = score([Evidence(0.7, 1, "support", "a") for _ in range(3)])
    many_topics = score([Evidence(0.7, 1, "support", t) for t in ("a", "b", "c")])
    assert many_topics.score >= one_topic.score


def test_bounds():
    r = score([Evidence(1.0, 0, "support", f"t{i}") for i in range(20)])
    assert 1 <= r.score <= 99
