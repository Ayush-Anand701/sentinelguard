# SentinelGuard — Team Continuity Document

**Team:** Shubham + You (2-member project)
**Repo:** https://github.com/Ayush-Anand701/sentinelguard
**Branch:** `main`
**Virtual environment:** `.venv` (Windows: activate with `.venv\Scripts\activate`, do this every time you reopen VS Code)

---

## Work split (as of today)

| Owner | Work item | Status |
|---|---|---|
| Shubham | Phase 01 — Environment + research | ✅ Done |
| **You** | **Phase 02 — UnicodeNormalizer** | ▶ Your first task |
| Shubham | Phase 03 — IntentDriftDetector | ▶ His next task (needs the paper details he already read) |
| Both | Phase 04 — RiskScorer + FeedbackLoop | ⏳ Pending — split further once you're both up to speed |
| Both | Phase 05 — pip library + FastAPI middleware | ⏳ Pending — integration work |
| Both | Phase 06 — Benchmark + paper + patent | ⏳ Pending |

**Rationale:** Shubham read all 3 research papers and ran the manual attack experiments, so he has the context to build the drift-detection logic correctly. Phase 02 (Normalizer) is self-contained and doesn't require that research background, so it's a good on-ramp for you into the codebase, style, and testing setup. Once you've shipped Phase 02, you'll have enough context to pair with Shubham on Phase 03, or take point on Phase 04.

---

## Project folder structure

```
sentinelguard/
├── src/sentinelguard/
│   ├── __init__.py
│   ├── normalizer.py      ← YOUR FILE — build this first
│   ├── drift_detector.py  ← Shubham, Phase 03
│   ├── risk_scorer.py     ← Phase 04
│   ├── feedback.py        ← Phase 04
│   └── middleware.py      ← Phase 05
├── tests/
│   ├── __init__.py
│   ├── test_normalizer.py ← You'll also write/extend this
│   ├── test_drift.py
│   └── test_integration.py
├── benchmarks/datasets/
├── notebooks/
├── docs/
│   └── research_notes.md
├── pyproject.toml
└── README.md
```

---

## Tech stack

| Layer | Tool |
|---|---|
| Language | Python 3.11+ |
| Embeddings | sentence-transformers (dev: `all-MiniLM-L6-v2`, production: `all-mpnet-base-v2`) |
| API / Middleware | FastAPI |
| Testing | pytest |
| Packaging | pyproject.toml + hatchling |
| Version control | Git + GitHub |

---

## What's already DONE (Phase 01 — by Shubham)

- Environment: `.venv` created, all dependencies installed (sentence-transformers, numpy, fastapi, uvicorn, pytest, black), full folder structure created, Git + GitHub set up (PAT auth), GitHub Actions CI configured.
- Research: all 3 papers read and documented in `docs/research_notes.md`:
  - **Paper 1 — DeepContext** (arXiv 2602.16935): F1 = 0.84, RNN hidden-state architecture, "glass cannon effect" is a noted limitation.
  - **Paper 2 — Peak+Accumulation** (arXiv 2602.11247): full scoring formula documented (see below).
  - **Paper 3 — Crescendo** (Russinovich et al., 2024): attacks typically take ~5 turns, drift becomes visible from turn 3–4.
- Manual attack experiments run on GPT-4o: Crescendo, DAN/persona, fictional framing, gradual erosion.
- AI Lab Project Review Document generated (.docx, 5 sections, 11 related works table).
- Resume bullet points written for SentinelGuard.
- Professor meeting prep done (patent angle, Q&A, meeting tips).

**Ask Shubham for `docs/research_notes.md`** if you haven't seen it — it has the actual attack transcripts and findings, which will help you understand *why* the normalizer matters (it closes a real bypass, see below).

---

## YOUR TASK: Phase 02 — Build the UnicodeNormalizer (Week 2)

**File to create/edit:** `src/sentinelguard/normalizer.py`

**What it does:** Strips Unicode invisible characters, normalizes homoglyphs, and cleans text *before* any classifier sees it. This closes the confirmed LlamaFirewall Unicode bypass (May 2025) — attackers can hide malicious instructions using invisible Unicode characters or lookalike characters (homoglyphs) that visually resemble Latin letters but aren't, which lets them slip past keyword/pattern-based filters.

