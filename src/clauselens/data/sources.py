"""Adapters that turn CUAD and LEDGAR into `RawExample`s.

Schemas were verified against:
- CUAD v1 `CUADv1.json` (SQuAD-style; 510 contracts, 41 categories, qa id = "<title>__<category>")
- LexGLUE `ledgar` config on Hugging Face (fields: `text`, `label` as ClassLabel, 100 classes)
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from clauselens.data.io import read_jsonl, write_jsonl
from clauselens.schemas import RawExample

# fmt: off
CUAD_CATEGORIES: tuple[str, ...] = (
    "Affiliate License-Licensee", "Affiliate License-Licensor", "Agreement Date", "Anti-Assignment",
    "Audit Rights", "Cap On Liability", "Change Of Control", "Competitive Restriction Exception",
    "Covenant Not To Sue", "Document Name", "Effective Date", "Exclusivity", "Expiration Date",
    "Governing Law", "Insurance", "Ip Ownership Assignment", "Irrevocable Or Perpetual License",
    "Joint Ip Ownership", "License Grant", "Liquidated Damages", "Minimum Commitment",
    "Most Favored Nation", "No-Solicit Of Customers", "No-Solicit Of Employees", "Non-Compete",
    "Non-Disparagement", "Non-Transferable License", "Notice Period To Terminate Renewal",
    "Parties", "Post-Termination Services", "Price Restrictions", "Renewal Term",
    "Revenue/Profit Sharing", "Rofr/Rofo/Rofn", "Source Code Escrow", "Termination For Convenience",
    "Third Party Beneficiary", "Uncapped Liability", "Unlimited/All-You-Can-Eat-License",
    "Volume Restriction", "Warranty Duration",
)

LEDGAR_LABELS: tuple[str, ...] = (
    "Adjustments", "Agreements", "Amendments", "Anti-Corruption Laws", "Applicable Laws",
    "Approvals", "Arbitration", "Assignments", "Assigns", "Authority", "Authorizations",
    "Base Salary", "Benefits", "Binding Effects", "Books", "Brokers", "Capitalization",
    "Change In Control", "Closings", "Compliance With Laws", "Confidentiality",
    "Consent To Jurisdiction", "Consents", "Construction", "Cooperation", "Costs", "Counterparts",
    "Death", "Defined Terms", "Definitions", "Disability", "Disclosures", "Duties",
    "Effective Dates", "Effectiveness", "Employment", "Enforceability", "Enforcements",
    "Entire Agreements", "Erisa", "Existence", "Expenses", "Fees", "Financial Statements",
    "Forfeitures", "Further Assurances", "General", "Governing Laws", "Headings",
    "Indemnifications", "Indemnity", "Insurances", "Integration", "Intellectual Property",
    "Interests", "Interpretations", "Jurisdictions", "Liens", "Litigations", "Miscellaneous",
    "Modifications", "No Conflicts", "No Defaults", "No Waivers", "Non-Disparagement", "Notices",
    "Organizations", "Participations", "Payments", "Positions", "Powers", "Publicity",
    "Qualifications", "Records", "Releases", "Remedies", "Representations", "Sales", "Sanctions",
    "Severability", "Solvency", "Specific Performance", "Submission To Jurisdiction",
    "Subsidiaries", "Successors", "Survival", "Tax Withholdings", "Taxes", "Terminations", "Terms",
    "Titles", "Transactions With Affiliates", "Use Of Proceeds", "Vacations", "Venues", "Vesting",
    "Waiver Of Jury Trials", "Waivers", "Warranties", "Withholdings",
)
# fmt: on

# Hugging Face split name -> our split name
LEDGAR_SPLITS: dict[str, str] = {"train": "train", "validation": "val", "test": "test"}
_QA_ID_SEPARATOR = "__"


def load_cuad(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def parse_cuad(data: Mapping[str, Any]) -> tuple[list[RawExample], list[dict[str, str]]]:
    """Return (answer spans as examples, full contract texts).

    Contract texts are kept so Phase 3 can mine unlabeled passages as negatives.
    """
    valid = set(CUAD_CATEGORIES)
    examples: list[RawExample] = []
    contracts: list[dict[str, str]] = []

    for contract in data["data"]:
        doc_id = contract["title"]
        for paragraph in contract["paragraphs"]:
            contracts.append({"doc_id": doc_id, "text": paragraph["context"]})
            for qa in paragraph["qas"]:
                category = qa["id"].rsplit(_QA_ID_SEPARATOR, 1)[-1]
                if category not in valid:
                    raise ValueError(f"unexpected CUAD category {category!r} in {qa['id']!r}")
                for answer in qa["answers"]:  # empty when the category is absent
                    examples.append(
                        RawExample(
                            text=answer["text"],
                            source="cuad",
                            source_label=category,
                            doc_id=doc_id,
                        )
                    )
    return examples, contracts


def export_ledgar(dataset_dict: Mapping[str, Any], out_dir: Path) -> dict[str, int]:
    """Write each LEDGAR split as JSONL with label *names* (not class indices)."""
    names = tuple(dataset_dict["train"].features["label"].names)
    if names != LEDGAR_LABELS:
        raise ValueError("LEDGAR label set differs from the one this repo was verified against")

    counts: dict[str, int] = {}
    for hf_split in LEDGAR_SPLITS:
        rows = ({"text": r["text"], "label": names[r["label"]]} for r in dataset_dict[hf_split])
        counts[hf_split] = write_jsonl(out_dir / f"{hf_split}.jsonl", rows)
    return counts


def read_ledgar(raw_dir: Path) -> Iterator[RawExample]:
    for hf_split, our_split in LEDGAR_SPLITS.items():
        for row in read_jsonl(raw_dir / f"{hf_split}.jsonl"):
            yield RawExample(
                text=row["text"],
                source="ledgar",
                source_label=row["label"],
                split_hint=our_split,
            )
