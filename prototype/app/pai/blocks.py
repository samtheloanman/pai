"""Hard blocks: text that must never leave this box for a cloud model. Reasons never echo the match."""
import re

_SECRETS = re.compile(
    r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[bp]-[A-Za-z0-9-]{10,}"
    r"|nvapi-[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,}|[A-Fa-f0-9]{32,})(?![A-Za-z0-9])"
)
_TOKEN = re.compile(r"[A-Za-z0-9+/_-]{32,}={0,2}")  # generic base64-ish blob; must mix letters and digits
_DIGITS = re.compile(r"\d(?:[ -]?\d){12,18}")
_SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")


def _luhn(d: str) -> bool:
    s = sum((n * 2 - 9 if n * 2 > 9 else n * 2) if i % 2 else n for i, n in enumerate(int(c) for c in reversed(d)))
    return s % 10 == 0


def allowed_for_cloud(text: str, off_limits: list[str]) -> tuple[bool, str]:
    if any(_luhn(re.sub(r"\D", "", m)) for m in _DIGITS.findall(text)):
        return False, "card number"
    if _SECRETS.search(text) or any(re.search(r"\d", t) and re.search(r"[A-Za-z]", t) for t in _TOKEN.findall(text)):
        return False, "secret or key"
    if _SSN.search(text):
        return False, "ID number"
    for phrase in off_limits:
        if phrase.strip() and re.search(rf"(?<!\w){re.escape(phrase.strip())}(?!\w)", text, re.I):
            return False, "off-limits topic"
    return True, ""
