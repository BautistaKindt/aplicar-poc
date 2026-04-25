"""
Greenhouse ATS Adapter
======================
Endpoint:  GET https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs?content=true
Auth:      None — this is a public API
Docs:      https://developers.greenhouse.io/job-board/v1/#retrieve-all-jobs

The ?content=true parameter includes the full job description HTML in each job.
Greenhouse paginates by returning ALL jobs in one shot (no cursor/offset needed).
"""

import logging
import time

import requests

from models import Job

logger = logging.getLogger(__name__)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs"


def fetch_jobs(company_config: dict) -> list[Job]:
    """
    Fetch all open jobs for a single Greenhouse tenant and return normalized Job objects.

    company_config keys:
        tenant  (str) — the Greenhouse board tenant slug, e.g. "stripe"
        company (str) — human-readable company name
    """
    tenant = company_config["tenant"]
    company = company_config["company"]
    url = BASE_URL.format(tenant=tenant)

    try:
        response = requests.get(url, params={"content": "true"}, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Greenhouse [%s]: request failed — %s", tenant, exc)
        return []

    data = response.json()
    raw_jobs = data.get("jobs", [])

    jobs = []
    for raw in raw_jobs:
        # Greenhouse location is a nested object; fall back gracefully
        location_obj = raw.get("location") or {}
        location = location_obj.get("name") or ""

        # Content block holds the full description HTML
        content = raw.get("content") or ""

        job = Job(
            source=f"greenhouse:{tenant}",
            company=company,
            title=raw.get("title", ""),
            location=location,
            description=content,
            apply_url=raw.get("absolute_url", ""),
            posted_at=raw.get("updated_at"),
            raw=raw,
        )
        jobs.append(job)

    time.sleep(0.5)  # be polite between companies
    logger.info("Greenhouse [%s]: fetched %d jobs", tenant, len(jobs))
    return jobs
