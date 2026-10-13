from __future__ import annotations

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from transformers import AutoTokenizer  # noqa: E402

from clauselens.data.taxonomy import Taxonomy  # noqa: E402
from clauselens.finetune import HEAD_FILE, TrainConfig, train, truncated_fraction  # noqa: E402
from clauselens.inference import ClauseClassifier, classify_document  # noqa: E402
from clauselens.segment import segment_document  # noqa: E402
from clauselens.synth.generator import generate_documents, generate_samples  # noqa: E402


def test_truncated_fraction(tiny_model_dir):
    tokenizer = AutoTokenizer.from_pretrained(tiny_model_dir)
    assert truncated_fraction(tokenizer, ["word " * 500, "short text"], 64) == 0.5
    assert truncated_fraction(tokenizer, [], 64) == 0.0


@pytest.fixture(scope="module")
def trained(tmp_path_factory, tiny_model_dir):
    records, _ = generate_samples(n_train=6, n_val=2, n_test=3, seed=1)
    rows = [r.model_dump() for r in records]
    by_split = {s: [r for r in rows if r["split"] == s] for s in ("train", "val", "test")}
    labels = Taxonomy.load().with_other(["out_of_domain"]).clause_ids
    cfg = TrainConfig(
        model_name=str(tiny_model_dir), epochs=2, batch_size=16, max_len=64, lr=5e-3,
        fp16=False, select_on="synth_val",
    )  # fmt: skip
    out = tmp_path_factory.mktemp("trained")
    eval_sets = {"synth_val": by_split["val"], "synth_test": by_split["test"]}
    return train(by_split["train"], eval_sets, labels, cfg, out), out, labels


def test_training_report_and_artifacts(trained):
    report, out, labels = trained
    assert (out / "config.json").exists() and (out / HEAD_FILE).exists()
    assert report["selected_on"] == "synth_val" and report["best_epoch"] in (1, 2)
    assert len(report["history"]) == 2
    assert report["history"][1]["train_loss"] < report["history"][0]["train_loss"]
    assert "termination" in report["inactive_labels"]  # only synthetic labels were trained on
    assert set(report["final"]) == {"synth_val", "synth_test"}
    for metrics in report["final"].values():
        assert 0.0 <= metrics["micro_f1"] <= 1.0 and 0.0 <= metrics["macro_f1"] <= 1.0


def test_classifier_never_predicts_unseen_labels(trained):
    report, out, labels = trained
    clf = ClauseClassifier(out, device="cpu")
    texts = ["The deposit shall be refunded within 30 days.", "gibberish zzz qqq"]
    probs = clf.predict_proba(texts)
    assert probs.shape == (2, len(labels))
    for i, label in enumerate(labels):
        if label in report["inactive_labels"]:
            assert probs[:, i].max() < 1e-6
    for pred in clf.predict(texts):
        assert pred["labels"] and not set(pred["labels"]) & set(report["inactive_labels"])
        assert len(pred["top"]) == 3


def test_classify_document_returns_one_row_per_segment(trained):
    _, out, _ = trained
    clf = ClauseClassifier(out, device="cpu")
    doc = generate_documents(1, seed=5)[0]
    rows = classify_document(doc["text"], clf)
    assert len(rows) == len(segment_document(doc["text"]))
    assert {r["kind"] for r in rows} >= {"clause", "trailer"}
    assert all(r["labels"] for r in rows)
