from __future__ import annotations

from clauselens.storage import Store

REPORT = {
    "report_id": "abc123", "created_utc": "2026-10-11T10:00:00+00:00", "doc_type": "rent_agreement",
    "summary": {"overall_risk": "amber"}, "clauses": [{"index": 0}],
}  # fmt: skip


def test_save_get_list_delete_roundtrip():
    store = Store("sqlite://")
    store.save(REPORT)
    store.save({**REPORT, "report_id": "zzz999", "created_utc": "2026-10-12T10:00:00+00:00"})
    assert store.get("abc123") == REPORT
    assert [r["report_id"] for r in store.list()] == ["zzz999", "abc123"]  # newest first
    assert store.list()[1]["title"] == "Rent Agreement · 2026-10-11"
    assert store.delete("abc123") is True and store.delete("abc123") is False
    assert store.get("abc123") is None


def test_feedback_is_stored_and_deleted_with_the_report():
    store = Store("sqlite://")
    store.save(REPORT)
    store.add_feedback("abc123", 0, ["security_deposit"], "red", "wrong label")
    assert store.feedback("abc123") == [
        {"clause_index": 0, "labels": ["security_deposit"], "risk": "red", "note": "wrong label",
         "created_utc": store.feedback("abc123")[0]["created_utc"]}
    ]  # fmt: skip
    store.delete("abc123")
    assert store.feedback("abc123") == []


def test_file_database_persists_between_instances(tmp_path):
    path = tmp_path / "sub" / "app.db"
    Store(str(path)).save(REPORT)
    assert Store(str(path)).get("abc123") == REPORT
