"""Near-duplicate detection (MinHash + LSH) used to stop train/test leakage."""

from __future__ import annotations

from collections.abc import Sequence

try:
    from datasketch import MinHash, MinHashLSH
except ImportError:  # lightweight fallback for minimal/test environments
    MinHash = None  # type: ignore[assignment,misc]
    MinHashLSH = None  # type: ignore[assignment,misc]

from clauselens.data.text import normalize_text


def shingles(text: str, k: int = 3) -> set[str]:
    """Word k-shingles of the normalised, case-folded text."""
    words = normalize_text(text).casefold().split()
    if len(words) <= k:
        return {" ".join(words)}
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def minhash(text: str, *, num_perm: int = 128, k: int = 3):
    if MinHash is None:
        raise RuntimeError("datasketch is required for MinHash signatures")
    m = MinHash(num_perm=num_perm, seed=1)
    for shingle in shingles(text, k):
        m.update(shingle.encode("utf-8"))
    return m


def find_near_duplicates(
    queries: Sequence[str],
    reference: Sequence[str],
    *,
    threshold: float = 0.85,
    num_perm: int = 128,
    k: int = 3,
) -> set[int]:
    """Indices of `queries` having an (approximately) >= `threshold` Jaccard match in `reference`.

    LSH is probabilistic: it can miss pairs very close to the threshold. That is acceptable
    for leakage control, where the goal is to remove the clear duplicates.
    """
    if not queries or not reference:
        return set()
    if MinHash is None or MinHashLSH is None:
        # Deterministic fallback: use an inverted shingle index to narrow candidates, then
        # calculate exact Jaccard similarity. This is slower than LSH but needs no extra package.
        ref_shingles = [shingles(text, k) for text in reference]
        inverted: dict[str, set[int]] = {}
        for j, parts in enumerate(ref_shingles):
            for part in parts:
                inverted.setdefault(part, set()).add(j)
        duplicates: set[int] = set()
        for i, text in enumerate(queries):
            parts = shingles(text, k)
            candidates: set[int] = set()
            for part in parts:
                candidates.update(inverted.get(part, ()))
            for j in candidates:
                union = len(parts | ref_shingles[j])
                if union and len(parts & ref_shingles[j]) / union >= threshold:
                    duplicates.add(i)
                    break
        return duplicates
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    for j, text in enumerate(reference):
        lsh.insert(str(j), minhash(text, num_perm=num_perm, k=k))
    return {i for i, text in enumerate(queries) if lsh.query(minhash(text, num_perm=num_perm, k=k))}
