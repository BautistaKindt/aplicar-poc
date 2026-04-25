"""
Aplicar ATS Adapter POC — main entry point.

Reads companies from companies.yaml, dispatches to the right adapter,
collects all jobs, filters for Argentina-relevant roles, writes jobs.json,
and prints a summary.
"""

import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path

import yaml

from adapters import greenhouse, globant, lever, loreal, mercadolibre, pepsico, smartrecruiters, workday
from adapters.workday import fetch_job_detail, _strip_html as _workday_strip_html
from filters import filter_argentina_jobs
from models import Job

# Show INFO logs so the user can see progress as it runs
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Map ATS name (as it appears in companies.yaml) → adapter module
ADAPTER_MAP = {
    "greenhouse": greenhouse,
    "globant": globant,
    "lever": lever,
    "loreal": loreal,
    "mercadolibre": mercadolibre,
    "pepsico": pepsico,
    "smartrecruiters": smartrecruiters,
    "workday": workday,
}

OUTPUT_FILE = Path("jobs.json")


def load_companies(path: str = "companies.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def fetch_all_jobs(companies: dict) -> tuple[list[Job], dict]:
    """
    Run all adapters and return (all_jobs, per_ats_stats).

    per_ats_stats maps ats_name → {"jobs": int, "companies": int}
    """
    all_jobs: list[Job] = []
    stats: dict[str, dict] = {}

    for ats_name, company_list in companies.items():
        adapter = ADAPTER_MAP.get(ats_name)
        if adapter is None:
            logger.warning("No adapter found for ATS '%s' — skipping", ats_name)
            continue

        ats_jobs: list[Job] = []

        for company_config in company_list:
            logger.info(
                "Fetching %s / %s ...",
                ats_name,
                company_config.get("company", company_config.get("tenant")),
            )
            try:
                jobs = adapter.fetch_jobs(company_config)
                ats_jobs.extend(jobs)
            except Exception as exc:
                # Catch-all so one broken company never kills the whole run
                logger.warning(
                    "Unhandled error for %s [%s]: %s",
                    ats_name,
                    company_config.get("tenant", "?"),
                    exc,
                )

        all_jobs.extend(ats_jobs)
        stats[ats_name] = {
            "jobs": len(ats_jobs),
            "companies": len(company_list),
        }

    return all_jobs, stats


def backfill_workday_descriptions(jobs: list[Job]) -> None:
    """
    For Workday jobs that passed the Argentina filter, fetch full descriptions
    from the detail endpoint and populate Job.description in place.
    Only backfills jobs that currently have an empty description.
    """
    targets = [j for j in jobs if j.source.startswith("workday:") and not j.description]
    if not targets:
        return

    logger.info("Backfilling descriptions for %d Workday jobs...", len(targets))

    for job in targets:
        # Parse tenant/wd/site from apply_url: https://{tenant}.{wd}.myworkdayjobs.com/en-US/{site}/job/...
        # We need external_path, which is stored in raw["externalPath"]
        external_path = job.raw.get("externalPath", "")
        if not external_path:
            continue

        # Parse tenant+wd+site from source ("workday:accenture") + apply_url
        # apply_url = https://accenture.wd103.myworkdayjobs.com/en-US/AccentureCareers/job/...
        apply_url = job.apply_url
        try:
            host = apply_url.split("/")[2]           # accenture.wd103.myworkdayjobs.com
            parts = host.split(".")                   # ['accenture', 'wd103', 'myworkdayjobs', 'com']
            tenant = parts[0]
            wd = parts[1]
            path_parts = apply_url.split("/en-US/")  # split on the locale segment
            site = path_parts[1].split("/")[0]        # 'AccentureCareers'
        except (IndexError, AttributeError):
            logger.warning("Could not parse tenant/wd/site from apply_url: %s", apply_url)
            continue

        detail = fetch_job_detail(tenant, wd, site, external_path)
        desc_html = detail.get("jobDescription") or ""
        if desc_html:
            job.description = _workday_strip_html(desc_html)
            logger.info("  ✓ %s @ %s", job.title, job.company)
        else:
            logger.warning("  ✗ No description for %s @ %s", job.title, job.company)

        time.sleep(0.5)


def write_output(jobs: list[Job], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([job.to_dict() for job in jobs], f, ensure_ascii=False, indent=2)


def print_summary(
    all_jobs: list[Job],
    argentina_jobs: list[Job],
    stats: dict,
) -> None:
    import random

    total = len(all_jobs)
    total_companies = sum(s["companies"] for s in stats.values())
    total_ats = len(stats)

    # ATS display names (label + annotation)
    ATS_LABELS = {
        "greenhouse": "Greenhouse",
        "lever": "Lever",
        "loreal": "L'Oréal (HTML)",
        "pepsico": "PepsiCo (custom)",
        "smartrecruiters": "SmartRecruiters",
        "workday": "Workday",
        "globant": "Globant (custom SAP)",
        "mercadolibre": "Mercado Libre (custom)",
    }

    print("\n" + "=" * 48)
    print("  Aplicar POC — Argentina-relevant jobs")
    print("=" * 48)

    print(f"\nFetched {total:,} jobs across {total_companies} companies in {total_ats} ATS platforms")

    # Dynamic column width for ATS labels
    label_width = max(len(ATS_LABELS.get(k, k)) for k in stats)
    for ats_name, s in stats.items():
        label = ATS_LABELS.get(ats_name, ats_name.capitalize())
        # Skip Meli line if stubbed (0 jobs)
        if ats_name in ("mercadolibre", "loreal") and s["jobs"] == 0:
            continue
        companies_str = f"({s['companies']} {'company' if s['companies'] == 1 else 'companies'})"
        print(f"  {label:<{label_width}}  {s['jobs']:>5} jobs  {companies_str}")

    print(f"\nArgentina-relevant: {len(argentina_jobs)} jobs")

    # Count argentina jobs per company
    company_counts: dict[str, int] = defaultdict(int)
    for job in argentina_jobs:
        company_counts[job.company] += 1

    if company_counts:
        sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
        col_width = max(len(c) for c, _ in sorted_companies)
        print("\nTop companies by Argentine openings:")
        for company, count in sorted_companies:
            print(f"  {company:<{col_width}}  {count:>4}")

    if argentina_jobs:
        sample = random.sample(argentina_jobs, min(5, len(argentina_jobs)))
        print("\nSample roles (random 5 from filtered set):")
        for job in sample:
            loc = job.location or "—"
            print(f"  - {job.title} @ {job.company} ({loc})")

    print(f"\nOutput written to {OUTPUT_FILE}")
    print("=" * 48)


def main() -> None:
    print("Loading companies.yaml ...")
    companies = load_companies()

    print(f"Starting fetch across {sum(len(v) for v in companies.values())} companies ...\n")
    all_jobs, stats = fetch_all_jobs(companies)

    print("\nFiltering for Argentina-relevant jobs ...")
    argentina_jobs = filter_argentina_jobs(all_jobs)

    print(f"Backfilling Workday descriptions for {sum(1 for j in argentina_jobs if j.source.startswith('workday:'))} matched Workday jobs ...")
    backfill_workday_descriptions(argentina_jobs)

    print(f"Writing {len(argentina_jobs)} Argentina-relevant jobs to {OUTPUT_FILE} ...")
    write_output(argentina_jobs, OUTPUT_FILE)

    print_summary(all_jobs, argentina_jobs, stats)


if __name__ == "__main__":
    main()
