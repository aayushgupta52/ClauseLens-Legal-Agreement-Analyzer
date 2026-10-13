"""Template-based synthetic clauses and documents (Phase 2)."""

from __future__ import annotations

import hashlib
import itertools
import random
import re
import textwrap
from collections import Counter
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel

from clauselens.data.dedupe import find_near_duplicates
from clauselens.schemas import ClauseRecord
from clauselens.synth.templates import COMMON, FILLERS, ORDER, SPECS

RISKS = ("green", "amber", "red")
OTHER = "other"
NUMBERINGS = ("dot", "paren", "clause", "article", "none")
HEADINGS = ("inline", "line", "none")

ROLE_SETS: dict[str, list[dict[str, str]]] = {
    "rent_agreement": [
        {"owner": "Owner", "tenant": "Tenant"},
        {"owner": "Licensor", "tenant": "Licensee"},
        {"owner": "Landlord", "tenant": "Tenant"},
    ],
    "offer_and_bond": [
        {"employer": "Company", "employee": "Employee"},
        {"employer": "Employer", "employee": "Intern"},
        {"employer": "Organisation", "employee": "Trainee"},
    ],
}
ROLE_SLOTS = frozenset({"owner", "tenant", "employer", "employee"})
_NAME_SLOTS = ("owner_name", "tenant_name", "employee_name")

_FIRST = ("Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Rohan", "Neha")
_LAST = ("Sharma", "Patil", "Iyer", "Gupta", "Desai", "Khan", "Nair", "Joshi")
_COMPANY = ("Nimbus Infotech Pvt. Ltd.", "Orchid Analytics Private Limited", "Kestrel Labs LLP")
_CITIES = ("Mumbai", "Thane", "Navi Mumbai", "Pune")
_LOCALITIES = ("Andheri West", "Powai", "Borivali East", "Vashi", "Kothrud", "Mulund West")
_DESIGNATIONS = ("Graduate Engineer Trainee", "Software Engineer", "Data Analyst Intern")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December")  # fmt: skip
_WORDS = {1: "one", 2: "two", 3: "three", 6: "six", 7: "seven", 10: "ten", 11: "eleven",
          12: "twelve", 15: "fifteen", 24: "twenty-four", 30: "thirty", 45: "forty-five",
          48: "forty-eight", 60: "sixty", 90: "ninety"}  # fmt: skip


