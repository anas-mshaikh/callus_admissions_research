# Callus Admissions Research

AI-native admissions research workflow with official-source discovery, structured extraction, verification, targeted LLM adjudication, and a Streamlit operator UI.

## Workflow

1. Input university, country, program, and degree intent
2. Discover likely official URLs with ADK Google Search
3. Fetch and parse selected official pages
4. Extract required admissions fields
5. Verify values against official source text
6. Adjudicate weak fields with an LLM
7. Export final comparison, discovery, and correction artifacts

## Source Policy

- Official university pages are the source of truth
- English requirement and fee pages may be used as supporting official sources
- Third-party sites are never accepted as final evidence

## Run The CLI

```bash
python src/scripts/run_pipeline.py
```

## Run The Streamlit UI

```bash
python -m streamlit run streamlit_app.py
```

The UI reuses the same pipeline as the CLI. It supports:

- running a program-specific research intent from a form
- editing and saving batch input JSON
- viewing workflow, source discovery, final comparison, AI-vs-verified, and corrections
- downloading exported JSON and CSV artifacts from `data/outputs`
