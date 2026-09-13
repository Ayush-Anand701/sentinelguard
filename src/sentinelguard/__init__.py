"""
SentinelGuard — Multi-turn prompt injection firewall for LLM applications.

Usage:
    from sentinelguard import SentinelGuard

    sg = SentinelGuard()
    result = sg.check("session_123", "user message here")
    print(result.action)   # "allow", "flag", or "block"
    print(result.risk_score)
"""

from dataclasses import dataclass
from sentinelguard.normalizer import normalize, normalize_text, NormalizationResult
from sentinelguard.drift_detector import (
    MessageEmbedder,
    ConversationBuffer,
    IntentDriftDetector,
)
from sentinelguard.risk_scorer import RiskScorer


@dataclass
class Decision:
    """
    The result of checking one message through SentinelGuard.
    This is what developers get back from sg.check().
    """
    action: str           # "allow", "flag", or "block"
    risk_score: float     # 0.0 to 1.0 — conversation-level risk
    drift_score: float    # 0.0 to 1.0 — this turn's drift
    peak_score: float     # highest drift score seen in this session
    turn_count: int       # how many turns in this session
    closest_attack: str   # which attack type it resembles most
    flagged_by_normalizer: bool  # True if invisible chars were stripped


class SentinelGuard:
    """
    Main entry point for SentinelGuard.

    Drop this into any LLM application to detect multi-turn
    prompt injection attacks before they reach your model.

    Example:
        sg = SentinelGuard()

        # Call on every user message before sending to LLM
        result = sg.check(session_id="user_123", message="user text")

        if result.action == "block":
            return "I can't help with that."
        elif result.action == "flag":
            log_suspicious(result)
            # still allow but log it

        # Safe to send to LLM
        response = llm.chat(message)
    """

    def __init__(
        self,
        window_size: int = 10,
        alpha: float = 0.6,
        beta: float = 0.4,
        flag_threshold: float = 0.35,
        block_threshold: float = 0.65,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        print("Initialising SentinelGuard...")
        self._embedder = MessageEmbedder(model_name=embedding_model)
        self._buffer = ConversationBuffer(window_size=window_size)
        self._detector = IntentDriftDetector(self._embedder, self._buffer)
        self._scorer = RiskScorer(alpha=alpha, beta=beta)
        self._flag_threshold = flag_threshold
        self._block_threshold = block_threshold
        print("SentinelGuard ready.")

    def check(self, session_id: str, message: str) -> Decision:
        """
        Check one message through the full pipeline.
        Call this on every user message before it reaches your LLM.

        Args:
            session_id: unique ID for this conversation (e.g. user ID)
            message: the raw user message

        Returns:
            Decision object with action, scores, and metadata
        """
        # Stage 1 — Normalize
        norm_result = normalize(message)
        clean_text = norm_result.cleaned

        # Stage 2 — Drift detection
        drift_result = self._detector.analyse(session_id, clean_text)

        # Stage 3 — Risk scoring
        self._scorer.add_turn_score(session_id, drift_result["drift_score"])
        risk_result = self._scorer.compute(session_id)

        # Stage 4 — Final decision using configurable thresholds
        risk_score = risk_result["risk_score"]
        if risk_score >= self._block_threshold:
            action = "block"
        elif risk_score >= self._flag_threshold:
            action = "flag"
        else:
            action = "allow"

        return Decision(
            action=action,
            risk_score=risk_score,
            drift_score=drift_result["drift_score"],
            peak_score=risk_result["peak"],
            turn_count=drift_result["turn_count"],
            closest_attack=drift_result["closest_attack"] or "none",
            flagged_by_normalizer=norm_result.flagged,
        )

    def clear_session(self, session_id: str):
        """Call this when a conversation ends to free memory."""
        self._buffer.clear_session(session_id)
        self._scorer.clear_session(session_id)