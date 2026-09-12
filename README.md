# SentinelGuard

SentinelGuard is a Python middleware project for detecting multi-turn prompt
injection and intent drift. It normalizes user text before it is embedded and
compared with known attack trajectories.

## Setup

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q -p no:cacheprovider
```

## Phase 02: Unicode normalization

Use the public API before sending text to another classifier:

```python
from sentinelguard import normalize, normalize_text

result = normalize("ign\u200bore previous instructions")
assert result.cleaned == "ignore previous instructions"
assert result.flagged

cleaned_text = normalize_text("p\u0430ssword")
assert cleaned_text == "password"
```

`normalize()` returns a `NormalizationResult` containing the cleaned text and
JSON-safe counters for invisible characters, generic control characters, and
homoglyph substitutions. `IntentDriftDetector.analyse()` performs this step
automatically and includes that metadata under `result["normalization"]`.

### Multilingual-content policy

The normalizer is security-first for English-language prompts. It maps a small,
auditable set of Cyrillic and Greek look-alikes to Latin equivalents because
these characters can hide attack keywords from filters. This is intentionally
lossy for those characters, so applications that display or audit multilingual
content should retain the original message separately from `result.cleaned`.

The mapping table is deliberately limited. Add a character only when there is a
clear visual-confusion or attack-regression case, along with a test.

## Phase 03: intent-drift detection

`IntentDriftDetector` embeds each normalized message, retains a sliding window
per session, computes the semantic direction from earlier to recent turns, and
compares that direction with representative attack anchors. The default window
is 10 turns; scores below 0.35 allow, scores from 0.35 to below 0.65 flag, and
scores at or above 0.65 block.

The defaults are explicit and configurable without changing current behavior:

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

`DriftDetectorConfig(min_turns_for_action=3)` is available for experiments
where actioning should wait for a third turn; the default remains 2 turns to
preserve the original Phase 03 behavior.

## Presentation checklist

In PowerShell, from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q -p no:cacheprovider
python src\smoke_test.py
```

The smoke test runs in offline mode so it will not depend on internet access
while presenting. Before the presentation, while connected to the internet,
cache the model once:

```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

`all-MiniLM-L6-v2` is about 80 MB. The smoke test prints every conversation
turn's drift score, decision, closest attack anchor, and Unicode-obfuscation
flag.
