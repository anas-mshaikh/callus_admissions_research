# Callus Company Inc. Competency Assessment

AI Researcher submission: an AI-native admissions research workflow for US/UK university programs.

## What This Project Does

This project automates a small, judge-visible research workflow for university admissions.

It takes either:
- a program intent such as `Stanford University | Computer Science | Master's`, or
- a manual list of official source URLs

Then it:
1. discovers likely official university pages when discovery mode is used
2. fetches official pages with HTTP and browser fallback
3. extracts 4 required admissions fields
4. verifies extracted values against official page text
5. escalates weak fields to an LLM adjudicator
6. merges the strongest evidence into a final record
7. exports comparison and correction artifacts

The 4 required fields are:
- application deadline
- required English proficiency evidence
- application fee
- one notable admissions requirement

## Assessment Alignment

This repo is built to match the assessment brief closely.

### 1. Agentic workflow using multiple tools

The workflow uses distinct tool roles instead of repeated summarization:

- Search/discovery provider
  - `ADK Google Search`
  - `Google Custom Search`
  - `Vertex AI Search`
- Backend research pipeline
  - fetch
  - extraction
  - verification
  - evidence merge
- LLM adjudication provider
  - `OpenAI`
  - `Gemini`
  - `Hugging Face Inference`
- Streamlit frontend
  - operator/demo UI

This satisfies the requirement to use at least 2 tools and shows clear tool-role separation.

### 2. Official-source verification

The workflow is designed around source discipline:

- official university pages are the source of truth
- English requirement and fee pages may be used as supporting official pages
- third-party sites are not accepted as final evidence

### 3. AI vs verified distinction

The app and exports separate:

- initial AI/rule-based extracted answers
- final accepted answers verified from official pages
- correction or unresolved cases

### 4. Error correction visibility

The workflow records weak or ambiguous fields and exports them in:

- `ai_vs_verified.csv`
- `correction_log.csv`
- `source_discovery.json`

This is the evidence trail for the required “at least 3 examples where AI output was incomplete, ambiguous, or potentially incorrect.”

## Current Submission Status

What is already in the repo:

- working backend research pipeline
- separate frontend and backend processes
- dynamic discovery provider selection
- dynamic LLM provider/model selection
- manual source fallback mode
- exported comparison and correction artifacts
- sample 4-university input set in [data/inputs/universities.json](/Users/anasshaikh/Documents/Work/Interview/Callus/callus_admissions_research/data/inputs/universities.json)

What still needs to be produced for final submission:

- 2-minute `.mp4` walkthrough
- final polished run outputs using valid official university pages
- README/PDF narrative using the final verified results
- repository or Drive/Notion link for submission

## Architecture

### Frontend

[streamlit_app.py](/Users/anasshaikh/Documents/Work/Interview/Callus/callus_admissions_research/streamlit_app.py)

- judge-facing operator UI
- sends requests to backend over HTTP
- supports discovery mode and manual URL mode
- presents:
  - final results
  - source evidence
  - downloadable exports

### Backend API

[main.py](/Users/anasshaikh/Documents/Work/Interview/Callus/callus_admissions_research/src/callus_research/main.py)

- FastAPI app
- exposes `/research/run` for intent-based runs
- exposes `/research/run-target` for manual-source runs

### Core workflow

[research_workflow.py](/Users/anasshaikh/Documents/Work/Interview/Callus/callus_admissions_research/src/callus_research/services/research_workflow.py)

- intent -> discovery -> research target -> pipeline
- or manual target -> pipeline directly

[research_pipeline.py](/Users/anasshaikh/Documents/Work/Interview/Callus/callus_admissions_research/src/callus_research/services/research_pipeline.py)

- fetch
- extract
- verify
- adjudicate weak fields
- merge final record

## How the Workflow Works

### Discovery mode

Input:
- university
- country
- program
- degree type

Flow:
1. build search queries for program, admissions, English requirements, and fee pages
2. rank candidate URLs
3. keep official-source pages
4. fetch and process selected pages

### Manual mode

Input:
- university
- country
- program
- degree type
- one or more official URLs

Manual mode bypasses discovery and sends URLs directly into the backend pipeline.

Example:

```text
https://cs.stanford.edu/admissions/graduate-application-checklists
https://gradadmissions.stanford.edu/apply/application-fee | fee_page
https://gradadmissions.stanford.edu/apply/test-scores | english_requirements_page
```

## Outputs

Backend and UI exports are written or generated as:

- `target_results.json`
  - full per-target and per-page results
- `final_records.json`
  - merged final admissions answers
- `comparison_table.csv`
  - final structured comparison table
- `ai_vs_verified.csv`
  - first-pass output vs final accepted answer
- `correction_log.csv`
  - weak fields, adjudication action, and rationale
- `source_discovery.json`
  - candidate and selected discovery URLs

These outputs map directly to the assessment requirements for:
- structured comparison
- AI vs verified labeling
- documented correction cases

## Running the Project

### 1. Start the backend

```bash
uv run uvicorn callus_research.main:app --app-dir src --reload
```

Backend default:

- `http://127.0.0.1:8000`

### 2. Start the frontend

```bash
uv run streamlit run streamlit_app.py
```

### 3. Optional CLI batch run

```bash
uv run python src/scripts/run_pipeline.py
```

## Recommended Demo Flow

For the 2-minute submission video, use this order:

1. show the 4 targets:
   - 2 US universities
   - 2 UK universities
2. run discovery or manual mode
3. show final results first
4. open source evidence for one target
5. show at least 3 correction or unresolved cases
6. show exported comparison and correction artifacts

## Important Notes

- Use real official university pages in the final demo. Placeholder URLs and generic university homepages produce poor results and weaken the submission.
- Hugging Face routed inference depends on provider/task availability. If a model is not exposed for the task path being used, adjudication may fail before generation starts.
- The strongest submission is not “the model answered something.” It is “the workflow found official pages, verified answers, and documented corrections visibly.”

## Why This Fits Callus

This project is aligned with Callus because it demonstrates:

- an AI-assisted research operator workflow
- source verification instead of blind generation
- modular tool roles
- correction visibility
- reusable structured outputs for scale

That is the relevant signal for a company building AI agents for global talent and opportunity workflows.
