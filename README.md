# SchemeSaathi — Punjab Government Scheme Finder

SchemeSaathi is a Streamlit application that helps citizens discover relevant Government of Punjab support schemes from a curated, official-source knowledge base.

## Architecture

### Citizen side

`User profile + optional field + natural-language need → Semantic RAG → preliminary eligibility → official source`

### Knowledge-maintenance side

`GitHub Actions scheduler → Source Maintenance Agent → official URL checks → replacement discovery → validation → schemes.json update → RAG uses refreshed data`

**RAG answers the citizen. The Agent maintains the knowledge.**

## Current MVP

- 36 scheme / initiative records
- Six fields: Education, Agriculture, Business, Energy, Social Welfare, Livestock
- Mandatory profile: Age, District, Occupation
- Natural-language need is the primary retrieval signal
- Sentence Transformers + FAISS semantic retrieval
- Preliminary eligibility labels; never an official government eligibility decision
- Official Government of Punjab source links
- Dastak service routing for explicit government-service queries

## Source Maintenance Agent

`update_agent.py` checks every `official_url` in `data/schemes.json`.

For a working source:
- records the verification date
- canonicalizes same-official-domain redirects

For a broken source:
- searches for a replacement using Tavily
- accepts only a reachable Punjab Government official-domain candidate
- checks scheme-name evidence
- updates only when confidence passes the conservative threshold
- otherwise marks the record unresolved instead of guessing

The agent writes a run report to:

`data/source_refresh_report.json`

## Run the Agent locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Set:

```text
TAVILY_API_KEY=your_key
```

Then:

```bash
python update_agent.py
```

The agent is intentionally conservative. A human should still verify a repaired source before relying on it for an application.

## GitHub Actions

Workflow:

`.github/workflows/source-refresh.yml`

It runs:

- automatically every Monday at 03:00 UTC
- manually through **Actions → SchemeSaathi Source Refresh → Run workflow**

Add this repository secret:

`TAVILY_API_KEY`

The workflow has permission to commit only the generated source-refresh changes back to the repository.

## Streamlit deployment

Deploy the repository as a Streamlit app using `app.py` as the entry point.

The Agent does **not** need to be exposed as a button in the public Streamlit UI. Its job is scheduled knowledge maintenance through GitHub Actions.

## Important trust rule

SchemeSaathi does not guarantee official eligibility. It provides preliminary matching and sends users to the official source for current rules and application instructions.

Never replace an uncertain source with a guessed URL.
