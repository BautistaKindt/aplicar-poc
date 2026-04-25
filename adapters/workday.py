"""
Workday ATS Adapter
====================
Endpoint:  POST https://{tenant}.{wdN}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
Auth:      None — public careers endpoint (requires browser-like headers to avoid 403)
Docs:      No official public API docs; this is the undocumented but stable endpoint
           used by all Workday-hosted careers pages.

Workday uses offset-based pagination with a typical page size of 20.
We POST with increasing offsets until `jobPostings` is empty or offset >= total.

Required headers:
  - Accept: application/json
  - Content-Type: application/json
  - User-Agent: a browser User-Agent string (plain Python UA gets blocked)
  - Referer: the careers site URL (some tenants validate this)
"""

import logging
import re
import time

import requests

from models import Job

logger = logging.getLogger(__name__)

PAGE_SIZE = 20

# Headers that mimic a real browser request — Workday rejects missing/default UAs
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _build_url(tenant: str, wd: str, site: str) -> str:
    return f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"


def _build_referer(tenant: str, wd: str, site: str) -> str:
    return f"https://{tenant}.{wd}.myworkdayjobs.com/en-US/{site}"


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def fetch_job_detail(tenant: str, wd: str, site: str, external_path: str) -> dict:
    """
    Fetch the full detail for a single Workday job posting.

    external_path is the value from the list response (e.g. "/job/City/Title_REF").
    Returns the raw `jobPostingInfo` dict, or {} on failure.
    """
    # external_path already contains /job/..., so we append it directly to the CXS base
    url = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{external_path}"
    headers = {**HEADERS, "Referer": _build_referer(tenant, wd, site)}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json().get("jobPostingInfo", {})
    except requests.RequestException as exc:
        logger.warning("Workday detail fetch failed [%s%s]: %s", tenant, external_path, exc)
        return {}


def fetch_jobs(company_config: dict) -> list[Job]:
    """
    Fetch all open jobs for a Workday tenant and return normalized Job objects.

    company_config keys:
        tenant  (str) — Workday tenant slug, e.g. "accenture"
        wd      (str) — Workday instance identifier, e.g. "wd103"
        site    (str) — Careers site name, e.g. "AccentureCareers"
        company (str) — human-readable company name
    """
    tenant = company_config["tenant"]
    wd = company_config["wd"]
    site = company_config["site"]
    company = company_config["company"]

    url = _build_url(tenant, wd, site)
    headers = {**HEADERS, "Referer": _build_referer(tenant, wd, site)}

    all_jobs: list[Job] = []
    offset = 0
    total = None  # learned from first response

    while True:
        body = {
            "appliedFacets": {},
            "limit": PAGE_SIZE,
            "offset": offset,
            "searchText": "",
        }

        try:
            response = requests.post(url, json=body, headers=headers, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Workday [%s]: request failed at offset=%d — %s", tenant, offset, exc)
            break

        data = response.json()

        # The total count is returned in the first response; capture it once
        if total is None:
            total = data.get("total", 0)

        raw_postings = data.get("jobPostings", [])
        if not raw_postings:
            break

        for raw in raw_postings:
            # The list endpoint has no dedicated location field.
            # Workday packs job ID + location into bulletFields[0] and bulletFields[1].
            bullet_fields = raw.get("bulletFields") or []
            location_raw = bullet_fields[1] if len(bullet_fields) > 1 else ""

            # The detail page is at the tenant's careers domain + bulletFields/externalPath
            external_path = raw.get("externalPath", "")
            if external_path:
                apply_url = f"https://{tenant}.{wd}.myworkdayjobs.com/en-US/{site}{external_path}"
            else:
                apply_url = ""

            job = Job(
                source=f"workday:{tenant}",
                company=company,
                title=raw.get("title", ""),
                location=location_raw,
                # Workday job listings don't return full descriptions in the list endpoint
                description="",
                apply_url=apply_url,
                posted_at=raw.get("postedOn"),
                raw=raw,
            )
            all_jobs.append(job)

        offset += PAGE_SIZE

        # Stop if we've passed the total or didn't get a full page
        if total is not None and offset >= total:
            break
        if len(raw_postings) < PAGE_SIZE:
            break

        time.sleep(0.5)  # polite delay between paginated requests

    time.sleep(0.5)
    logger.info("Workday [%s]: fetched %d jobs (total reported: %s)", tenant, len(all_jobs), total)
    return all_jobs
