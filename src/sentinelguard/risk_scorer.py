class RiskScorer:
    """
    Combines per-turn drift scores into a single conversation-level
    risk score using the Peak+Accumulation formula.

    Fixes the main weakness of the drift detector alone:
    if turn 3 scores high but turn 4 scores low, a naive system
    would drop the alert. RiskScorer remembers the peak and keeps
    the risk elevated.

    Formula: score = alpha x peak + beta x mean
    Default: score = 0.6 x peak + 0.4 x mean_of_all_turns
    """

    def __init__(self, alpha: float = 0.6, beta: float = 0.4):
        # alpha weights the single worst turn
        # beta weights the average across all turns
        self.alpha = alpha
        self.beta = beta

        # Per-session history of drift scores
        self._session_scores: dict[str, list[float]] = {}

    def add_turn_score(self, session_id: str, drift_score: float):
        """Record a new per-turn drift score for a session."""
        if session_id not in self._session_scores:
            self._session_scores[session_id] = []
        self._session_scores[session_id].append(drift_score)

    def compute(self, session_id: str) -> dict:
        """
        Compute the conversation-level risk score for a session.

        Returns:
            risk_score: float 0-1 (final combined score)
            peak: float (highest single turn score seen)
            mean: float (average across all turns)
            turn_count: int (how many turns scored so far)
            action: str ("allow", "flag", or "block")
        """
        scores = self._session_scores.get(session_id, [])

        if not scores:
            return {
                "risk_score": 0.0,
                "peak": 0.0,
                "mean": 0.0,
                "turn_count": 0,
                "action": "allow"
            }

        peak = max(scores)
        mean = sum(scores) / len(scores)

        # Peak+Accumulation formula
        risk_score = round(
            min(1.0, self.alpha * peak + self.beta * mean), 4
        )

        # Determine action
        if risk_score < 0.35:
            action = "allow"
        elif risk_score < 0.65:
            action = "flag"
        else:
            action = "block"

        return {
            "risk_score": risk_score,
            "peak": round(peak, 4),
            "mean": round(mean, 4),
            "turn_count": len(scores),
            "action": action
        }

    def get_scores(self, session_id: str) -> list[float]:
        """Return the raw per-turn score history for a session."""
        return self._session_scores.get(session_id, [])

    def clear_session(self, session_id: str):
        """Clear a session's score history."""
        if session_id in self._session_scores:
            del self._session_scores[session_id]