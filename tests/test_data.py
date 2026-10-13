from __future__ import annotations

import pytest

from clauselens.data.build import build_dataset
from clauselens.data.dedupe import find_near_duplicates
from clauselens.data.sources import (
    CUAD_CATEGORIES,
    LEDGAR_LABELS,
    parse_cuad,
)
from clauselens.data.split import assign_groups
from clauselens.data.taxonomy import Taxonomy, TaxonomyError
from clauselens.data.text import fingerprint, normalize_text
from clauselens.schemas import RawExample


@pytest.fixture(scope="module")
def taxonomy() -> Taxonomy:
    return Taxonomy.load()


# ---------- taxonomy ----------


def test_label_constants_match_verified_sizes():
    assert len(CUAD_CATEGORIES) == 41 and len(set(CUAD_CATEGORIES)) == 41
    assert len(LEDGAR_LABELS) == 100 and len(set(LEDGAR_LABELS)) == 100


def test_taxonomy_is_consistent(taxonomy):
    ids = taxonomy.clause_ids
    assert len(ids) == len(set(ids))
    assert taxonomy.resolve("cuad", "Non-Compete") == "non_compete"
    assert taxonomy.resolve("ledgar", "Terminations") == "termination"
    assert taxonomy.is_excluded("cuad", "Parties")
    assert taxonomy.resolve("cuad", "Parties") is None


def test_taxonomy_covers_every_cuad_category(taxonomy):
    taxonomy.validate_against("cuad", CUAD_CATEGORIES, require_full_coverage=True)


def test_taxonomy_ledgar_labels_all_exist(taxonomy):
    taxonomy.validate_against("ledgar", LEDGAR_LABELS)


def test_taxonomy_rejects_double_mapping(tmp_path):
    bad = tmp_path / "taxonomy.yaml"
    bad.write_text(
        """
version: 1
clauses:
  - {id: a, name: A, applies_to: [common], description: d, map: {cuad: ["Governing Law"]}}
  - {id: b, name: B, applies_to: [common], description: d, map: {cuad: ["Governing Law"]}}
""",
        encoding="utf-8",
    )
    with pytest.raises(TaxonomyError):
        Taxonomy.load(bad)


def test_taxonomy_rejects_unknown_doc_type(tmp_path):
    bad = tmp_path / "taxonomy.yaml"
    bad.write_text(
        """
version: 1
clauses:
  - {id: a, name: A, applies_to: [car_loan], description: d}
""",
        encoding="utf-8",
    )
    with pytest.raises(TaxonomyError):
        Taxonomy.load(bad)


# ---------- text / split / dedupe ----------


def test_normalize_and_fingerprint_ignore_case_and_whitespace():
    assert normalize_text("  A\u00a0 b\n\tc ") == "A b c"
    assert fingerprint("Hello   World") == fingerprint("hello world\n")
    assert fingerprint("hello world") != fingerprint("hello worlds")


def test_assign_groups_deterministic_order_independent_and_balanced():
    ids = [f"doc{i}" for i in range(100)]
    a = assign_groups(ids, seed=7)
    b = assign_groups(reversed(ids), seed=7)
    assert a == b
    counts = {s: list(a.values()).count(s) for s in ("train", "val", "test")}
    assert counts == {"train": 80, "val": 10, "test": 10}
    assert a != assign_groups(ids, seed=8)


def test_assign_groups_validates_ratios():
    with pytest.raises(ValueError):
        assign_groups(["a"], ratios=(0.5, 0.5, 0.5))


def _long_text(prefix: str, n: int = 80) -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def test_find_near_duplicates():
    base = _long_text("alpha")
    near = base.replace("alpha40", "changed")
    other = _long_text("beta")
    assert find_near_duplicates([near, other], [base]) == {0}
    assert find_near_duplicates([], [base]) == set()


# ---------- sources ----------