**Suggested scope for your implementation:**
1. Strip zero-width and other invisible/control Unicode characters (e.g. zero-width space, zero-width joiner, bidi override characters).
2. Normalize Unicode forms (NFKC/NFKD normalization) to fold visually-similar characters to a canonical form.
3. Detect/map common homoglyphs (e.g. Cyrillic "а" vs Latin "a") to their Latin equivalents.
4. Return cleaned text, and ideally flag/log when normalization actually changed something (useful signal for the RiskScorer later).
5. Write tests in `tests/test_normalizer.py` covering: zero-width character stripping, homoglyph substitution, mixed-script strings, and a no-op case (already-clean text should pass through unchanged).

**Suggested starter checklist:**
- [ ] Research the LlamaFirewall Unicode bypass writeup so you know the exact attack shape you're closing
- [ ] Implement `normalize(text: str) -> str` (or similar signature — align naming with whatever `drift_detector.py` will expect as input)
- [ ] Add homoglyph mapping table (can start small, expand later)
- [ ] Write pytest cases
- [ ] Run `pytest tests/test_normalizer.py` locally before pushing
- [ ] Open a PR against `main` rather than pushing directly, so Shubham can review

---

## Full 6-phase roadmap (for reference)

| Phase | What | Timeline | Status |
|---|---|---|---|
| 01 | Environment + research | Week 1 | ✅ Done (Shubham) |
| 02 | UnicodeNormalizer | Week 2 | ▶ **You — next** |
| 03 | IntentDriftDetector | Weeks 3–4 | ⏳ Pending (Shubham) |
| 04 | RiskScorer + FeedbackLoop | Week 5 | ⏳ Pending (Both) |
| 05 | pip library + FastAPI middleware | Week 6 | ⏳ Pending (Both) |
| 06 | Benchmark + paper + patent | Weeks 7–8 | ⏳ Pending (Both) |

---

## Key decisions already made (don't relitigate these without discussing)

| Decision | What was decided |
|---|---|
| Embedding model | `all-MiniLM-L6-v2` (dev), `all-mpnet-base-v2` (production) |
| Sliding window size | Default 10 turns |
| Risk thresholds | LOW < 0.35, MEDIUM 0.35–0.65, HIGH > 0.65 |
| Scoring formula | Peak+Accumulation: `score = 0.6 × peak + 0.4 × sum` (constants: ρ=0.45, δ=0.15, βe=0.2, βr=0.7, threshold=0.7) |
| Branch name | `main` (not `master`) |
| GitHub auth | Personal Access Token (PAT), stored in remote URL |
| Patent type | Provisional patent (USPTO, ~$320, file in Week 8) |

---

## Important technical context

**Branch naming:** `git status` may show "On branch master" locally in old clones, but the actual remote push target is `main`. Always use:
```
git push origin main
```

**Reactivating the virtual environment** (every time you reopen VS Code):
```
.venv\Scripts\activate
```

---

## Questions to sync with Shubham on

- What input/output format should `normalizer.py` expose so `drift_detector.py` (Phase 03) can consume it cleanly? (e.g. does drift_detector expect a plain string, or a struct with metadata about what was normalized?)
- Should normalization flags feed into the RiskScorer (Phase 04) as a signal, or stay purely a pre-processing step?
- Get access to `docs/research_notes.md` and the manual attack transcripts, since they'll be useful when you move to Phase 04.

---

## Phase 02 completion update (2026-09-12)

Phase 02 is complete and integrated with `IntentDriftDetector`.

- `normalizer.py` now exposes `normalize()`, `normalize_text()`, and a
  `NormalizationResult` containing cleaned text and normalization metadata.
- The normalizer removes invisible, bidi, and other unsafe control characters,
  applies NFKC, and maps a small audited set of common homoglyphs.
- `IntentDriftDetector.analyse()` normalizes before embedding and includes a
  JSON-safe `normalization` field in its result. Its trajectory formula, attack
  anchors, thresholds, and allow/flag/block logic are unchanged.
- Validation completed: 16 normalizer tests and 11 full drift-detector tests
  passed. See `docs/phase_02_normalizer.md` for the handoff record.

Next: coordinate Phase 04 ownership (RiskScorer + FeedbackLoop), including how
the normalizer metadata should contribute to the risk score.
