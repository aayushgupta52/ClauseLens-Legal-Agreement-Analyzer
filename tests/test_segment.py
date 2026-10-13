from __future__ import annotations

from clauselens.data.text import normalize_text
from clauselens.segment import clause_recovery, segment_document, split_sentences
from clauselens.synth import generator as g

LICENCE = """LEAVE AND LICENSE AGREEMENT

This Agreement is made at Mumbai on 5th June 2025 between Mr. R. K. Mehta (Licensor) and Ms.
Priya Nair (Licensee).

1. The Licensee shall pay a monthly license fee of Rs. 35,000/- on or before the 5th of every month.
2. The Licensee has paid Rs. 1,05,000/- as interest free refundable security deposit. The deposit
shall be returned within 30 days of vacating, i.e. after the keys are handed over.
3. LOCK-IN PERIOD
Neither party may terminate this Agreement during the first 6 months.
4. The Licensee shall not sub-let the premises. Guests may stay for up to 7 days.
(a) No pets are allowed.
(b) Smoking is not permitted inside the flat.
Page 2 of 3
5. Either party may terminate this Agreement by giving 30 days notice.

IN WITNESS WHEREOF the parties have signed below.
Licensor: ________   Licensee: ________
Witnesses:
1. ________
2. ________
"""


def test_realistic_licence_text():
    segs = segment_document(LICENCE)
    assert [s.kind for s in segs] == ["preamble", *["clause"] * 5, "trailer"]
    assert [s.number for s in segs[1:6]] == ["1.", "2.", "3.", "4.", "5."]
    assert segs[3].heading == "LOCK-IN PERIOD"
    assert "Rs. 1,05,000/-" in segs[2].text and "i.e. after the keys" in segs[2].text
    assert "No pets are allowed" in segs[4].text  # short sub-items stay inside their clause
    assert not any("Page 2" in s.text for s in segs)
    assert "Witnesses" in segs[-1].text  # signature numbering did not create clauses


def test_offsets_point_into_the_original_text():
    for s in segment_document(LICENCE):
        window = normalize_text(LICENCE[s.start : s.end])
        assert normalize_text(" ".join(s.text.split()[:4])) in window


def test_paragraph_mode_inline_headings_and_trailer():
    text = (
        "SECURITY DEPOSIT: The tenant pays a refundable deposit.\n\n"
        "Notice Period: Either party may leave on 30 days notice.\n\n"
        "IN WITNESS WHEREOF the parties sign.\n\nWitnesses:\n1. ______\n"
    )
    segs = segment_document(text)
    assert [(s.kind, s.heading) for s in segs] == [
        ("clause", "SECURITY DEPOSIT"),
        ("clause", "Notice Period"),
        ("trailer", None),
    ]


def test_wrapped_fragments_are_not_mistaken_for_numbers():
    text = (
        "1. The notice period shall be three\n(3) months from the date of joining.\n"
        "2. The agreement is dated 5th March,\n2025. It continues until ended.\n"
        "3. The rent is 1.5 times\nthe base amount.\n"
    )
    segs = segment_document(text)
    assert [s.number for s in segs] == ["1.", "2.", "3."]
    assert "(3) months" in segs[0].text and "2025." in segs[1].text


def test_long_clause_is_split_at_sub_numbers():
    body = " ".join(["word"] * 30)
    text = "1. The Tenant shall:\n" + "\n".join(f"({c}) {body}" for c in "abc") + "\n"
    segs = segment_document(text, max_words=60)
    assert [s.number for s in segs] == ["1.", "(a)", "(b)", "(c)"]


def test_long_unnumbered_sentences_are_packed():
    sentence = "This sentence has exactly ten words in it for packing."
    text = "1. " + " ".join([sentence] * 9)
    parts = segment_document(text, max_words=30)
    assert len(parts) == 3 and all(p.n_words <= 30 for p in parts)


def test_sentence_splitter_respects_abbreviations():
    out = split_sentences(
        "Pay Rs. 25,000/- to Mr. Sharma i.e. the owner. Then S. K. Rao signs. Done; ok."
    )
    assert out == [
        "Pay Rs. 25,000/- to Mr. Sharma i.e. the owner.",
        "Then S. K. Rao signs.",
        "Done; ok.",
    ]


def test_empty_input():
    assert segment_document("") == [] and segment_document("  \n\n \n") == []


def test_every_synthetic_layout_is_recovered():
    # Regression guard only: the generator and the segmenter were written by the same people.
    for doc in g.generate_documents(n_docs=60, seed=9):
        segs = segment_document(doc["text"])
        found, total = clause_recovery(
            [i["text"] for i in doc["items"] if i["kind"] == "clause"], segs
        )
        assert found == total, (doc["doc_id"], doc["style"])
        assert segs[-1].kind == "trailer"
