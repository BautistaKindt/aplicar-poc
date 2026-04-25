"""
Lever ATS Adapter
==================
Endpoint:  GET https://api.lever.co/v0/postings/{tenant}?mode=json
Auth:      None — fully public
Docs:      https://hire.lever.co/developer/postings

Returns a flat JSON array of all open postings — no pagination needed,
Lever returns everything in a single response.

Each posting has a nested `categories` object with `location`, `team`, etc.
The `hostedUrl` field is the canonical apply link.
"""

import logging
import time

import requests

from models import Job

logger = logging.getLogger(__name__)

BASE_URL = "https://api.lever.co/v0/postings/{tenant}?mode=json"


def fetch_jobs(company_config: dict) -> list[Job]:
    """
    Fetch all open postings for a Lever tenant and return normalized Job objects.

    company_config keys:
        tenant  (str) — Lever board tenant slug, e.g. "despegar"
        company (str) — human-readable company name
    """
    tenant = company_config["tenant"]
    company = company_config["company"]
    url = BASE_URL.format(tenant=tenant)

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Lever [%s]: request failed — %s", tenant, exc)
        return []

    raw_jobs = response.json()
    if not isinstance(raw_jobs, list):
        logger.warning("Lever [%s]: unexpected response shape — %s", tenant, type(raw_jobs))
        return []

    jobs = []
    for raw in raw_jobs:
        categories = raw.get("categories") or {}
        location = categories.get("location") or ""

        # descriptionPlain is pre-stripped; fall back to description (HTML) if absent
        description = raw.get("descriptionPlain") or raw.get("description") or ""

        job = Job(
            source=f"lever:{tenant}",
            company=company,
            title=raw.get("text", ""),
            location=location,
            description=description,
            apply_url=raw.get("hostedUrl") or raw.get("applyUrl") or "",
            posted_at=str(raw["createdAt"]) if raw.get("createdAt") else None,
            raw=raw,
        )
        jobs.append(job)

    time.sleep(0.5)
    logger.info("Lever [%s]: fetched %d jobs", tenant, len(jobs))
    return jobs
