# ClauseLens

Upload a **rent / Leave & License agreement** or a **job offer / service-bond letter** and ClauseLens

- splits it into clauses and recognises the clause type (deposit, lock-in, notice, bond, ...),
- extracts the key terms (amounts, periods, percentages) verbatim from the text,
- flags risky clauses **green / amber / red** with a reason and a negotiation tip,
- explains everything in plain **English or Hinglish**, with optional translated report output,
- lists clauses a good agreement should have but yours seems to lack,
- answers questions about the contract with citations ("Deposit kab wapas milega?"),
- includes a **bond cost calculator**, and masks Aadhaar / PAN / phone / e-mail / account numbers
  *before* anything else touches the text.

It is an **awareness tool, not legal advice**. See "Limitations" below.

## Quick start

Needs Python 3.10+ and internet (CUAD is downloaded from GitHub).

```bash
unzip clauselens-complete.zip && cd clauselens
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[all]"
python scripts/run_all.py            # data -> train -> evaluate -> tests   (a few minutes)
python scripts/serve.py              # then open http://127.0.0.1:8000
```

* No Hugging Face access? `python scripts/run_all.py --skip-ledgar` (CUAD + synthetic data only).
  `run_all.py` also falls back to that by itself if the LEDGAR download fails.
* The app works even before `run_all.py`: on first start it trains its small models from
  synthetic data (about 30 s). Run `run_all.py` once to get the real data in, too.

## React frontend (responsive UI)

ClauseLens includes a React + Vite frontend in `frontend/`. It keeps the existing Python analysis engine and FastAPI endpoints; the React UI calls those endpoints through the Vite `/api` proxy.

### Development on Windows

Open two VS Code terminals from the project root.

**Terminal 1 — start the Python backend:**

```powershell
.venv\Scripts\Activate.ps1
python scripts/serve.py
```

**Terminal 2 — start the React frontend:**

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://127.0.0.1:5173`. Keep both terminals running while developing. The frontend is responsive for desktop, tablet, and mobile widths.

### Build the frontend for the regular Python URL

```powershell
cd frontend
npm install
npm run build
cd ..
python scripts/serve.py
```

After a successful build, FastAPI serves `frontend/dist` at `http://127.0.0.1:8000` and leaves the existing `/api/*` routes active. If no React build exists, the original HTML interface remains as a fallback.

The “Download PDF” action opens the browser print dialog; choose **Save as PDF** to save the report. The print view includes a separate full-report layout, so it includes the summary, all key facts, missing-term checks, and every clause even when the on-screen report was displaying only one tab. It does not claim a server-side PDF has been generated.

### Multilingual document and report translation (optional)

The analyzer is still primarily English-oriented. For a non-English source document, ClauseLens can detect/select the source language, translate a temporary analysis copy to English, classify it with the existing model, and preserve matched original-language wording for comparison. Translation quality and risk classification for non-English legal documents have not been validated on a gold dataset; always verify each finding against the original clause. If a source clause cannot be matched confidently after translation, the UI labels the English analysis text instead of presenting it as original wording.

A LibreTranslate-compatible service is required for translating non-English documents or report explanations. To run the local service with Docker Desktop:

```powershell
docker compose -f docker-compose.translation.yml up
```

This binds the service to `127.0.0.1:5000`. Supported language pairs depend on the language models available in that service. English analysis works without the translation service. To use scanned PDFs, the optional Python OCR dependencies are included in `.[all]`, but the Tesseract application and the required Tesseract language data must also be installed on Windows.

## What `run_all.py` does

| step | script | output |
|---|---|---|
| 1 | `download_cuad.py` | `data/raw/cuad/` (checksum verified, CC BY 4.0) |
| 2 | `download_ledgar.py` | `data/raw/ledgar/` (LexGLUE, optional) |
| 3 | `build_dataset_v1.py` | `data/processed/v1/` clean, de-duplicated, leakage-checked train/val/test |
| 4 | `generate_synthetic.py` | `data/processed/synth_v1/` + synthetic documents (rent / bond clauses have no public data) |
| 5 | `train_baselines.py` | `models/*.joblib`, `reports/baselines_v1.json` |
| 6 | `evaluate_components.py` | `reports/components.json`, **`reports/SUMMARY.md`** |
| 7 | `pytest` | the whole test-suite |

## Using it

**Web UI** (`python scripts/serve.py`): paste text or upload `.txt` / `.docx` / `.pdf`, pick English or
Hinglish, press *Analyze*. Tabs: Analyze, Model Lab (metrics), About. Reports are saved in a local
SQLite file (`data/app/clauselens.db`) and can be deleted from the UI. Untick "save in history" to keep
nothing.

**API** (docs at `http://127.0.0.1:8000/docs`):

```bash
curl -s localhost:8000/api/sample | python -c "import sys,json;print(json.load(sys.stdin)['text'])" > sample.txt
curl -s -X POST localhost:8000/api/analyze -H 'Content-Type: application/json' \
     -d "{\"text\": $(python -c 'import json;print(json.dumps(open("sample.txt").read()))'), \"language\": \"hinglish\"}"
curl -s -X POST localhost:8000/api/analyze/file -F file=@agreement.docx -F language=en
curl -s -X POST localhost:8000/api/calc/bond -H 'Content-Type: application/json' \
     -d '{"bond_amount": 120000, "bond_months": 12, "months_served": 3, "mode": "pro_rata"}'
```

