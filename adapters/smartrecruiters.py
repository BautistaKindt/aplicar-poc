"""
SmartRecruiters ATS Adapter
============================
Endpoint:  GET https://api.smartrecruiters.com/v1/companies/{tenant}/postings?limit=100
Auth:      None — this is a public API
Docs:      https://developers.smartrecruiters.com/reference/jobad-postings-1

SmartRecruiters paginates using offset + limit. We walk pages until
the returned list is shorter than the requested limit (i.e. last page).
Note: the tenant name must match exactly — e.g. "Globant2" (capital G, trailing 2).
"""

import logging
import time

import requests

from models import Job

logger = logging.getLogger(__name__)

BASE_URL = "https://api.smartrecruiters.com/v1/companies/{tenant}/postings"
PAGE_SIZE = 100


def fetch_jobs(company_config: dict) -> list[Job]:
    """
    Fetch all open jobs for a SmartRecruiters tenant and return normalized Job objects.

    company_config keys:
        tenant  (str) — SmartRecruiters company identifier (case-sensitive)
        company (str) — human-readable company name
    """
    tenant = company_config["tenant"]
    company = company_config["company"]
    url = BASE_URL.format(tenant=tenant)

    all_jobs: list[Job] = []
    offset = 0

    while True:
        params = {"limit": PAGE_SIZE, "offset": offset}

        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("SmartRecruiters [%s]: request failed — %s", tenant, exc)
            break

        data = response.json()
        raw_postings = data.get("content", [])

        for raw in raw_postings:
            # Location can be a dict or absent
            location_obj = raw.get("location") or {}
            city = location_obj.get("city") or ""
            country = location_obj.get("country") or ""
            region = location_obj.get("region") or ""
            # Build a human-readable location string
            parts = [p for p in [city, region, country] if p]
            location = ", ".join(parts)

            # SmartRecruiters provides a "ref" URL we can use as the apply link
            apply_url = raw.get("ref") or ""

            job = Job(
                source=f"smartrecruiters:{tenant}",
                company=company,
                title=raw.get("name", ""),
                location=location,
                description=raw.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", ""),
                apply_url=apply_url,
                posted_at=raw.get("releasedDate"),
                raw=raw,
            )
            all_jobs.append(job)

        # If we got fewer results than the page size, we've reached the last page
        if len(raw_postings) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        time.sleep(0.5)  # polite delay between paginated requests

    time.sleep(0.5)
    logger.info("SmartRecruiters [%s]: fetched %d jobs", tenant, len(all_jobs))
    return all_jobs
