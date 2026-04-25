"""
Argentina-relevance filter for job listings.

Modify ARGENTINA_TERMS or REMOTE_TERMS to tune what gets included.
"""

from models import Job

# Location keywords that directly signal an Argentina-based or LATAM-remote role
ARGENTINA_TERMS = [
    "argentina",
    "buenos aires",
    "cordoba",
    "córdoba",
    "rosario",
    "mendoza",
    "remote - latam",
    "remote latam",
    "latin america",
    "latinoamérica",
    "latam",
]

# If a job mentions remote work AND one of these geographic terms, include it too
REMOTE_TERMS = ["remote", "trabajo remoto", "100% remote"]


def _contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def is_argentina_relevant(job: Job) -> bool:
    """
    Returns True if the job is relevant for candidates in Argentina.

    A job qualifies if:
    1. Its location field contains any Argentina/LATAM keyword, OR
    2. Its title or description mentions remote work AND an Argentina/LATAM keyword
    """
    # Check location first — most reliable signal
    if _contains_any(job.location, ARGENTINA_TERMS):
        return True

    # Fallback: remote role that explicitly mentions LATAM/Argentina in title or description
    combined_text = f"{job.title} {job.description}"
    if _contains_any(combined_text, REMOTE_TERMS) and _contains_any(
        combined_text, ARGENTINA_TERMS
    ):
        return True

    return False


def filter_argentina_jobs(jobs: list[Job]) -> list[Job]:
    return [job for job in jobs if is_argentina_relevant(job)]
