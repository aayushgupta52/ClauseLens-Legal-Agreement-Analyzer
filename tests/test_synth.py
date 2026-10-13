from __future__ import annotations

import random
import re

import pytest

from clauselens.data.text import normalize_text
from clauselens.synth import generator as g
from clauselens.synth.templates import COMMON, FILLERS, ORDER, SPECS


@pytest.fixture(scope="module")
def samples():
    return g.generate_samples(n_train=20, n_val=5, n_test=8, seed=3)[0]


def _templates():
    for spec in SPECS.values():
        yield from spec.core
        for pair in spec.mods:
            yield from pair
    for pair in FILLERS.values():
        yield from pair
    for _, _, pair in COMMON.values():
        yield from pair


def test_every_template_slot_is_defined():
    names = {n for t in _templates() for n in re.findall(r"\{([^{}|]+)\}", t)}
    assert names <= set(g.SLOTS) | g.ROLE_SLOTS


def test_every_clause_has_three_risk_levels_and_flags():
    assert len(SPECS) == 15
    for spec in SPECS.values():
        assert len(spec.mods) == 3 and len(spec.flags) == 3
        assert spec.flags[0] == () and spec.flags[2], spec.clause_id  # green clean, red flagged
    assert all(cid in SPECS for ids in ORDER.values() for cid in ids)


def test_indian_digit_grouping():
    assert (g.inr(999), g.inr(25000), g.inr(150000), g.inr(1234567)) == (
        "999", "25,000", "1,50,000", "12,34,567",
    )  # fmt: skip


def test_render_offsets_and_consistency_within_a_context():
    ctx = {"tenant": "Licensee"}
    text, ents = g.render(
        "{tenant} pays {deposit_amount}, i.e. {deposit_amount} {again|once more}.",
        random.Random(0),
        ctx,
    )
    assert len(ents) == 2 and ents[0].text == ents[1].text  # same slot -> same value
    assert all(text[e.start : e.end] == e.text for e in ents)
    assert text.startswith("Licensee pays")  # roles are substituted but are not entities


def test_samples_are_clean_and_unique(samples):
    texts = [r.text for r in samples]
    assert len(texts) == len(set(texts))
    assert not any("{" in t or "}" in t or "  " in t for t in texts)
    for r in samples:
        assert all(r.text[e.start : e.end] == e.text for e in r.entities)
        assert r.sources == ["synth"] and r.labels[0] in {*SPECS, "other"}


def test_generation_is_deterministic():
    a, _ = g.generate_samples(n_train=5, n_val=2, n_test=3, seed=11)
    b, _ = g.generate_samples(n_train=5, n_val=2, n_test=3, seed=11)
    assert [r.model_dump() for r in a] == [r.model_dump() for r in b]


def test_test_split_uses_unseen_phrasing(samples):
    fam = lambda split: {r.family for r in samples if r.split == split}  # noqa: E731
    assert fam("test") and not (fam("test") & (fam("train") | fam("val")))
    texts = lambda split: {r.text for r in samples if r.split == split}  # noqa: E731
    assert not (texts("test") & (texts("train") | texts("val")))


def test_all_clause_types_and_risks_are_covered(samples):
    assert {r.labels[0] for r in samples} == {*SPECS, "other"}
    for cid in SPECS:
        for split in ("train", "test"):
            risks = {r.risk for r in samples if r.labels == [cid] and r.split == split}
            assert risks == {"green", "amber", "red"}, (cid, split)
    assert all(r.risk is None for r in samples if r.labels == ["other"])


def test_roles_match_the_document_type(samples):
    rent_only = ("Owner", "Tenant", "Licensor", "Licensee", "Landlord")
    bond_only = ("Employer", "Employee", "Company", "Intern", "Trainee", "Organisation")
    for r in samples:
        forbidden = bond_only if r.doc_type == "rent_agreement" else rent_only
        assert not any(re.search(rf"\b{w}\b", r.text) for w in forbidden), r.text


def test_documents_carry_ground_truth_for_every_layout():
    docs = g.generate_documents(n_docs=30, seed=5)
    assert len({tuple(d["style"].values()) for d in docs}) == 30
    for d in docs:
        flat = normalize_text(d["text"])
        clauses = [i for i in d["items"] if i["kind"] == "clause"]
        assert all(normalize_text(i["text"]) in flat for i in clauses)
        assert {"governing_law", "dispute_resolution", "entire_agreement"} <= {
            i["clause_id"] for i in clauses
        }
        assert d["items"][0]["kind"] == "preamble" and d["items"][-1]["kind"] == "trailer"


def test_parties_in_one_document_never_share_a_name():
    for seed in range(40):
        ctx = {"owner": "Owner", "tenant": "Tenant"}
        g.render("{owner_name} and {tenant_name}", random.Random(seed), ctx)
        assert ctx["owner_name"] != ctx["tenant_name"]
