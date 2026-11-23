"""Hard blocks: text that must never leave this box for a cloud model. Reasons never echo the match."""
import re

_SECRETS = re.compile(
    r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[bp]-[A-Za-z0-9-]{10,}"
    r"|nvapi-[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,}|[A-Fa-f0-9]{32,})(?![A-Za-z0-9])"
)
_TOKEN = re.compile(r"[A-Za-z0-9+/_-]{32,}={0,2}")  # generic base64-ish blob; must mix letters and digits
_DIGITS = re.compile(r"\d(?:[^A-Za-z0-9]*\d)+")  # digit groups joined by any run of separators
_SSN = re.compile(r"(?<!\d)\d{3}[^A-Za-z0-9]+\d{2}[^A-Za-z0-9]+\d{4}(?!\d)")
# a bare 9-digit number is only an SSN after a keyword; plain 9-digit numbers stay allowed to limit false positives
_SSN_BARE = re.compile(r"(?i)\b(?:ssn|social)\b\D{0,20}(?<!\d)\d{9}(?!\d)")


_DBL = [n * 2 - 9 if n * 2 > 9 else n * 2 for n in range(10)]


def _has_card(groups: list[str]) -> bool:
    """True if any candidate digit string is 13-19 digits and passes Luhn.

    Candidates: every slice of whole digit groups totalling 13-19 digits, and for one unseparated run every
    13-19 digit window. Cards written in groups are caught with any digits around them. Luhn sums come from
    prefix sums, so each candidate costs O(1) and the whole check is linear in the number of digits.
    """
    d = "".join(groups)
    # ev[k]: Luhn sum of d[:k] doubling even indexes; od[k]: doubling odd indexes
    ev, od = [0], [0]
    for k, c in enumerate(d):
        n = ord(c) - 48
        ev.append(ev[-1] + (_DBL[n] if k % 2 == 0 else n))
        od.append(od[-1] + (n if k % 2 == 0 else _DBL[n]))

    def luhn(a: int, b: int) -> bool:  # d[a:b]; the rightmost digit (b-1) is never doubled
        x = od if (b - 1) % 2 == 0 else ev
        return (x[b] - x[a]) % 10 == 0

    if len(groups) == 1:
        return any(luhn(a, a + n) for n in range(13, 20) for a in range(len(d) - n + 1))
    ends, pos = [], 0
    for g in groups:
        pos += len(g)
        ends.append(pos)
    for i in range(len(groups)):
        a = ends[i] - len(groups[i])
        for j in range(i, len(groups)):  # groups hold >=1 digit, so this stops after at most 19 steps
            n = ends[j] - a
            if n > 19:
                break
            if n >= 13 and luhn(a, ends[j]):
                return True
    return False


def allowed_for_cloud(text: str, off_limits: list[str]) -> tuple[bool, str]:
    for m in _DIGITS.findall(text):
        if _has_card(re.findall(r"\d+", m)):
            return False, "card number"
    if _SECRETS.search(text) or any(re.search(r"\d", t) and re.search(r"[A-Za-z]", t) for t in _TOKEN.findall(text)):
        return False, "secret or key"
    if _SSN.search(text) or _SSN_BARE.search(text):
        return False, "ID number"
    for phrase in off_limits:
        if phrase.strip() and re.search(rf"(?<!\w){re.escape(phrase.strip())}(?!\w)", text, re.I):
            return False, "off-limits topic"
    return True, ""
