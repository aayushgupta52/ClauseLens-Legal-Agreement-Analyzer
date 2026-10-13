from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compare_reports  # noqa: E402


def _metrics(micro: float, macro: float) -> dict:
    return {"micro_f1": micro, "macro_f1": macro, "n": 10}


def test_comparison_table_merges_baselines_and_transformers(tmp_path):
    (tmp_path / "baselines_v1.json").write_text(
        json.dumps({"models": {"tfidf_lr": {"real_test": _metrics(0.88, 0.83)}}})
    )
    (tmp_path / "transformer_x.json").write_text(
        json.dumps(
            {
                "config": {"model_name": "org/some-bert"},
                "final": {"real_test": _metrics(0.93, 0.9), "gold": _metrics(0.5, 0.4)},
            }
        )
    )
    table = compare_reports.to_markdown(compare_reports.collect(tmp_path))
    lines = table.splitlines()
    assert lines[0] == "| model | real_test micro / macro F1 | gold micro / macro F1 |"
    assert "| tfidf_lr | 0.880 / 0.830 | - |" in lines
    assert "| org/some-bert | 0.930 / 0.900 | 0.500 / 0.400 |" in lines
