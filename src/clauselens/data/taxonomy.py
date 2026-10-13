"""Load and validate the clause taxonomy (configs/taxonomy.yaml)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

from clauselens.paths import CONFIGS

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
KNOWN_SOURCES = frozenset({"cuad", "ledgar"})
OTHER_ID = "other"


class TaxonomyError(ValueError):
    """Raised when the taxonomy config is inconsistent."""


@dataclass(frozen=True, slots=True)
class ClauseType:
    id: str
    name: str
    applies_to: tuple[str, ...]
    description: str


class Taxonomy:
    def __init__(
        self,
        version: int,
        clauses: list[ClauseType],
        mapping: dict[tuple[str, str], str],
        excluded: dict[tuple[str, str], str],
    ) -> None:
        self.version = version
        self.clauses = clauses
        self._mapping = mapping
        self._excluded = excluded

    @classmethod
    def load(
        cls,
        taxonomy_path: Path = CONFIGS / "taxonomy.yaml",
        scope_path: Path = CONFIGS / "scope.yaml",
    ) -> Taxonomy:
        tax = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8"))
        scope = yaml.safe_load(scope_path.read_text(encoding="utf-8"))
        allowed_scopes = {"common", *scope["doc_types"]}

        clauses: list[ClauseType] = []
        mapping: dict[tuple[str, str], str] = {}
        seen_ids: set[str] = set()

        for raw in tax["clauses"]:
            cid = raw["id"]
            if not _ID_PATTERN.match(cid):
                raise TaxonomyError(f"invalid clause id: {cid!r}")
            if cid in seen_ids:
                raise TaxonomyError(f"duplicate clause id: {cid}")
            seen_ids.add(cid)

            applies_to = tuple(raw["applies_to"])
            unknown = set(applies_to) - allowed_scopes
            if not applies_to or unknown:
                raise TaxonomyError(f"{cid}: bad applies_to {sorted(unknown) or 'empty'}")

            clauses.append(ClauseType(cid, raw["name"], applies_to, raw["description"]))

            for source, labels in (raw.get("map") or {}).items():
                if source not in KNOWN_SOURCES:
                    raise TaxonomyError(f"{cid}: unknown source {source!r}")
                for label in labels:
                    key = (source, label)
                    if key in mapping:
                        raise TaxonomyError(f"{key} mapped twice: {mapping[key]} and {cid}")
                    mapping[key] = cid

        excluded: dict[tuple[str, str], str] = {}
        for source, groups in (tax.get("excluded") or {}).items():
            if source not in KNOWN_SOURCES:
                raise TaxonomyError(f"excluded: unknown source {source!r}")
            for group, labels in groups.items():
                for label in labels:
                    key = (source, label)
                    if key in mapping or key in excluded:
                        raise TaxonomyError(f"{key} is both mapped/excluded or excluded twice")
                    excluded[key] = group

        return cls(tax["version"], clauses, mapping, excluded)

    def with_other(self, groups: Iterable[str]) -> Taxonomy:
        """Copy where excluded labels of the given groups map to the catch-all "other" class."""
        groups = set(groups)
        mapping = dict(self._mapping)
        for key, group in self._excluded.items():
            if group in groups:
                mapping[key] = OTHER_ID
        excluded = {k: g for k, g in self._excluded.items() if g not in groups}
        other = ClauseType(OTHER_ID, "Other", ("common",), "Text that is none of the clause types.")
        return Taxonomy(self.version, [*self.clauses, other], mapping, excluded)

    @property
    def clause_ids(self) -> list[str]:
        return [c.id for c in self.clauses]

    def resolve(self, source: str, label: str) -> str | None:
        """Clause id for a source label, or None if unmapped or excluded."""
        return self._mapping.get((source, label))

    def is_excluded(self, source: str, label: str) -> bool:
        return (source, label) in self._excluded

    def declared_labels(self, source: str) -> set[str]:
        keys = [*self._mapping, *self._excluded]
        return {label for src, label in keys if src == source}

    def validate_against(
        self, source: str, available: Iterable[str], *, require_full_coverage: bool = False
    ) -> None:
        """Check declared labels against the labels that really exist in the source.

        Catches typos in the YAML. With `require_full_coverage`, also fails if the
        source has labels the taxonomy has not decided about.
        """
        available_set = set(available)
        declared = self.declared_labels(source)
        missing = declared - available_set
        if missing:
            raise TaxonomyError(f"{source}: labels not found in source: {sorted(missing)}")
        if require_full_coverage:
            undecided = available_set - declared
            if undecided:
                raise TaxonomyError(f"{source}: labels not in taxonomy: {sorted(undecided)}")
