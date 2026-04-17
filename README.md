# Callus Admissions Research

Research pipeline for admissions requirements extraction with FastAPI endpoints, a CLI runner, and a Streamlit UI.

## Run The CLI

```bash
python src/scripts/run_pipeline.py
```

## Run The Streamlit UI

```bash
python -m streamlit run streamlit_app.py
```

The UI reuses the same pipeline as the CLI. It supports:

- running a single target from a form
- editing and saving the batch JSON input file
- reviewing final merged results and per-source diagnostics
- downloading exported JSON and CSV outputs from `data/outputs`
