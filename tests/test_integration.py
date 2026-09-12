from sentinelguard.risk_scorer import RiskScorer


def test_empty_session_returns_zero():
    scorer = RiskScorer()
    result = scorer.compute("session_x")
    assert result["risk_score"] == 0.0
    assert result["action"] == "allow"
    assert result["turn_count"] == 0


def test_single_low_score_allows():
    scorer = RiskScorer()
    scorer.add_turn_score("s1", 0.1)
    result = scorer.compute("s1")
    assert result["action"] == "allow"
    assert result["risk_score"] < 0.35


def test_single_high_score_blocks():
    scorer = RiskScorer()
    scorer.add_turn_score("s1", 0.9)
    result = scorer.compute("s1")
    assert result["action"] == "block"
    assert result["risk_score"] >= 0.65


def test_peak_is_remembered():
    scorer = RiskScorer()
    # Turn 3 spikes high, turn 4 drops back low
    # This is exactly what we saw in the smoke test
    scores = [0.1, 0.2, 0.8, 0.15]
    for s in scores:
        scorer.add_turn_score("s1", s)
    result = scorer.compute("s1")
    # Peak was 0.8 — risk score must stay elevated
    assert result["peak"] == 0.8
    assert result["risk_score"] > 0.35


def test_peak_accumulation_formula():
    scorer = RiskScorer(alpha=0.6, beta=0.4)
    scorer.add_turn_score("s1", 0.8)
    scorer.add_turn_score("s1", 0.4)
    result = scorer.compute("s1")
    peak = 0.8
    mean = (0.8 + 0.4) / 2
    expected = round(0.6 * peak + 0.4 * mean, 4)
    assert result["risk_score"] == expected


def test_multiple_sessions_independent():
    scorer = RiskScorer()
    scorer.add_turn_score("alice", 0.9)
    scorer.add_turn_score("bob", 0.1)
    alice = scorer.compute("alice")
    bob = scorer.compute("bob")
    assert alice["action"] == "block"
    assert bob["action"] == "allow"


def test_clear_session_resets_scores():
    scorer = RiskScorer()
    scorer.add_turn_score("s1", 0.9)
    scorer.clear_session("s1")
    result = scorer.compute("s1")
    assert result["risk_score"] == 0.0


def test_medium_score_flags():
    scorer = RiskScorer()
    scorer.add_turn_score("s1", 0.5)
    scorer.add_turn_score("s1", 0.55)
    result = scorer.compute("s1")
    assert result["action"] == "flag"