# Callus Company Inc. Competency Assessment

## AI Researcher Submission

### Verification-First Agentic Workflow for US/UK University Admissions Research

## Overview

This project is a small AI-native research workflow designed to automate part of the university admissions research process while preserving source-level accuracy.

The workflow is built around a simple principle:

**AI is used as a research accelerator, not as the source of truth.**

Given either:

* a university + program research intent, or
* a manually curated list of official university URLs,

the system discovers relevant official pages, extracts required admissions information, verifies the output against source text, escalates weak fields for LLM-assisted adjudication, and produces structured comparison and correction artifacts.

This submission is intentionally designed to match the Callus assessment brief: a **repeatable, scalable, verification-first research workflow** that makes AI-generated outputs visible, corrects ambiguity using official sources, and presents final results clearly.

---



## Why This Workflow Is Scalable

This project is intentionally small for the assessment, but the design is meant to scale beyond four universities.

### 1. Modular stages

Discovery, extraction, verification, adjudication, and export are separated cleanly. This makes the workflow easier to extend to new institutions, new countries, or new research domains.

### 2. Structured outputs

Because the system emits machine-readable artifacts, the workflow can support:

* larger university sets
* repeated monitoring
* audit trails
* downstream reporting systems
* future AI agents built on top of prior verified data

### 3. Cost-effective repeated usage

A practical scaling improvement is to persist verified results after the expensive work is complete.

A production version of this system can:

* **store verified final records in a database** for fast lookups,
* **cache recent runs** for short-term reruns,
* **avoid repeating expensive search + extraction + adjudication** for unchanged targets,
* and  **refresh data only when a record expires or a source changes** .

That means the costly workflow runs once, the verified record is stored, and later requests can be served quickly and cheaply until the data reaches its refresh window.

This improves:

* **speed** for repeated research requests,
* **cost efficiency** by reducing unnecessary LLM and fetch operations,
* and **operational scalability** when the number of university targets grows.

A simple lifecycle would be:

**discover once → verify once → store in DB → serve from cache/DB → refresh on expiry**

This is a much better long-term model than re-running full web research every time.

### Better support for Callus-style research operations

The same architecture could support future workflows such as:

* global opportunity research
* scholarship discovery
* talent-support guidance
* role-specific AI research operators
* verified knowledge layers for higher-volume admissions workflows

---

## Running the Project

### 1. Start the backend

```bash
uv run uvicorn callus_research.main:app --app-dir src --reload
```

Default backend URL:
`http://127.0.0.1:8000`

### 2. Start the frontend

```bash
uv run streamlit run streamlit_app.py
```

### 3. Optional CLI batch run

```bash
uv run python src/scripts/run_pipeline.py
```

---

## Submission is designed to show five things:

1. **Workflow design**
   A clear research pipeline with distinct stages for discovery, extraction, verification, adjudication, and reporting.
2. **Meaningful tool usage**
   Multiple tools are used for different roles rather than duplicating the same summarization step.
3. **Official-source discipline**
   Final answers are grounded in official university admissions pages, not third-party summaries.
4. **Visible correction logic**
   Weak, incomplete, or potentially incorrect AI outputs are surfaced and corrected transparently.
5. **Scalability potential**
   The workflow produces structured outputs that can support future admissions intelligence and broader talent-support research operations.

---

## Assessment Alignment

This project was built specifically to satisfy the requirements of the Callus AI Researcher competency assessment.

### 1. Mini agentic research workflow

The system runs a structured research flow rather than a one-off chat interaction:

**Input intent or official URLs → source discovery → page fetch → field extraction → verification → LLM adjudication for weak fields → field merge → final export**

This makes the workflow repeatable, auditable, and easier to scale.

### 2. Use of multiple tools

The workflow uses at least two distinct tools with different responsibilities:

* **Search / discovery provider**
  * ADK Google Search
  * Google Custom Search
  * Vertex AI Search
* **Backend research pipeline**
  * page fetching
  * extraction
  * verification
  * evidence merge
* **LLM adjudication provider**
  * OpenAI
  * Gemini
  * Hugging Face Inference
* **Streamlit frontend**
  * operator-facing review and export UI

### 3. Required admissions fields

The workflow extracts the four fields requested in the assignment:

* **Application deadline**
* **Required English proficiency evidence**
* **Application fee**
* **One notable admissions requirement**

### 4. AI-generated vs officially verified distinction

The system explicitly separates:

* first-pass extracted answers
* final accepted answers
* corrected or unresolved cases
* official source evidence

This is surfaced in both the UI and exported artifacts.

