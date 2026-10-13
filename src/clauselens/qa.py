"""Ask-your-contract (Phase 8): retrieval over the analysed clauses, answers with citations.

Extractive on purpose: the answer is the matching clause itself (plus its extracted key terms),
never a paraphrase, and the clause it came from is always cited. If nothing matches well enough
the answer says so instead of guessing.
"""

from __future__ import annotations

import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer

# question keywords (English + Hinglish) -> clause types that usually answer them
ROUTES: list[tuple[str, tuple[str, ...]]] = [
    ("security_deposit", ("deposit", "refund", "security", "wapas")),
    ("lock_in_period", ("lock-in", "lock in", "lockin", "early exit", "jaldi")),
    ("rent_escalation", ("rent increase", "escalat", "hike", "rent badh", "revision", "increase")),
    ("maintenance_repairs", ("repair", "maintenance", "fix")),
    (
        "utilities_and_charges",
        ("electricity", "water", "utilit", "society", "bijli", "paani", "charges"),
    ),
    ("owner_entry_inspection", ("enter", "inspection", "visit", "entry")),
    ("subletting_guests", ("guest", "sublet", "sharing", "visitor")),
    ("eviction_default", ("evict", "default", "non-payment", "unpaid", "nikal")),
    ("tenant_verification", ("police", "verification", "identity")),
    ("handover_inventory", ("inventory", "handover", "repaint", "condition")),
    ("service_bond", ("bond", "service period", "service agreement", "leave early", "resign")),
    ("training_cost_recovery", ("training", "onboarding")),
    ("notice_period", ("notice", "resign", "quit")),
    ("document_retention", ("original", "certificate", "marksheet", "documents")),
    ("salary_deductions", ("deduct", "salary", "stipend", "pay cut")),
    ("payment_terms", ("license fee", "licence fee", "payment of rent", "how do i pay")),
    ("termination", ("terminat", "end the agreement", "cancel")),
    ("governing_law", ("governing", "which law", "applicable law")),
    ("dispute_resolution", ("court", "jurisdiction", "dispute", "arbitrat")),
    ("confidentiality", ("confidential", "secret")),
    ("non_compete", ("non-compete", "compete")),
]
_AMOUNT_Q = re.compile(r"how much|how long|how many|kitna|kitne|kab|when|amount|period", re.I)
NOT_FOUND = {
    "en": "I could not find a clear answer to that in this agreement. Try rephrasing, or ask about a specific clause (deposit, notice, lock-in, bond...).",
    "hinglish": "Mujhe is agreement mein iska clear jawab nahi mila. Question dusre tareeke se poochho, ya kisi specific clause (deposit, notice, lock-in, bond...) ke baare mein poochho.",
}
LEAD = {"en": "The agreement says", "hinglish": "Agreement ke hisaab se"}
MIN_SCORE = 0.12


def route_question(question: str) -> list[str]:
    low = question.lower()
    return [cid for cid, keys in ROUTES if any(k in low for k in keys)]


def ask(clauses: list[dict[str, Any]], question: str, lang: str = "en", top_k: int = 3) -> dict:
    """Answer `question` from analysed `clauses` (dicts with text, labels, facts, ...)."""
    pool = [c for c in clauses if c.get("kind") == "clause" and c.get("text")]
    if not question.strip() or not pool:
        return {"answer": NOT_FOUND[lang], "found": False, "citations": []}

    routed = set(route_question(question))
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
    try:
        matrix = vectorizer.fit_transform([c["text"] for c in pool] + [question])
    except ValueError:  # question and clauses contain only stop words
        return {"answer": NOT_FOUND[lang], "found": False, "citations": []}
    sims = (matrix[:-1] @ matrix[-1].T).toarray().ravel()

    scored = []
    for clause, sim in zip(pool, sims, strict=True):
        boost = 0.5 if routed & set(clause.get("labels", [])) else 0.0
        heading = (clause.get("heading") or "").lower()
        if heading and any(w in heading for w in re.findall(r"[a-z]{4,}", question.lower())):
            boost += 0.2
        scored.append((float(sim) + boost, clause))
    scored.sort(key=lambda t: -t[0])
    best_score, best = scored[0]
    if best_score < MIN_SCORE:
        return {"answer": NOT_FOUND[lang], "found": False, "citations": []}

    citations = [
        {"index": c["index"], "number": c.get("original_number") or c.get("number"),
         # The UI may pass an already translated report. Prefer its current heading for display,
         # while preserving the source-language heading separately for traceability.
         "heading": c.get("heading") or c.get("original_heading"),
         "original_heading": c.get("original_heading") or c.get("heading"),
         "text": c.get("original_text") or c["text"], "score": round(s, 3)}
        for s, c in scored[:top_k] if s >= MIN_SCORE
    ]  # fmt: skip
    where = (best.get("number") or f"#{best['index']}").rstrip(".:")
    if best.get("heading"):
        where += f" ({best['heading']})"
    answer = f"{LEAD[lang]} (clause {where}): “{best['text']}”"
    if _AMOUNT_Q.search(question) and (best.get("explanation") or {}).get("facts_line"):
        answer += f"\nKey terms: {best['explanation']['facts_line']}"
    return {"answer": answer, "found": True, "citations": citations}
