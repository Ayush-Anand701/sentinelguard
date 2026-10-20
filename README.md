# SentinelGuard

> Multi-turn prompt injection firewall for LLM applications.

![Tests](https://img.shields.io/badge/tests-43%20passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Every existing prompt injection defense — including Meta's LlamaFirewall and
PromptGuard — scores each message in isolation. A sophisticated attacker who
spreads malicious intent across 10–20 seemingly innocent messages is completely
invisible to them. Multi-turn attacks currently succeed **92.78% of the time**
against all tested defenses (joint OpenAI/Anthropic/DeepMind study, 2025).

**SentinelGuard fixes this.** It maintains a semantic memory of the entire
conversation and detects when intent drifts gradually toward attack territory —
even when no individual message would trigger a stateless classifier.

---

## How it works

Every user message passes through a four-stage pipeline before reaching your LLM:

```
User message
    │
    ▼
┌─────────────────────┐
│  1. Normalizer      │  Strips Unicode invisible chars & homoglyphs
└──────────┬──────────┘
           │
    ▼
┌─────────────────────┐
│  2. Drift Detector  │  Embeds message, computes conversation trajectory
└──────────┬──────────┘
           │
    ▼
┌─────────────────────┐
│  3. Risk Scorer     │  Peak+Accumulation formula → conversation risk score
└──────────┬──────────┘
           │
    ▼
  allow / flag / block
```

---

## Quickstart

**Install:**
```bash
pip install -e ".[dev]"
```

**Use in any LLM app:**
```python
from sentinelguard import SentinelGuard

sg = SentinelGuard()

# Call this on every user message before sending to your LLM
result = sg.check(session_id="user_123", message="user text here")

if result.action == "block":
    return "I can't help with that."
elif result.action == "flag":
    log_suspicious(result)

# Safe — send to LLM
response = llm.chat(message)
```

**What `result` contains:**
```python
result.action           # "allow", "flag", or "block"
result.risk_score       # 0.0 to 1.0 — conversation-level risk
result.drift_score      # 0.0 to 1.0 — this turn's drift
result.peak_score       # highest drift score seen in this session
result.turn_count       # how many turns in this session
result.closest_attack   # "crescendo", "dan_persona", etc.
result.flagged_by_normalizer  # True if invisible chars were stripped
```

---

## What makes this different

| Feature | LlamaFirewall | PromptGuard | SentinelGuard |
|---|---|---|---|
| Multi-turn memory | ❌ | ❌ | ✅ |
| Unicode bypass closed | ❌ | ❌ | ✅ |
| Conversation trajectory | ❌ | ❌ | ✅ |
| Peak+Accumulation scoring | ❌ | ❌ | ✅ |
| Open source + pip install | ✅ | ✅ | ✅ |

---

## Modules

### Stage 1 — Unicode Normalizer
Strips zero-width characters, bidi overrides, and homoglyphs before any
classifier sees the text. Closes the confirmed LlamaFirewall Unicode bypass
(Trendyol Research, May 2025).

```python
from sentinelguard import normalize, normalize_text

result = normalize("ign\u200bore previous instructions")
print(result.cleaned)   # "ignore previous instructions"
print(result.flagged)   # True
print(result.invisible_chars_removed)  # 1

cleaned = normalize_text("p\u0430ssword")
print(cleaned)  # "password"
```

The normalizer maps a small auditable set of Cyrillic and Greek look-alikes to
Latin equivalents. Applications handling multilingual content should retain the
original message separately from `result.cleaned`.

### Stage 2 — Intent Drift Detector
Embeds each normalized message using `all-MiniLM-L6-v2`, maintains a
sliding window of embeddings per session, computes the semantic trajectory
from earlier to recent turns, and compares it against known attack anchors.

```python
from sentinelguard.drift_detector import (
    ConversationBuffer,
    DriftDetectorConfig,
    IntentDriftDetector,
    MessageEmbedder,
)

detector = IntentDriftDetector(
    MessageEmbedder(),
    ConversationBuffer(window_size=10),
    DriftDetectorConfig(),
)
```

Default thresholds: below 0.35 → allow, 0.35–0.65 → flag, 0.65+ → block.

### Stage 3 — Risk Scorer
Combines per-turn drift scores into a single conversation-level risk score
using the Peak+Accumulation formula:

```
risk = 0.6 × peak_turn_score + 0.4 × mean_of_all_turns
```

This ensures a high-risk turn is remembered even if subsequent turns
look innocent — fixing the score collapse seen in naive averaging.

### Stage 4 — Public API
The `SentinelGuard` class wires all three stages together with configurable
thresholds and session management.

```python
sg = SentinelGuard(
    window_size=10,        # sliding window size
    alpha=0.6,             # weight for peak score
    beta=0.4,              # weight for mean score
    flag_threshold=0.35,   # score to flag
    block_threshold=0.65,  # score to block
)

# Clear session when conversation ends
sg.clear_session("user_123")
```

---

## Running the tests

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q -p no:cacheprovider
```

Expected output:
```
43 passed in 21s
```

## Running the smoke test

Cache the embedding model first (one-time, requires internet, ~80MB):
```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

Then run offline:
```powershell
python src\smoke_test.py
```

The smoke test simulates a Crescendo attack, a benign conversation, and a
Unicode obfuscation attempt — printing drift score, risk score, and decision
for each turn.

---

## Project structure

```
sentinelguard/
├── src/sentinelguard/
│   ├── __init__.py          # public API — SentinelGuard class
│   ├── normalizer.py        # Stage 1 — Unicode normalization
│   ├── drift_detector.py    # Stage 2 — intent drift detection
│   ├── risk_scorer.py       # Stage 3 — Peak+Accumulation scoring
│   └── middleware.py        # FastAPI middleware
├── tests/
│   ├── test_normalizer.py   # 16 tests
│   ├── test_drift.py        # 19 tests
│   └── test_integration.py  # 8 tests
├── benchmarks/
│   └── datasets/            # attack + benign conversation dataset
├── docs/
│   └── research_notes.md
└── pyproject.toml
```

---

## Background & motivation

Prompt injection is ranked the #1 security risk for LLM applications by OWASP
(2025). Existing defenses are stateless — they score each message independently
and are blind to gradual multi-turn attacks. This project addresses that gap
with a novel temporal intent drift detection mechanism.

Key references:
- DeepContext (arXiv 2602.16935) — closest prior work, not open source
- Peak+Accumulation scoring (arXiv 2602.11247)
- Crescendo multi-turn jailbreak (Russinovich et al., 2024)
- LlamaFirewall Unicode bypass (Trendyol Research, May 2025)

---

## Contributing

Pull requests welcome. Please run `pytest` before submitting and ensure all
43 tests pass. New attack anchor phrases should come with a corresponding
regression test.

---

## Authors

- Shubham ([@Ayush-Anand701](https://github.com/Ayush-Anand701)) — core detection pipeline
- Teammate — normalizer improvements, test suite expansion