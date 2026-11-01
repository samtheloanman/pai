"""Reversible masking for text that is allowed to go to a cloud model (PRD PRIV-2).

shortcut: regex for emails, US-style phones and the owner's own name tokens, no Presidio/NER, so other people's
names and street addresses pass through; upgrade to Presidio when it can run on the box.
shortcut: placeholders must come back verbatim; a model that rewrites "[EMAIL_1]" leaves it in the reply.
The placeholder->original mapping lives in this object only, for one request, and is never stored or audited.
"""
import re

_EMAIL = ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"))
_PHONE = ("PHONE", re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"))


class Masker:
    def __init__(self, names: list[str]):
        words = {w for n in names for w in re.findall(r"\w+", n) if len(w) >= 2}
        self._pats = [_EMAIL, _PHONE]
        if words:
            alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
            self._pats.append(("NAME", re.compile(rf"(?<!\w)(?:{alt})(?!\w)", re.I)))
        self._ph: dict[tuple[str, str], str] = {}  # (kind, lowercased value) -> placeholder
        self._orig: dict[str, str] = {}  # placeholder -> first-seen original text

    @property
    def count(self) -> int:
        return len(self._orig)

    def _sub(self, kind: str, m: re.Match) -> str:
        key = (kind, m.group().lower())
        if key not in self._ph:
            n = sum(1 for k in self._ph if k[0] == kind) + 1
            self._ph[key] = f"[{kind}_{n}]"
            self._orig[self._ph[key]] = m.group()
        return self._ph[key]

    def mask(self, text: str) -> str:
        for kind, pat in self._pats:
            text = pat.sub(lambda m, k=kind: self._sub(k, m), text)
        return text

    def unmask(self, text: str) -> str:
        for ph, orig in self._orig.items():
            text = text.replace(ph, orig)
        return text
