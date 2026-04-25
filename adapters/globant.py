"""
Globant Custom Adapter (SAP SuccessFactors backend)
====================================================
Endpoint:  POST https://career.globant.com/api/sap/job-requisition-v1
Auth:      None — public API, but requires browser-like headers
Docs:      No official docs; discovered via browser DevTools on career.globant.com

⚠️  TYPO NOTE: The `deparment` parameter is intentionally misspelled in Globant's API.
    Sending the correctly-spelled "department" will silently ignore the filter.
    Do NOT fix this typo.

Page size is 10 (Globant's native default; no limit parameter is accepted).
Pagination: increment `page` by 1 starting from 1 until `jobRequisition` is empty.
Safety cap: stop after 30 pages to prevent infinite loops.

Apply URL pattern: https://career.globant.com/?jobReqId={jobReqId}
(confirmed via browser; the /job/{id} and /jobs/{id} patterns both return 404)
"""

import logging
import re
import time

import requests

from models import Job

logger = logging.getLogger(__name__)

API_URL = "https://career.globant.com/api/sap/job-requisition-v1"
MAX_PAGES = 30

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "Referer": "https://career.globant.com/",
    "Origin": "https://career.globant.com",
}


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def fetch_jobs(company_config: dict) -> list[Job]:
    """
    Fetch all open jobs from career.globant.com for the given country filter.

    company_config keys:
        company (str)        — human-readable company name
        country (list[str])  — country codes to filter, e.g. ["AR"]. Defaults to ["AR"].
    """
    company = company_config.get("company", "Globant")
    country = company_config.get("country", ["AR"])

    all_jobs: list[Job] = []

    for page in range(1, MAX_PAGES + 1):
        body = {
            "page": page,
            "q": "",
            "country": country,
            "deparment": "",  # intentional misspelling — Globant's API requires it
        }

        try:
            response = requests.post(API_URL, json=body, headers=HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Globant: request failed on page %d — %s", page, exc)
            break

        data = response.json()

        # Check for API-level errors
        if data.get("error") is not None:
            logger.warning("Globant: API returned error on page %d: %s", page, data["error"])
            break

        raw_jobs = data.get("jobRequisition", [])
        if not raw_jobs:
            break  # empty page = we've exhausted all results

        for raw in raw_jobs:
            job_req_id = raw.get("jobReqId", "")
            apply_url = f"https://career.globant.com/?jobReqId={job_req_id}" if job_req_id else ""

            description_html = raw.get("jobDescription") or ""
            description = _strip_html(description_html)

            area_list = raw.get("area") or []
            department = area_list[0].get("label", "") if area_list else ""

            job = Job(
                source="globant:career",
                company=company,
                title=raw.get("jobTitle", ""),
                location=raw.get("location", ""),
                description=description,
                apply_url=apply_url,
                posted_at=raw.get("createdDateTime"),
                raw=raw,
            )
            # Store department in raw so it's preserved in jobs.json
            job.raw["_department"] = department
            all_jobs.append(job)

        logger.info("Globant: page %d — %d jobs so far", page, len(all_jobs))
        time.sleep(0.5)

    logger.info("Globant: fetched %d total jobs (country=%s)", len(all_jobs), country)
    return all_jobs
