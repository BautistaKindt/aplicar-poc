"""
Shared data model for normalized job listings across all ATS platforms.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Job:
    # Unique source identifier: "ats_name:company_tenant"
    source: str
    company: str
    title: str
    location: str
    description: str
    apply_url: str
    posted_at: Optional[str]  # ISO 8601 string or None if not provided
    raw: dict = field(default_factory=dict)  # Original ATS response preserved verbatim

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "company": self.company,
            "title": self.title,
            "location": self.location,
            "description": self.description,
            "apply_url": self.apply_url,
            "posted_at": self.posted_at,
            "raw": self.raw,
        }