def inr(n: int) -> str:
    """Indian digit grouping: 150000 -> '1,50,000'."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail, groups = s[:-3], s[-3:], []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join([*groups, tail])


def _money(rng: random.Random, lo: int, hi: int, step: int) -> str:
    fmt = rng.choice(("Rs. {}/-", "Rs.{}/-", "INR {}", "₹{}", "Rs. {}"))
    return fmt.format(inr(rng.randrange(lo, hi + 1, step)))


def _dur(rng: random.Random, values: tuple[int, ...], unit: str) -> str:
    n = rng.choice(values)
    suffix = unit if n == 1 else unit + "s"
    if n in _WORDS and rng.random() < 0.5:
        return f"{_WORDS[n]} ({n}) {suffix}"
    return f"{n} {suffix}"


def _pct(rng: random.Random, values: tuple[int, ...]) -> str:
    n = rng.choice(values)
    return rng.choice((f"{n}%", f"{n} percent", f"{n} per cent"))


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _person(rng: random.Random) -> str:
    return f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"


SLOTS: dict[str, Callable[[random.Random], str]] = {
    "rent": lambda r: _money(r, 8000, 150000, 500),
    "deposit_amount": lambda r: _money(r, 30000, 600000, 5000),
    "repair_limit": lambda r: _money(r, 1000, 5000, 500),
    "maintenance_charge": lambda r: _money(r, 1500, 9000, 500),
    "bond_amount": lambda r: _money(r, 50000, 500000, 25000),
    "training_cost": lambda r: _money(r, 20000, 200000, 10000),
    "refund_days": lambda r: _dur(r, (7, 10, 15, 30), "day"),
    "long_refund_days": lambda r: _dur(r, (45, 60, 90), "day"),
    "notice_days": lambda r: _dur(r, (30, 45, 60, 90), "day"),
    "emp_notice_days": lambda r: _dur(r, (60, 90), "day"),
    "er_notice_days": lambda r: _dur(r, (7, 15, 30), "day"),
    "cure_days": lambda r: _dur(r, (7, 15, 30), "day"),
    "default_days": lambda r: _dur(r, (15, 30, 45), "day"),
    "verification_days": lambda r: _dur(r, (7, 10, 15, 30), "day"),
    "guest_days": lambda r: _dur(r, (3, 7, 10, 15), "day"),
    "lock_in_months": lambda r: _dur(r, (3, 6, 11, 12), "month"),
    "escalation_months": lambda r: _dur(r, (11, 12, 24), "month"),
    "bond_months": lambda r: _dur(r, (6, 12, 24), "month"),
    "recovery_months": lambda r: _dur(r, (6, 12, 24), "month"),
    "retention_months": lambda r: _dur(r, (1, 2, 3, 6), "month"),
    "entry_notice_hours": lambda r: _dur(r, (24, 48), "hour"),
    "penalty_months": lambda r: r.choice(("one month's", "two months'", "three months'")),
    "escalation_pct": lambda r: _pct(r, (3, 5, 7, 8, 10)),
    "deduction_pct": lambda r: _pct(r, (5, 10, 15, 20, 25)),
    "city": lambda r: r.choice(_CITIES),
    "locality": lambda r: r.choice(_LOCALITIES),
    "flat_no": lambda r: f"{r.randint(1, 15)}{r.randint(1, 4):02d}",
    "day": lambda r: _ordinal(r.randint(1, 28)),
    "month": lambda r: r.choice(_MONTHS),
    "year": lambda r: str(r.randint(2024, 2026)),
    "owner_name": _person,
    "tenant_name": _person,
    "employee_name": _person,
    "employer_name": lambda r: r.choice(_COMPANY),
    "designation": lambda r: r.choice(_DESIGNATIONS),
}

_TOKEN = re.compile(r"\{([^{}]+)\}")
# Neutral lead-ins: add surface variety to clause samples without changing the meaning.
_LEADS = ("", "", "It is agreed that ", "The parties agree that ",
          "Notwithstanding anything else in this Agreement, ")  # fmt: skip


class Entity(BaseModel):
    label: str  # slot name, e.g. "deposit_amount"
    text: str
    start: int
    end: int


class SynthRecord(ClauseRecord):
    doc_type: str
    risk: Literal["green", "amber", "red"] | None = None
    flags: list[str] = []
    family: str  # template family; test families never appear in train/val
    entities: list[Entity] = []


def _rng(*parts: object) -> random.Random:
    digest = hashlib.sha256(":".join(map(str, parts)).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _new_ctx(doc_type: str, rng: random.Random) -> dict[str, str]:
    return dict(rng.choice(ROLE_SETS[doc_type]))


def render(template: str, rng: random.Random, ctx: dict[str, str]) -> tuple[str, list[Entity]]:
    """Fill a template; `ctx` is updated so repeated slots stay consistent within a document.

    Returns the text and the entity spans (character offsets into the returned text).
    """
    parts: list[str] = []
    entities: list[Entity] = []
    pos = length = 0
    for m in _TOKEN.finditer(template):
        literal = template[pos : m.start()]
        parts.append(literal)
        length += len(literal)
        name = m.group(1)
        if "|" in name:
            value, is_entity = rng.choice(name.split("|")), False
        else:
            if name not in ctx:
                ctx[name] = SLOTS[name](rng)
                while name in _NAME_SLOTS and any(
                    ctx.get(other) == ctx[name] for other in _NAME_SLOTS if other != name
                ):
                    ctx[name] = SLOTS[name](rng)  # two parties never share a name
            value, is_entity = ctx[name], name not in ROLE_SLOTS
        if is_entity:
            entities.append(Entity(label=name, text=value, start=length, end=length + len(value)))
        parts.append(value)
        length += len(value)
        pos = m.end()
    parts.append(template[pos:])
    return "".join(parts), entities


def _record(text, entities, clause_id, doc_type, split, risk, flags, family) -> SynthRecord:
    return SynthRecord(
        id="s_" + hashlib.sha256(text.encode()).hexdigest()[:16],
        text=text,
        labels=[clause_id],
        sources=["synth"],
        source_labels=[f"synth:{clause_id}"],
        split=split,
        doc_type=doc_type,
        risk=risk,
        flags=list(flags),
        family=family,
        entities=entities,
    )


def generate_samples(
    *, n_train: int = 60, n_val: int = 10, n_test: int = 15, seed: int = 42
) -> tuple[list[SynthRecord], dict[str, Any]]:
    """Clause samples per (clause, risk) plus "other" samples (preambles, closing lines).

    train/val use phrasing 0 of every template; test uses phrasing 1 only.
    """
    plan = (("train", 0, n_train), ("val", 0, n_val), ("test", 1, n_test))
    seen: set[str] = set()
    records: list[SynthRecord] = []

    def draw(template, doc_type, clause_id, risk, flags, family, split, n, rng, lead=True):
        made = attempts = 0
        while made < n and attempts < n * 50:
            attempts += 1
            prefix = rng.choice(_LEADS) if lead else ""
            body = prefix + template[0].lower() + template[1:] if prefix else template
            text, entities = render(body, rng, _new_ctx(doc_type, rng))
            if text in seen:
                continue
            seen.add(text)
            made += 1
            records.append(_record(text, entities, clause_id, doc_type, split, risk, flags, family))

    for spec in SPECS.values():
        for risk in range(3):
            for split, pool, n in plan:
                draw(
                    f"{spec.core[pool]} {spec.mods[risk][pool]}", spec.doc_type, spec.clause_id,
                    RISKS[risk], spec.flags[risk], f"{spec.clause_id}:p{pool}:r{risk}",
                    split, n, _rng(seed, spec.clause_id, risk, split),
                )  # fmt: skip
    for key, pair in FILLERS.items():
        doc_type = key.split("_", 1)[1]
        for split, pool, n in plan:
            draw(
                pair[pool], doc_type, OTHER, None, (), f"{OTHER}:{key}:p{pool}",
                split, n, _rng(seed, key, split), lead=False,
            )  # fmt: skip

    # Leakage control, same idea as Phase 1: drop train/val texts that nearly duplicate a test text.
    test_texts = [r.text for r in records if r.split == "test"]
    kept = [r for r in records if r.split == "test"]
    removed: dict[str, int] = {}
    for split in ("train", "val"):
        cand = [r for r in records if r.split == split]
        hits = find_near_duplicates([r.text for r in cand], test_texts)
        removed[split] = len(hits)
        kept += [r for i, r in enumerate(cand) if i not in hits]

    kept.sort(key=lambda r: r.id)
    per_split = Counter(r.split for r in kept)
    stats = {
        "n_records": len(kept),
        "per_split": dict(per_split),
        "near_dup_removed": removed,
        "per_label_split": {
            label: dict(Counter(r.split for r in kept if r.labels == [label]))
            for label in sorted({r.labels[0] for r in kept})
        },
        "per_risk": dict(Counter(r.risk for r in kept if r.risk)),
    }
    return kept, stats


# ---------------------------------------------------------------- documents


def _roman(n: int) -> str:
    return ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII")[n - 1]


def _number(i: int, style: str) -> str:
    return {
        "dot": f"{i}. ",
        "paren": f"{i}) ",
        "clause": f"Clause {i}: ",
        "article": f"ARTICLE {_roman(i)}. ",
        "none": "",
    }[style]


def _layout(title: str, items: list[dict], numbering: str, heading: str, wrap: int | None) -> str:
    def fill(s: str) -> str:
        if not wrap:
            return s
        return textwrap.fill(s, wrap, break_long_words=False, break_on_hyphens=False)

    blocks = [title, fill(items[0]["text"])]
    n = 0
    for item in items[1:]:
        if item["kind"] != "clause":
            blocks.append(item["text"])
            continue
        n += 1
        prefix, head, body = _number(n, numbering), item["heading"], item["text"]
        if heading == "inline":
            blocks.append(fill(f"{prefix}{head}: {body}"))
        elif heading == "line":
            blocks.append(f"{prefix}{head}\n{fill(body)}")
        else:
            blocks.append(fill(f"{prefix}{body}"))
    return "\n\n".join(blocks) + "\n"


def assemble_document(
    doc_type: str,
    rng: random.Random,
    *,
    doc_id: str,
    numbering: str = "dot",
    heading: str = "inline",
    wrap: int | None = None,
    pool: int = 1,
) -> dict[str, Any]:
    """Build a full synthetic agreement with ground-truth clause texts and risk labels.

    Defaults to the held-out phrasing (pool 1) so documents can serve as unseen test data.
    """
    ctx = _new_ctx(doc_type, rng)
    if doc_type == "rent_agreement":
        title = "LEAVE AND LICENSE AGREEMENT" if ctx["owner"] == "Licensor" else "RENT AGREEMENT"
    else:
        title = "INTERNSHIP OFFER LETTER" if ctx["employee"] == "Intern" else "OFFER OF EMPLOYMENT"

    preamble, _ = render(FILLERS[f"preamble_{doc_type}"][pool], rng, ctx)
    items: list[dict] = [{"kind": "preamble", "clause_id": None, "risk": None, "text": preamble}]

    def add(clause_id: str, heading_text: str, template: str, risk: str | None) -> None:
        text, _ = render(template, rng, ctx)
        items.append(
            {"kind": "clause", "clause_id": clause_id, "risk": risk, "heading": heading_text,
             "text": text}
        )  # fmt: skip

    for clause_id in ORDER[doc_type]:
        spec = SPECS[clause_id]
        risk = rng.choices((0, 1, 2), weights=(4, 3, 3))[0]
        add(clause_id, spec.heading, f"{spec.core[pool]} {spec.mods[risk][pool]}", RISKS[risk])
    for clause_id, (head, _, pair) in COMMON.items():
        add(clause_id, head, pair[pool], None)

    closing, _ = render(FILLERS[f"trailer_{doc_type}"][pool], rng, ctx)
    if doc_type == "rent_agreement":
        sign = (f"{ctx['owner']}: ____________    {ctx['tenant']}: ____________\n\n"
                "Witnesses:\n1. ____________\n2. ____________")  # fmt: skip
    else:
        sign = f"{ctx['employee']}: ____________\nDate: ____________"
    trailer = f"{closing}\n\n{sign}"
    items.append({"kind": "trailer", "clause_id": None, "risk": None, "text": trailer})

    return {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "style": {"numbering": numbering, "heading": heading, "wrap": wrap},
        "text": _layout(title, items, numbering, heading, wrap),
        "items": items,
    }


def generate_documents(n_docs: int = 60, seed: int = 42) -> list[dict[str, Any]]:
    """Cycle through every layout style (numbering x heading x wrap) and both document types."""
    styles = list(itertools.product(NUMBERINGS, HEADINGS, (None, 78)))
    docs = []
    for i in range(n_docs):
        numbering, heading, wrap = styles[i % len(styles)]
        doc_type = ("rent_agreement", "offer_and_bond")[(i // len(styles) + i) % 2]
        docs.append(
            assemble_document(
                doc_type,
                _rng(seed, "doc", i),
                doc_id=f"synth_doc_{i:04d}",
                numbering=numbering,
                heading=heading,
                wrap=wrap,
            )  # fmt: skip
        )
    return docs
