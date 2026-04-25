"""
PepsiCo Custom Adapter (Jibe/iCIMS backend)
============================================
Endpoint:  GET https://www.pepsicojobs.com/api/jobs
Auth:      None — public JSON API
Docs:      No official docs; discovered via browser DevTools on pepsicojobs.com

Each job is nested under a "data" key: response["jobs"][i]["data"].
Apply URL is the `apply_url` field in the job data (links to iCIMS).
Location built from city + country fields; fallback to location_name.
Pagination: increment `page` from 1 until jobs array is empty (safety cap: 50 pages).
"""

import logging
import time

import requests

from models import Job

logger = logging.getLogger(__name__)

API_URL = "https://www.pepsicojobs.com/api/jobs"
MAX_PAGES = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def fetch_jobs(company_config: dict) -> list[Job]:
    """
    Fetch open jobs from pepsicojobs.com for the given country filter.

    company_config keys:
        company (str)  — human-readable company name
        country (str)  — country filter string, e.g. "Argentina"
    """
    company = company_config.get("company", "PepsiCo")
    country = company_config.get("country", "Argentina")

    all_jobs: list[Job] = []

    for page in range(1, MAX_PAGES + 1):
        params = {
            "page": page,
            "sortBy": "relevance",
            "descending": "false",
            "internal": "false",
            "country": country,
        }

        try:
            response = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("PepsiCo: request failed on page %d — %s", page, exc)
            break

        data = response.json()
        raw_jobs = data.get("jobs", [])
        if not raw_jobs:
            break

        for wrapper in raw_jobs:
            raw = wrapper.get("data") or wrapper

            city = raw.get("city") or ""
            country_name = raw.get("country") or ""
            location_name = raw.get("location_name") or ""
            if city and country_name:
                location = f"{city}, {country_name}"
            elif location_name:
                location = location_name
            else:
                location = country_name

            description = raw.get("description") or ""
            qualifications = raw.get("qualifications") or ""
            if qualifications:
                description = f"{description}\n{qualifications}".strip()

            apply_url = raw.get("apply_url") or ""

            job = Job(
                source="pepsico:careers",
                company=company,
                title=raw.get("title", ""),
                location=location,
                description=description,
                apply_url=apply_url,
                posted_at=raw.get("posted_date"),
                raw=raw,
            )
            all_jobs.append(job)

        logger.info("PepsiCo: page %d — %d jobs so far", page, len(all_jobs))
        time.sleep(0.5)

    logger.info("PepsiCo: fetched %d total jobs (country=%s)", len(all_jobs), country)
    return all_jobs
