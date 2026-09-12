# Phase 02: UnicodeNormalizer — Completion Record

## Purpose

The normalizer is SentinelGuard's first processing stage. It removes Unicode
obfuscation before messages are embedded or compared with attack anchors, so
invisible characters and cross-script look-alikes cannot split security-relevant
words such as `ignore`, `previous`, or `password`.

## Delivered behavior

- NFKC compatibility normalization, including full-width Latin characters.
- Removal of zero-width, BOM, soft-hyphen, bidi-override, and other unsafe
  Unicode control/formatting characters while retaining newlines, carriage
  returns, and tabs.
- A small, auditable Cyrillic/Greek homoglyph map for English security prompts.
- `NormalizationResult` metadata: whether the message changed and counts of
  invisible/control characters removed and homoglyphs replaced.
- Public API: `normalize()`, `normalize_text()`, and `NormalizationResult`.

## Drift-detector integration

`IntentDriftDetector.analyse()` normalizes each incoming message before it is
embedded and stored in `ConversationBuffer`. Its existing drift-score formula,
attack anchors, thresholds, and actions are unchanged. Each result now includes
a JSON-safe `normalization` metadata object for Phase 04 risk scoring.

## Validation

- 16 normalizer tests cover no-op input, zero-width and bidi controls, generic
  controls, homoglyphs, NFKC, mixed obfuscation, a realistic regression case,
  idempotence, and the public API.
- Drift-detector integration is tested with a deterministic fake embedder.
- The full real-model drift suite passed with 11 tests.

## Policy note

Cross-script replacement is intentionally security-first and can change
legitimate Greek or Cyrillic content. Preserve the original message separately
when applications need to display or audit multilingual text. Add new mappings
only with a clear attack case and regression test.
