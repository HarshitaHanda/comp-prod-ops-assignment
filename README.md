# Composio AI Product Ops - 100 App Research Agent

A reproducible research pipeline and single-page case study for the Composio AI Product Ops Intern take-home.

**Live case study:** deploy this repository directly on Vercel.  
**Research set:** 100 apps across CRM, support, communications, marketing, ecommerce, data/SEO, developer infra, productivity, fintech, and AI/media.

## What this project does

The assignment is not just "fill 100 rows." The project is built around three things:

1. **Automated research** - start from the official URL for each app, crawl likely API/auth/developer documentation, and extract structured claims.
2. **Pattern finding** - calculate auth, access, buildability, blocker, category, and Composio-toolkit patterns across the full set.
3. **Verification** - re-check a sample through a separate browser-rendered path, log corrections, and support explicit human checks.

The static frontend reads the generated JSON and turns it into the two-minute case study required by the brief.

## Architecture

```text
data/apps.json
      |
      v
requests + BeautifulSoup crawler
(official domain only)
      |
      v
structured LLM extraction
      |
      +----> Composio SDK toolkit-catalog enrichment
      |
      v
data/results.json
      |
      v
Playwright / Chromium verification sample
      |
      +----> logged corrections
      +----> human check records
      |
      v
data/verification.json
      |
      v
summary counts + static case-study UI
```

### Why Composio is used this way

The Composio SDK is not imported as decoration. The pipeline uses the official Python SDK to load the live toolkit catalog and record whether each researched app already has a matching Composio toolkit. That is useful Product Ops context while keeping the actual API/auth verdict grounded in the app's own official documentation.

## Local setup

### 1. Clone and create an environment

```bash
git clone https://github.com/HarshitaHanda/comp-prod-ops-assignment.git
cd comp-prod-ops-assignment

python -m venv .venv
```

Activate it:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure secrets

Copy `.env.example` to `.env` and add your own keys:

```env
COMPOSIO_API_KEY=ak_...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5-mini
```

`.env` is gitignored. Never commit API keys.

## Run the pipeline

For a safe first test, research only three apps:

```bash
python -m agent.run_pipeline --limit 3 --skip-verify
```

Research the full 100:

```bash
python -m agent.run_pipeline
```

Resume from a specific app:

```bash
python -m agent.run_pipeline --start 41
```

Run only the verification pass:

```bash
python -m agent.verify --sample-size 15
python -m agent.summary
```

The research script checkpoints `data/results.json` after every app, so a failed row does not wipe previous work.

## Data contract

Each researched app includes:

```json
{
  "id": 1,
  "name": "Example",
  "category": "CRM and Sales",
  "description": "One-line description",
  "auth_methods": ["OAuth2"],
  "access_model": "self-serve-free",
  "api_surface": "Public REST API; broad read/write surface",
  "mcp_status": "none-found",
  "buildability": "yes",
  "main_blocker": null,
  "composio_toolkit": {
    "name": "Example",
    "slug": "example"
  },
  "confidence": 0.94,
  "evidence": [
    {
      "url": "https://official.example.dev/docs/auth",
      "supports": "OAuth2 developer authentication"
    }
  ]
}
```

## Verification design

The first pass and verification pass deliberately use different retrieval paths:

- **Pass 1:** `requests` + BeautifulSoup, crawling the official domain.
- **Pass 2:** Playwright/Chromium renders sampled evidence pages, which catches JS-only docs and challenges every material field.
- **Human pass:** manual checks are recorded in `data/human_checks.json`.

Corrections are retained in `data/verification.json` instead of silently overwriting the mistake history. That lets the case study show what was wrong and how verification improved it.

## Human checks

After manually checking a sampled app against official docs, add an entry to `data/human_checks.json`:

```json
{
  "checks": [
    {
      "app_id": 1,
      "app_name": "Salesforce",
      "claims_checked": 6,
      "claims_correct_after_verification": 6,
      "notes": "Checked auth, API surface, access gate, MCP, buildability and blocker.",
      "evidence": ["https://developer.salesforce.com/..."]
    }
  ]
}
```

Then rerun:

```bash
python -m agent.verify --sample-size 15
python -m agent.summary
```

## Serve the case study locally

Any static server works:

```bash
python -m http.server 8000
```

Open `http://localhost:8000`.

## Deploy on Vercel

Import this GitHub repository into Vercel as a new project.

- Framework preset: **Other**
- Build command: leave empty
- Output directory: leave empty
- Root directory: repository root

Because the deliverable is static HTML/CSS/JS plus JSON, Vercel can serve it directly. No secrets are required for the deployed case-study page; API keys are only needed when running the research pipeline locally.

## Repository structure

```text
.
+-- agent/
|   +-- browser_verifier.py
|   +-- composio_enrichment.py
|   +-- crawler.py
|   +-- llm.py
|   +-- models.py
|   +-- research.py
|   +-- run_pipeline.py
|   +-- summary.py
|   +-- verify.py
+-- data/
|   +-- apps.json
|   +-- human_checks.json
|   +-- results.json
|   +-- summary.json
|   +-- verification.json
+-- index.html
+-- app.js
+-- styles.css
+-- requirements.txt
+-- vercel.json
+-- .env.example
```

## Honesty / limitations

- A retrieved marketing page is not treated as proof of API access.
- If official source retrieval fails, the row is flagged `needs-human`.
- `none-found` for MCP means no official MCP was found in the pages inspected; it is not a claim that no MCP exists anywhere.
- Some access gates are only visible after login or sales contact, so those require manual confirmation.
- The initial committed dataset is intentionally `pending`; the repository does not ship invented findings or fake accuracy numbers.

## Author

Harshita Handa
