"""Rule-based segmentation of agreement text into clause-sized pieces (Phase 3).

Works on plain text (copy-paste or .txt). PDF / DOCX extraction comes in the API phase.
Heuristics, deliberately simple and transparent:
- a new clause starts at a top-level number ("1.", "1)", "Clause 1:", "ARTICLE IV.");
- without numbering, blank-line paragraphs are clauses;
- "IN WITNESS WHEREOF", signature lines and Schedules start a trailer segment;
- over-long clauses are split at sub-numbers "(a)", "1.1", then at sentence boundaries;
- an ALL-CAPS or "Title Case:" heading is separated from the body.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from clauselens.data.text import normalize_text

_NUM = re.compile(
    r"""^\s*(?P<num>
          (?i:clause|section|article)\s+(?:\d+(?:\.\d+)*|[IVXLCivxlc]+)[.)]?
        | \d+(?:\.\d+)+[.)]?
        | \d+[.)]
        | \((?:\d{1,2}|[a-zA-Z]|[ivxIVX]{2,4})\)
        | [IVXLC]{1,5}[.)]
        | [A-Z][.)]
      )(?:(?:\s*[:\-–]\s*|\s+)(?P<rest>\S.*))?$""",
    re.X,
)
_TRAILER = re.compile(
    r"^\s*(?:(?i:in\s+witness\s+whereof)|(?:Signed|SIGNED|Executed|EXECUTED|Accepted|ACCEPTED|"
    r"Witnesses?|WITNESSES?|Yours\s+(?:sincerely|faithfully))\b)"
)
_ANNEX = re.compile(r"^\s*(?:Schedule|SCHEDULE|Annexure|ANNEXURE|Annex|ANNEX)\b")
_UNIT_START = re.compile(r"(?i)(?:days?|months?|years?|hours?|weeks?|per\b|percent|%)")
_NOISE = re.compile(r"^\s*(?:page\s+\d+(?:\s+of\s+\d+)?|-\s*\d+\s*-)\s*$", re.I)
_INLINE_HEADING = re.compile(r"^(?P<h>[A-Z][A-Za-z0-9&/,'()\- ]{1,60}?):\s+(?P<b>\S.*)$")
_SENTENCE_END = re.compile(r"(?<=[.;?!])\s+(?=[A-Z(\"'])")
_ABBREVIATIONS = frozenset(
    {"rs", "no", "nos", "mr", "mrs", "ms", "dr", "sr", "jr", "vs", "etc", "viz", "ltd", "pvt",
     "inc", "co", "dt", "sec", "art", "cl", "st", "approx", "i.e", "e.g", "smt", "shri"}
)  # fmt: skip
_SMALL_WORDS = frozenset({"of", "and", "the", "for", "to", "in", "on", "or", "&"})


@dataclass(frozen=True, slots=True)
class Segment:
    index: int
    text: str  # whitespace-normalised body, without number and heading
    start: int  # character offsets into the original text
    end: int
    number: str | None
    heading: str | None
    kind: str  # "clause" | "preamble" | "trailer"

    @property
    def n_words(self) -> int:
        return len(self.text.split())


@dataclass(slots=True)
class _Line:
    start: int
    end: int
    raw: str
    kind: str  # blank | number | trailer | text
    number: str | None = None
    rest: str = ""
    level: int = 0
    annex: bool = False


def _level(num: str) -> int:
    n = num.strip()
    if re.match(r"(?i)(clause|section|article)\b", n):
        return 1
    if re.fullmatch(r"\d+[.)]|[IVXLC]{1,5}[.)]", n):
        return 1
    if re.fullmatch(r"\d+(?:\.\d+)+[.)]?", n):
        return 1 + n.rstrip(".)").count(".")
    return 2


def _is_false_number(m: re.Match[str]) -> bool:
    """Wrapped fragments that only look like numbering: "(3) months ...", "1.5 percent", "2025."."""
    num = m["num"].lstrip("(")
    if not num[:1].isdigit():
        return False
    return bool(re.match(r"\d{3,}", num) or _UNIT_START.match(m["rest"] or ""))


def _scan(text: str) -> list[_Line]:
    lines: list[_Line] = []
    pos = 0
    for raw in text.splitlines(keepends=True):
        body = raw.rstrip("\r\n")
        start, end = pos, pos + len(body)
        pos += len(raw)
        n_words = len(body.split())
        if not body.strip() or _NOISE.match(body):
            lines.append(_Line(start, end, body, "blank"))
        elif (m := _NUM.match(body)) and not _is_false_number(m):
            lines.append(
                _Line(start, end, body, "number", m["num"].strip(), (m["rest"] or "").strip(),
                      _level(m["num"]))
            )  # fmt: skip
        elif (
            re.match(r"(?i)\s*in\s+witness\s+whereof", body)
            or (_TRAILER.match(body) and n_words <= 20)
            or (_ANNEX.match(body) and n_words <= 6)
        ):
            lines.append(_Line(start, end, body, "trailer", annex=bool(_ANNEX.match(body))))
        else:
            lines.append(_Line(start, end, body, "text"))
    return lines


def _is_heading(s: str) -> bool:
    s = s.strip().rstrip(":.-– ")
    letters = [c for c in s if c.isalpha()]
    return (
        bool(letters)
        and 1 <= len(s.split()) <= 8
        and len(s) <= 70
        and all(c.isupper() for c in letters)
    )


def _is_title(s: str) -> bool:
    words = s.split()
    return 1 <= len(words) <= 6 and all(w[0].isupper() or w.lower() in _SMALL_WORDS for w in words)


def _split_heading(first_line: str) -> tuple[str | None, str]:
    m = _INLINE_HEADING.match(first_line)
    if m and (_is_heading(m["h"]) or _is_title(m["h"])):
        return m["h"].strip(), m["b"]
    return None, first_line


def split_sentences(text: str) -> list[str]:
    """Sentence split that does not break after Rs., No., Mr., i.e., initials, etc."""
    out: list[str] = []
    start = 0
    for m in _SENTENCE_END.finditer(text):
        before = text[start : m.start()]
        words = before.split()
        last = words[-1].rstrip(".;?!").lower() if words else ""
        is_abbreviation = last in _ABBREVIATIONS or (len(last) == 1 and last.isalpha())
        if text[m.start() - 1] == "." and is_abbreviation:
            continue
        out.append(before.strip())
        start = m.end()
    out.append(text[start:].strip())
    return [s for s in out if s]


def _pack(body: str, max_words: int) -> list[str]:
    if len(body.split()) <= max_words:
        return [body]
    parts: list[str] = []
    current: list[str] = []
    count = 0
    for sentence in split_sentences(body):
        n = len(sentence.split())
        if current and count + n > max_words:
            parts.append(" ".join(current))
            current, count = [], 0
        current.append(sentence)
        count += n
    if current:
        parts.append(" ".join(current))
    return parts


def _build(lines: list[_Line], s: int, e: int, kind: str):
    idx = [i for i in range(s, e) if lines[i].kind != "blank"]
    first = lines[idx[0]]
    number = first.number if first.kind == "number" else None
    pieces = [first.rest if first.kind == "number" else first.raw.strip()]
    pieces += [lines[i].raw.strip() for i in idx[1:]]
    pieces = [p for p in pieces if p]
    heading = None
    if kind == "clause" and pieces:
        if len(pieces) >= 2 and _is_heading(pieces[0]):
            heading, pieces = pieces[0].strip().rstrip(":.-– "), pieces[1:]
        else:
            heading, pieces[0] = _split_heading(pieces[0])
    body = normalize_text(" ".join(pieces))
    return body, number, heading, first.start, lines[idx[-1]].end


def segment_document(text: str, *, max_words: int = 150) -> list[Segment]:
    lines = _scan(text)
    nonblank = [i for i, ln in enumerate(lines) if ln.kind != "blank"]
    if not nonblank:
        return []
    # Numbers inside the signature block ("Witnesses: 1. ___") must not define the structure.
    first_trailer = next((i for i, ln in enumerate(lines) if ln.kind == "trailer"), len(lines))
    levels = [ln.level for ln in lines[:first_trailer] if ln.kind == "number"]
    top = min(levels) if levels else None

    boundaries: list[int] = []
    in_trailer, prev_blank = False, True
    for i, ln in enumerate(lines):
        if ln.kind == "blank":
            prev_blank = True
            continue
        if ln.kind == "trailer":
            if not in_trailer or ln.annex:
                boundaries.append(i)
            in_trailer = True
        elif not in_trailer:
            numbered_start = ln.kind == "number" and ln.level == top
            if numbered_start or (top is None and prev_blank):
                boundaries.append(i)
        prev_blank = False

    spans: list[tuple[int, int, str]] = []
    if boundaries[0] > nonblank[0]:
        spans.append((nonblank[0], boundaries[0], "preamble"))
    for k, s in enumerate(boundaries):
        e = boundaries[k + 1] if k + 1 < len(boundaries) else len(lines)
        spans.append((s, e, "trailer" if lines[s].kind == "trailer" else "clause"))

    expanded: list[tuple[int, int, str]] = []
    for s, e, kind in spans:
        words = sum(len(lines[i].raw.split()) for i in range(s, e))
        subs = [
            i for i in range(s + 1, e) if lines[i].kind == "number" and lines[i].level > (top or 0)
        ]
        if kind == "clause" and top is not None and words > max_words and subs:
            cuts = [s, *subs, e]
            expanded += [(a, b, kind) for a, b in zip(cuts, cuts[1:], strict=False)]
        else:
            expanded.append((s, e, kind))

    segments: list[Segment] = []
    for s, e, kind in expanded:
        body, number, heading, start, end = _build(lines, s, e, kind)
        if not body:
            continue
        for part in _pack(body, max_words) if kind == "clause" else [body]:
            segments.append(Segment(len(segments), part, start, end, number, heading, kind))
    return segments


def clause_recovery(gt_texts: Iterable[str], segments: Sequence[Segment]) -> tuple[int, int]:
    """How many ground-truth clause texts appear exactly (after whitespace normalisation)."""
    found = {normalize_text(s.text) for s in segments}
    gt = [normalize_text(t) for t in gt_texts]
    return sum(t in found for t in gt), len(gt)
