from __future__ import annotations

from clauselens.data.build import build_dataset
from clauselens.data.taxonomy import OTHER_ID, Taxonomy
from clauselens.schemas import RawExample


def _tax() -> Taxonomy:
    return Taxonomy.load().with_other(["out_of_domain"])


def test_with_other_maps_only_the_requested_groups():
    tax = _tax()
    assert OTHER_ID in tax.clause_ids
    assert tax.resolve("cuad", "License Grant") == OTHER_ID
    assert tax.resolve("ledgar", "Brokers") == OTHER_ID
    assert not tax.is_excluded("cuad", "License Grant")
    # metadata facts stay excluded; real clause labels are untouched
    assert tax.resolve("cuad", "Parties") is None and tax.is_excluded("cuad", "Parties")
    assert tax.resolve("cuad", "Non-Compete") == "non_compete"


def test_with_other_does_not_mutate_the_original():
    base = Taxonomy.load()
    base.with_other(["out_of_domain"])
    assert base.resolve("cuad", "License Grant") is None
    assert OTHER_ID not in base.clause_ids


def test_a_real_label_always_wins_over_other():
    text = "Either party may terminate on thirty days written notice to the other."
    examples = [
        RawExample(text, "cuad", "Termination For Convenience", "doc1"),
        RawExample(text, "cuad", "License Grant", "doc1"),
    ]
    records, _ = build_dataset(examples, _tax(), ["doc1"])
    assert [r.labels for r in records] == [["termination"]]


def test_other_is_capped_per_split():
    positives = [
        RawExample(
            f"Termination clause {i} allows either party to end this agreement on notice.",
            "ledgar",
            "Terminations",
            split_hint="train",
        )
        for i in range(2)
    ]
    others = [
        RawExample(
            f"Broker clause number {i} states that no broker is entitled to any fee.",
            "ledgar",
            "Brokers",
            split_hint="train",
        )
        for i in range(10)
    ]
    records, stats = build_dataset(positives + others, _tax(), [], max_other_ratio=1.0)
    assert sum(r.labels == [OTHER_ID] for r in records) == 2
    assert stats["dropped"]["other_cap"] == 8
    assert sum(r.labels == ["termination"] for r in records) == 2
