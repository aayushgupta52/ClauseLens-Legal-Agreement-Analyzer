from __future__ import annotations

from pathlib import Path

import pytest


def make_tiny_model(path: Path, texts: list[str]) -> Path:
    """A ~100k-parameter BERT with its own WordPiece vocab.

    Lets the tests exercise the whole fine-tuning code path offline in seconds; the numbers it
    produces mean nothing.
    """
    from tokenizers import BertWordPieceTokenizer
    from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast

    path.mkdir(parents=True, exist_ok=True)
    wordpiece = BertWordPieceTokenizer(lowercase=True)
    wordpiece.train_from_iterator(texts, vocab_size=800, min_frequency=1)
    wordpiece.save_model(str(path))
    tokenizer = BertTokenizerFast(vocab_file=str(path / "vocab.txt"), do_lower_case=True)
    tokenizer.save_pretrained(path)
    config = BertConfig(
        vocab_size=tokenizer.vocab_size,
        hidden_size=32,
        num_hidden_layers=2,
        num_attention_heads=2,
        intermediate_size=64,
        max_position_embeddings=512,
    )
    BertForSequenceClassification(config).save_pretrained(path)
    return path


@pytest.fixture(scope="session")
def tiny_model_dir(tmp_path_factory) -> Path:
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from clauselens.synth.generator import generate_samples

    records, _ = generate_samples(n_train=4, n_val=1, n_test=2, seed=0)
    return make_tiny_model(tmp_path_factory.mktemp("tiny"), [r.text for r in records])


def make_pdf(text: str) -> bytes:
    """A minimal one-page text PDF (enough for pypdf to extract `text`)."""
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out


@pytest.fixture(scope="session")
def engine():
    """A small, fully offline analysis engine (synthetic-data TF-IDF classifier + risk model)."""
    from clauselens.baselines import encode, fit, make_models
    from clauselens.classifier import TfidfClassifier, clause_labels
    from clauselens.data.taxonomy import Taxonomy
    from clauselens.pipeline import Engine
    from clauselens.risk import RiskEngine, train_risk_model
    from clauselens.synth.generator import generate_samples

    samples, _ = generate_samples(n_train=25, n_val=5, n_test=5, seed=7)
    rows = [r.model_dump() for r in samples]
    train = [r for r in rows if r["split"] == "train"]
    labels = clause_labels()
    model = make_models()["tfidf_char_svm"]
    active = fit(model, [r["text"] for r in train], encode(train, labels))
    risk = RiskEngine(train_risk_model([r for r in rows if r["split"] in ("train", "val")]))
    return Engine(
        TfidfClassifier(model, labels, active), risk, Taxonomy.load().with_other(["out_of_domain"])
    )


@pytest.fixture(scope="session")
def analyzer(engine):
    from clauselens.pipeline import Analyzer

    return Analyzer(engine)
