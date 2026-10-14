from __future__ import annotations

from clauselens.facts import extract_facts
from clauselens.gaps import EXPECTED, GAP_TEXT, detect_doc_type, find_gaps
from clauselens.hints import property_clause_label
from clauselens.synth.generator import _rng, assemble_document


def test_property_purchase_document_type_detection():
    text = (
        "AGREEMENT FOR SALE\nThe purchaser agrees to buy the flat. The seller shall provide "
        "clear title and possession on the agreed date. Stamp duty and registration charges "
        "are payable as set out herein. The carpet area is recorded in this agreement."
    )
    doc_type, confidence = detect_doc_type(text)
    assert doc_type == "property_purchase"
    assert confidence > 0.5


def test_property_clause_override_beats_generic_classifier_labels():
    text = (
        "The Seller may change the layout, fixtures, carpet area, common facilities, parking "
        "allocation or building specifications without prior written consent. Any reduction in "
        "area or facilities will not entitle the Buyer to a price reduction, cancellation or compensation."
    )
    assert property_clause_label("property_purchase", "Changes to Property Specifications", text) == "property_specifications"
    assert property_clause_label("rent_agreement", "Changes to Property Specifications", text) is None


def test_property_expected_terms_have_gap_messages():
    assert set(EXPECTED["property_purchase"]).issubset(GAP_TEXT)
    assert find_gaps("property_purchase", {"property_specifications"}, set(EXPECTED["property_purchase"]))


def test_property_facts_get_contextual_roles():
    facts = extract_facts("The purchase consideration is ₹85,00,000 and the booking amount is ₹5,00,000.", "booking_payment")
    assert any(f.text == "₹85,00,000" and f.role == "purchase_price" for f in facts)
    assert any(f.text == "₹5,00,000" and f.role == "booking_amount" for f in facts)


def test_property_sample_document_can_be_generated_and_detected():
    doc = assemble_document("property_purchase", _rng("property-test"), doc_id="property-test", pool=1)
    assert "AGREEMENT FOR SALE" in doc["text"]
    assert detect_doc_type(doc["text"])[0] == "property_purchase"
    assert len([x for x in doc["items"] if x["kind"] == "clause"]) == len(EXPECTED["property_purchase"]) + 3


def test_property_specification_clause_gets_rule_based_red_flag(engine):
    from clauselens.pipeline import run_sequential

    text = (
        "AGREEMENT FOR SALE between Seller and Buyer for purchase of a flat.\n\n"
        "1. PROPERTY SPECIFICATIONS: The Seller may change the layout, fixtures, carpet area, "
        "common facilities, parking allocation or building specifications without prior written "
        "consent. Any reduction in area or facilities will not entitle the Buyer to a price "
        "reduction, cancellation or compensation.\n\n"
        "2. TITLE AND ENCUMBRANCES: The seller shall disclose any encumbrance and provide title documents.\n\n"
        "3. POSSESSION AND HANDOVER: Possession shall be given on the agreed date.\n\n"
        "4. BOOKING AND PURCHASE PAYMENTS: The purchase consideration and booking amount are payable by instalments.\n\n"
        "5. CANCELLATION AND REFUND: The booking amount shall be refunded as set out herein.\n\n"
        "6. REGISTRATION AND TRANSACTION CHARGES: Stamp duty and registration charges shall be paid by the buyer."
    )
    report = run_sequential(engine, {"text": text, "language": "en"})["report"]
    clause = next(c for c in report["clauses"] if c["primary"] == "property_specifications")
    assert clause["label_source"] == "property_rule"
    assert clause["risk"] == "red"
    assert any(flag["flag"] == "seller_specification_change" for flag in clause["flags"])