| endpoint | purpose |
|---|---|
| `POST /api/analyze`, `POST /api/analyze/file` | full analysis (text or file) |
| `GET /api/reports`, `GET/DELETE /api/reports/{id}` | history |
| `POST /api/reports/{id}/ask`, `POST /api/ask` | ask-your-contract (stored / stateless) |
| `POST /api/reports/{id}/feedback` | user corrections (stored for later retraining) |
| `POST /api/calc/bond` | bond cost calculator |
| `GET /api/sample`, `/api/health`, `/api/metrics` | sample text, status, evaluation numbers |
| `GET /api/translation/status`, `POST /api/translate/report` | translation-service status and report translation |

## How it works

```
text / .docx / .pdf
   -> PII shield (mask Aadhaar, PAN, phone, e-mail, account, IFSC)          pii.py
   -> segmenter (numbering, headings, signature block, wrapped lines)        segment.py
   -> clause classifier (TF-IDF SVM; BERT optional)                          classifier.py
        + heading / keyword hints when the model is unsure                   hints.py
   -> key facts (money, durations, %, dates + role)                          facts.py
   -> risk = worse of {transparent rules, small ML model}                    risk.py
   -> (review step for uncertain clauses)                                    pipeline.py
   -> explanations (fixed templates, EN / Hinglish, numbers copied verbatim) explain.py
   -> missing-clause check, report                                           gaps.py, pipeline.py
```

The steps are plain functions wired into a **LangGraph** `StateGraph` (conditional edge
`risk -> review | explain`); the same functions also run without LangGraph and the tests assert both
produce the same report. Explanations are **templates, not a generative model**, so they cannot invent
numbers. `check_grounded` verifies that every number shown comes from the clause itself.

Taxonomy: `configs/taxonomy.yaml` (36 clause types + "other"). Scope: `configs/scope.yaml`.
Risk rubric: `docs/risk_rubric.md`.

## Evaluation: read this before trusting a number

`reports/SUMMARY.md` is generated by `run_all.py`. Most numbers are on **synthetic** data. Rent / bond
clauses have no public labeled data, so they were generated from hand-written templates, with the test
split using phrasing the training split never saw. That proves the components work and shows the
generalisation gap (validation 1.0 vs test ~0.5 for the TF-IDF model). It does **not** tell you how
well ClauseLens does on real Indian agreements. For that build a gold set:

```bash
# put 30-50 anonymised agreements as .txt into data/gold/raw/
python -m clauselens.gold prepare                      # -> data/gold/annotation_template.csv
# two people fill clause_types (a|b for several, "other" for non-clauses) and risk independently
python -m clauselens.gold validate annotator_a.csv
python -m clauselens.gold agreement --a annotator_a.csv --b annotator_b.csv   # Cohen's kappa
python -m clauselens.gold export --csv adjudicated.csv                        # -> data/gold/gold_v1.jsonl
python scripts/train_baselines.py                      # a "gold" column now appears
```

## Optional: BERT fine-tuning on Colab (Phase 4)

`notebooks/04_finetune_colab.ipynb` fine-tunes legal-BERT / InLegalBERT / bert-base on a T4 GPU, compares
them with the TF-IDF baselines, and demos document classification. Upload `clauselens-complete.zip`
to Colab and run the cells top to bottom (the notebook runs the tests first). To use a fine-tuned model
in the app:

```bash
pip install -e ".[nlp]"
export CLAUSELENS_CLASSIFIER=transformer CLAUSELENS_TRANSFORMER_DIR=models/nlpaueb__legal-bert-base-uncased
python scripts/serve.py
```

The PyTorch code could not be executed where this project was built (no GPU / torch download); its
tests run a tiny BERT on CPU and are skipped when torch is not installed. Run `pytest` after
`pip install -e ".[nlp]"` before trusting a long training run.

## Tests

```bash
pytest                                        # ~110 tests, a few seconds to a minute
# optional UI check in a simulated browser (needs Node.js):
python scripts/serve.py &                     # in one terminal
cd tests/ui_smoke && npm install && node ui_test.js
```

## Privacy

Structured identifiers are masked before analysis and the masked text is what is stored. **Names and
addresses are not masked** (that needs an NER model). Nothing leaves your machine: there are no external
API calls and the UI loads no external scripts or fonts. Delete any report from the UI or with
`DELETE /api/reports/{id}`.

## Limitations (honest list)

* Accuracy on real agreements is unmeasured until you build a gold set.
* Risk rules and thresholds are working hypotheses: **have an advocate validate them**.
* Synthetic rent / bond data has low diversity; paraphrase augmentation (e.g. with an LLM) and real
  labelled agreements are the main upgrade path.
* Clause classification remains English-oriented. Non-English clauses are machine-translated to English first, which can lose legal nuance; accuracy on real multilingual Indian agreements has not been measured against a validated gold set.
* Scanned PDFs require the optional OCR libraries, the Tesseract application, and matching Tesseract language data. Photos and poor-quality scans can still fail. Amount formats outside common `Rs. 1,50,000/-` / `INR` / `₹` / `lakh` styles may be missed.
* The classifier can misjudge unseen phrasing; the UI marks low-confidence clauses "review".

## Data and model licences

CUAD (CC BY 4.0, Hendrycks et al. 2021) and LEDGAR via LexGLUE (CC BY 4.0). `nlpaueb/legal-bert-base-uncased`
is CC BY-SA 4.0; check the model card of any other model you fine-tune. Synthetic data is generated
locally and contains no real people (names are random combinations).

## Layout

```
configs/    scope + clause taxonomy          docs/       risk rubric
scripts/    run_all, serve, data + training  notebooks/  Colab fine-tuning
src/clauselens/
  data/ (CUAD/LEDGAR adapters, dedupe, splits)   synth/ (templates + generator)
  segment, classifier, facts, risk, explain, pii, gaps, hints, qa, calculators, pipeline,
  api, storage, ingest, web/index.html           baselines, finetune, inference (BERT), gold
tests/      pytest suite + ui_smoke (Node, optional)
```
