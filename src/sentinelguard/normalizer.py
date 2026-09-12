"""Unicode normalization used before SentinelGuard embeds a user message."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# Explicitly listed format characters cover the common zero-width and bidi
# obfuscation techniques. The generic control-character pass below catches
# any remaining Unicode control or formatting characters.
_INVISIBLE_CHARS = frozenset(
    {
        "\u00ad",  # soft hyphen
        "\u180e",  # Mongolian vowel separator
        "\u200b",  # zero-width space
        "\u200c",  # zero-width non-joiner
        "\u200d",  # zero-width joiner
        "\u200e",  # left-to-right mark
        "\u200f",  # right-to-left mark
        "\u202a",  # left-to-right embedding
        "\u202b",  # right-to-left embedding
        "\u202c",  # pop directional formatting
        "\u202d",  # left-to-right override
        "\u202e",  # right-to-left override
        "\u2060",  # word joiner
        "\ufeff",  # byte-order mark / zero-width no-break space
    }
)

# Common cross-script confusables that can disguise English security-sensitive
# words. This is deliberately small and auditable; mapping is intentionally
# lossy for these characters, so callers handling multilingual user content
# should retain the original message for display or audit purposes.
_HOMOGLYPH_MAP = {
    # Cyrillic
    "\u0430": "a", "\u0410": "A",
    "\u0435": "e", "\u0415": "E",
    "\u043e": "o", "\u041e": "O",
    "\u0440": "p", "\u0420": "P",
    "\u0441": "c", "\u0421": "C",
    "\u0443": "y", "\u0423": "Y",
    "\u0445": "x", "\u0425": "X",
    "\u0456": "i", "\u0406": "I",
    "\u0455": "s", "\u04bb": "h", "\u0458": "j",
    "\u0501": "d",
    # Greek
    "\u03b1": "a", "\u0391": "A",
    "\u03b2": "b",
    "\u03bf": "o", "\u039f": "O",
    "\u03c1": "p", "\u03a1": "P",
    "\u03c5": "u", "\u03bd": "v",
}

_ALLOWED_CONTROL_CHARS = frozenset({"\n", "\r", "\t"})


@dataclass(frozen=True)
class NormalizationResult:
    """Cleaned text and security-relevant metadata for one message."""

    original: str
    cleaned: str
    invisible_chars_removed: int = 0
    control_chars_removed: int = 0
    homoglyphs_replaced: int = 0
    unicode_normalized: bool = False
    flagged: bool = field(init=False)

    def __post_init__(self) -> None:
        # NFKC-only transformations (for example, full-width ASCII) are also
        # meaningful obfuscation signals, so compare the final content.
        object.__setattr__(self, "flagged", self.cleaned != self.original)

    def as_dict(self) -> dict[str, int | bool]:
        """Return JSON-safe metadata suitable for detector/API responses."""
        return {
            "flagged": self.flagged,
            "unicode_normalized": self.unicode_normalized,
            "invisible_chars_removed": self.invisible_chars_removed,
            "control_chars_removed": self.control_chars_removed,
            "homoglyphs_replaced": self.homoglyphs_replaced,
        }


def _strip_controls(text: str) -> tuple[str, int, int]:
    """Remove invisible and other non-printable controls, preserving layout."""
    invisible_removed = 0
    control_removed = 0
    cleaned_chars: list[str] = []

    for char in text:
        if char in _INVISIBLE_CHARS:
            invisible_removed += 1
        elif (
            unicodedata.category(char).startswith("C")
            and char not in _ALLOWED_CONTROL_CHARS
        ):
            control_removed += 1
        else:
            cleaned_chars.append(char)

    return "".join(cleaned_chars), invisible_removed, control_removed


def _replace_homoglyphs(text: str) -> tuple[str, int]:
    replacements = 0
    cleaned_chars: list[str] = []
    for char in text:
        replacement = _HOMOGLYPH_MAP.get(char)
        if replacement is None:
            cleaned_chars.append(char)
        else:
            cleaned_chars.append(replacement)
            replacements += 1
    return "".join(cleaned_chars), replacements


def normalize(text: str) -> NormalizationResult:
    """Normalize and clean text before it reaches downstream classifiers."""
    if not isinstance(text, str):
        raise TypeError(f"normalize() expects str, got {type(text).__name__}")

    nfkc_text = unicodedata.normalize("NFKC", text)
    stripped, invisible_count, control_count = _strip_controls(nfkc_text)
    cleaned, homoglyph_count = _replace_homoglyphs(stripped)

    return NormalizationResult(
        original=text,
        cleaned=cleaned,
        invisible_chars_removed=invisible_count,
        control_chars_removed=control_count,
        homoglyphs_replaced=homoglyph_count,
        unicode_normalized=nfkc_text != text,
    )


def normalize_text(text: str) -> str:
    """Convenience wrapper for consumers that only need cleaned text."""
    return normalize(text).cleaned
