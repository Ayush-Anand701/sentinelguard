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
