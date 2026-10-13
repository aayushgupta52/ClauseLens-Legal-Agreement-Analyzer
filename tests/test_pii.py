from __future__ import annotations

from clauselens.pii import mask_pii, unmask

TEXT = (
    "Aadhaar 1234 5678 9012, PAN ABCDE1234F, mobile +91 98765 43210, mail ravi.k@example.com, "
    "A/c No. 123456789012, IFSC HDFC0001234."
)


def test_every_identifier_type_is_masked():
    masked, counts, mapping = mask_pii(TEXT)
    for secret in ("1234 5678 9012", "ABCDE1234F", "98765 43210", "ravi.k@example.com",
                   "123456789012", "HDFC0001234"):  # fmt: skip
        assert secret not in masked
    assert counts == {"ACCOUNT": 1, "AADHAAR": 1, "PAN": 1, "IFSC": 1, "EMAIL": 1, "PHONE": 1}
    assert unmask(masked, mapping) == TEXT


def test_same_value_gets_the_same_token_across_formats():
    masked, counts, _ = mask_pii("Call 9876543210 or +91 98765 43210 or 98765-43210.")
    assert counts == {"PHONE": 1} and masked.count("[PHONE_1]") == 3


def test_amounts_dates_and_durations_are_left_alone():
    text = "Rent Rs. 1,50,000/- on 5th March 2025 for 12 months, deposit Rs.35000, 10% increase."
    assert mask_pii(text)[0] == text


def test_empty_text():
    assert mask_pii("") == ("", {}, {})
