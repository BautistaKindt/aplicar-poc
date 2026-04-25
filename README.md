# Aplicar — ATS Adapter POC

A command-line proof of concept that fetches open jobs from multiple ATS platforms, normalizes them into a unified schema, and filters for Argentina-relevant roles.

## What it does

1. Reads `companies.yaml` to know which companies to fetch and which ATS each uses.
2. Calls the appropriate adapter for each company (Greenhouse, SmartRecruiters, Workday).
3. Normalizes every job into a shared `Job` object (title, location, apply URL, etc.).
4. Filters for Argentina-relevant jobs using keyword matching on location, title, and description.
5. Writes the filtered results to `jobs.json`.
6. Prints a summary to the terminal.

## Setup

```bash
# Clone / enter the directory
cd aplicar-poc

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

You'll see live INFO logs on stderr as each company is fetched, then a summary like:

```
Fetched 847 jobs across 8 companies in 3 ATS platforms
  Greenhouse: 312 jobs (4 companies)
  Smartrecruiters: 428 jobs (2 companies)
  Workday: 107 jobs (2 companies)

Argentina-relevant: 34 jobs

Top companies by Argentine openings:
  Globant: 21
  Accenture: 8
  GitLab: 5

Output written to jobs.json
```

## Project structure

```
aplicar-poc/
├── main.py              # Entry point — orchestrates fetch, filter, output
├── models.py            # Shared Job dataclass
├── filters.py           # Argentina-relevance filter (easy to tune)
├── companies.yaml       # List of companies and their ATS config
├── requirements.txt
├── adapters/
│   ├── greenhouse.py    # Greenhouse adapter
│   ├── smartrecruiters.py  # SmartRecruiters adapter
│   └── workday.py       # Workday adapter
└── jobs.json            # Output (created after running)
```

## Adapters

### Greenhouse (`adapters/greenhouse.py`)
- **Endpoint:** `GET https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs?content=true`
- **Auth:** None — fully public
- **Pagination:** None needed — all jobs returned in one response
- **Companies:** Stripe, Airbnb, Dropbox, GitLab

### SmartRecruiters (`adapters/smartrecruiters.py`)
- **Endpoint:** `GET https://api.smartrecruiters.com/v1/companies/{tenant}/postings?limit=100`
- **Auth:** None — fully public
- **Pagination:** offset-based, walks pages until fewer than 100 results returned
- **Companies:** Globant (tenant: `Globant2`), Globant Commerce Studio

### Workday (`adapters/workday.py`)
- **Endpoint:** `POST https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs`
- **Auth:** None, but requires browser-like headers (User-Agent, Referer) to avoid 403s
- **Pagination:** offset-based with page size 20, continues until `jobPostings` is empty or offset ≥ total
- **Companies:** Accenture, NVIDIA
- **Note:** Workday list responses do not include full job descriptions — only title, location, and a link to the detail page. This is intentional for the POC; description fetching can be added later.

## Adding a new company

1. Find the company's ATS and tenant slug.
2. Add an entry to the relevant section in `companies.yaml`.
3. Run `python main.py` — no code changes needed.

## Adding a new ATS

1. Create `adapters/your_ats.py` with a `fetch_jobs(company_config: dict) -> list[Job]` function.
2. Register it in the `ADAPTER_MAP` in `main.py`.
3. Add companies under the new ATS key in `companies.yaml`.

## Tuning the Argentina filter

Edit `filters.py`:
- Add terms to `ARGENTINA_TERMS` to catch more locations.
- Add terms to `REMOTE_TERMS` to catch more remote-work signals.
- The filter checks location first, then falls back to title + description for remote roles.