def test_parse_cuad_collects_answers_and_contracts():
    data = {
        "data": [
            {
                "title": "ACME-AGREEMENT",
                "paragraphs": [
                    {
                        "context": "full contract text",
                        "qas": [
                            {
                                "id": "ACME-AGREEMENT__Governing Law",
                                "question": "q",
                                "is_impossible": False,
                                "answers": [
                                    {"text": "Governed by the laws of India.", "answer_start": 0}
                                ],
                            },
                            {
                                "id": "ACME-AGREEMENT__Non-Compete",
                                "question": "q",
                                "is_impossible": True,
                                "answers": [],
                            },
                        ],
                    }
                ],
            }
        ]
    }
    examples, contracts = parse_cuad(data)
    assert [(e.source_label, e.doc_id) for e in examples] == [("Governing Law", "ACME-AGREEMENT")]
    assert contracts == [{"doc_id": "ACME-AGREEMENT", "text": "full contract text"}]


def test_parse_cuad_rejects_unknown_category():
    data = {
        "data": [
            {
                "title": "T",
                "paragraphs": [
                    {"context": "c", "qas": [{"id": "T__Made Up Category", "answers": []}]}
                ],
            }
        ]
    }
    with pytest.raises(ValueError):
        parse_cuad(data)


# ---------- build pipeline ----------


def test_build_dataset_end_to_end(taxonomy):
    doc_ids = [f"doc{i}" for i in range(10)]
    near_base = _long_text("gamma")
    near_variant = near_base.replace("gamma40", "different")
    exact = "This agreement may be terminated by either party with notice."

    examples = [
        # same CUAD span tagged with two categories -> one multi-label record
        RawExample(
            "Either party may terminate on thirty days written notice to the other.",
            "cuad",
            "Termination For Convenience",
            "doc1",
        ),
        RawExample(
            "Either party may terminate on thirty days written notice to the other.",
            "cuad",
            "Notice Period To Terminate Renewal",
            "doc1",
        ),
        # exact duplicate (different case/spacing) in train and test -> kept once, in test
        RawExample(exact, "ledgar", "Terminations", split_hint="train"),
        RawExample(exact.upper() + "  ", "ledgar", "Terminations", split_hint="test"),
        # near-duplicate: train copy must be purged because a test copy exists
        RawExample(near_base, "ledgar", "Confidentiality", split_hint="train"),
        RawExample(near_variant, "ledgar", "Confidentiality", split_hint="test"),
        # dropped examples
        RawExample("Acme Corp and Beta Ltd.", "cuad", "Parties", "doc2"),
        RawExample(
            "Remedies available to the parties are cumulative and not exclusive of each other.",
            "ledgar",
            "Remedies",
            split_hint="train",
        ),
        RawExample("Too short here", "ledgar", "Terminations", split_hint="train"),
    ]

    records, stats = build_dataset(examples, taxonomy, doc_ids, seed=42)

    assert stats["dropped"] == {"excluded_label": 1, "unmapped_label": 1, "too_short": 1}
    assert stats["top_unmapped_labels"] == [("ledgar:Remedies", 1)]
    assert stats["n_texts_in_multiple_splits_before_resolution"] == 1
    assert stats["n_near_duplicates_removed_from_train"] == 1
    assert stats["n_records"] == len(records) == 3

    multi = next(r for r in records if set(r.labels) == {"termination", "term_and_renewal"})
    assert multi.sources == ["cuad"] and multi.doc_id == "doc1"
    assert multi.split == assign_groups(doc_ids, seed=42)["doc1"]

    exact_rec = next(r for r in records if r.labels == ["termination"])
    assert exact_rec.split == "test"

    conf = [r for r in records if r.labels == ["confidentiality"]]
    assert len(conf) == 1 and conf[0].split == "test"

    train_texts = [r.text for r in records if r.split == "train"]
    held_texts = [r.text for r in records if r.split != "train"]
    assert find_near_duplicates(train_texts, held_texts) == set()


def test_build_dataset_is_deterministic(taxonomy):
    examples = [
        RawExample(
            f"Clause number {i} says the tenant shall pay rent monthly.",
            "ledgar",
            "Payments",
            split_hint="train",
        )
        for i in range(20)
    ]
    a, _ = build_dataset(examples, taxonomy, [], seed=1)
    b, _ = build_dataset(list(reversed(examples)), taxonomy, [], seed=1)
    assert [r.model_dump() for r in a] == [r.model_dump() for r in b]
