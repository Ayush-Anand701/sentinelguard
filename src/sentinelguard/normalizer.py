import unicodedata
import re
import time

# These are Unicode characters that are invisible to the human eye
# but can be used to hide instructions from security filters.
# We strip all of them before anything else sees the text.
INVISIBLE_CHARACTERS = [
    '\u200b',  # zero-width space
    '\u200c',  # zero-width non-joiner
    '\u200d',  # zero-width joiner
    '\u200e',  # left-to-right mark
    '\u200f',  # right-to-left mark
    '\ufeff',  # byte order mark
    '\u00ad',  # soft hyphen
    '\u2060',  # word joiner
    '\u180e',  # mongolian vowel separator
]


class UnicodeNormalizer:
    """
    First line of defense in SentinelGuard.
    Cleans every message before it reaches the drift detector.
    Closes the LlamaFirewall Unicode bypass confirmed May 2025.
    """

    def __init__(self):
        # This list records everything we stripped, for auditing
        self._audit_log = []

    def normalize(self, text: str) -> str:
        """
        Takes a raw user message, cleans it, returns safe text.
        """
        original = text
        self._audit_log = []  # reset log for each new message

        # Step 1 — Strip invisible characters
        for char in INVISIBLE_CHARACTERS:
            if char in text:
                count = text.count(char)
                text = text.replace(char, '')
                self._audit_log.append({
                    "action": "stripped_invisible",
                    "char_code": hex(ord(char)),
                    "count": count
                })

        # Step 2 — NFKC normalization
        # Standardises within same script (e.g. fullwidth → normal)
        text = unicodedata.normalize('NFKC', text)

        # Step 2b — Homoglyph mapping
        # NFKC does NOT map across scripts (Cyrillic → Latin etc.)
        # We do this manually for the most common attack characters
        HOMOGLYPHS = {
            '\u0430': 'a',  # Cyrillic а → Latin a
            '\u0435': 'e',  # Cyrillic е → Latin e
            '\u0456': 'i',  # Cyrillic і → Latin i
            '\u043e': 'o',  # Cyrillic о → Latin o
            '\u0440': 'r',  # Cyrillic р → Latin r
            '\u0441': 'c',  # Cyrillic с → Latin c
            '\u0445': 'x',  # Cyrillic х → Latin x
            '\u0443': 'y',  # Cyrillic у → Latin y
            '\u0042': 'B',  # keep latin B (already correct)
            '\u0392': 'B',  # Greek Β → Latin B
            '\u0391': 'A',  # Greek Α → Latin A
            '\u0395': 'E',  # Greek Ε → Latin E
            '\u0396': 'Z',  # Greek Ζ → Latin Z
            '\u0397': 'H',  # Greek Η → Latin H
            '\u0399': 'I',  # Greek Ι → Latin I
            '\u039a': 'K',  # Greek Κ → Latin K
            '\u039c': 'M',  # Greek Μ → Latin M
            '\u039d': 'N',  # Greek Ν → Latin N
            '\u039f': 'O',  # Greek Ο → Latin O
            '\u03a1': 'R',  # Greek Ρ → Latin R
            '\u03a4': 'T',  # Greek Τ → Latin T
            '\u03a5': 'Y',  # Greek Υ → Latin Y
            '\u03a7': 'X',  # Greek Χ → Latin X
        }
        for foreign_char, latin_equiv in HOMOGLYPHS.items():
            if foreign_char in text:
                text = text.replace(foreign_char, latin_equiv)
                self._audit_log.append({
                    "action": "homoglyph_mapped",
                    "from": hex(ord(foreign_char)),
                    "to": latin_equiv
                })

        # Step 3 — Strip any remaining non-printable control characters
        # (except normal ones like newline \n and tab \t)
        cleaned = []
        for char in text:
            if unicodedata.category(char).startswith('C') and char not in '\n\t\r':
                self._audit_log.append({
                    "action": "stripped_control",
                    "char_code": hex(ord(char))
                })
            else:
                cleaned.append(char)
        text = ''.join(cleaned)

        # Log if anything changed
        if text != original:
            self._audit_log.append({
                "action": "summary",
                "original_length": len(original),
                "cleaned_length": len(text)
            })

        return text

    def get_audit_log(self) -> list:
        """
        Returns a list of everything that was stripped in the last normalize() call.
        Useful for debugging and for the paper's evaluation section.
        """
        return self._audit_log