### 5. Error correction and reasoning

The workflow records weak or ambiguous fields and preserves them in reviewable outputs such as:

* `ai_vs_verified.csv`
* `correction_log.csv`
* `source_discovery.json`

These artifacts are designed to support the assignment requirement to identify cases where AI output was incomplete, ambiguous, or potentially incorrect, then correct those cases using official university sources.---

## Workflow Design

## 1. Input

The system accepts either:

### A. Discovery mode

A structured research intent:

* university name
* country
* program name
* degree type

### B. Manual mode

A curated list of official source URLs, used when discovery should be bypassed or tightly controlled.

---

## 2. Source discovery

In discovery mode, the system generates and ranks likely official pages for:

* program details
* admissions requirements
* English language requirements
* fee information

We designed the system locate the **right official university pages** for downstream extraction and verification.

---

## 3. Fetching and raw storage

Once candidate pages are selected, the backend fetches the source content using:

* HTTP first
* browser fallback when required

The raw HTML is preserved so that extraction and verification can be reproduced later.

---

## 4. Extraction

The pipeline extracts the required admissions fields from saved page content:

* application deadline
* English requirement
* application fee
* notable requirement

This first pass is intentionally treated as provisional.

---

## 5. Verification

Each extracted field is checked against page text to determine whether the extracted answer is:

* supported,
* weak,
* ambiguous,
* or unresolved.

This is the most important quality layer in the workflow.

---

## 6. LLM adjudication for weak fields

If a field remains weak or uncertain after rule-based verification, the system escalates only that field to an LLM adjudicator.

The adjudicator returns a structured decision such as:

* `keep`
* `replace`
* `unresolved`

along with:

* rationale
* citation type
* citation text
* confidence

This ensures LLM usage is targeted and reviewable rather than hidden or overly broad.

---

## 7. Merge and final record creation

After processing multiple pages for the same university-program target, the system merges the strongest field-level evidence into one final record.

This final record is what powers the comparison table and exported outputs.

---

## Output Artifacts

The workflow generates artifacts that map directly to the assessment requirements.

### `target_results.json`

Full per-target and per-page workflow output.

### `final_records.json`

Merged final admissions answers per target.

### `comparison_table.csv`

Final structured comparison table for all required fields.

### `ai_vs_verified.csv`

First-pass extracted output compared against final accepted answers.

### `correction_log.csv`

Weak fields, adjudication actions, and rationale.

### `source_discovery.json`

Candidate and selected URLs from the discovery stage.

These outputs make the workflow easier to inspect, explain, and defend.

---

## Why This Workflow Is Scalable

This project is intentionally small for the assessment, but the design is meant to scale beyond four universities.

### 1. Modular stages

Discovery, extraction, verification, adjudication, and export are separated cleanly. This makes the workflow easier to extend to new institutions, new countries, or new research domains.

### 2. Structured outputs

Because the system emits machine-readable artifacts, the workflow can support:

* larger university sets
* repeated monitoring
* audit trails
* downstream reporting systems
* future AI agents built on top of prior verified data

### 3. Cost-effective repeated usage

A practical scaling improvement is to persist verified results after the expensive work is complete.

A production version of this system can:

* **store verified final records in a database** for fast lookups,
* **cache recent runs** for short-term reruns,
* **avoid repeating expensive search + extraction + adjudication** for unchanged targets,
* and  **refresh data only when a record expires or a source changes** .

That means the costly workflow runs once, the verified record is stored, and later requests can be served quickly and cheaply until the data reaches its refresh window.

This improves:

* **speed** for repeated research requests,
* **cost efficiency** by reducing unnecessary LLM and fetch operations,
* and **operational scalability** when the number of university targets grows.

A simple lifecycle would be:

**discover once → verify once → store in DB → serve from cache/DB → refresh on expiry**

This is a much better long-term model than re-running full web research every time.

## Current Project Structure

### Frontend

`streamlit_app.py`

Responsibilities:

* judge-facing operator UI
* runtime configuration
* discovery vs manual mode input
* final result review
* evidence inspection
* export downloads

### Backend API

`src/callus_research/main.py`

Responsibilities:

* expose research endpoints
* receive structured targets/intents
* return typed workflow results

### Core workflow

`src/callus_research/services/research_workflow.py`

Responsibilities:

* intent handling
* discovery orchestration
* routing into the research pipeline

### Pipeline

`src/callus_research/services/research_pipeline.py`

Responsibilities:

* page fetch
* extraction
* verification
* weak-field adjudication
* final field merge
