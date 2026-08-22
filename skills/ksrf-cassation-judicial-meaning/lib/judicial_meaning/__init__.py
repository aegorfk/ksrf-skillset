"""Portable primitives for researching the judicial meaning of a legal norm.

The package intentionally has no project, database, network-service, or third-party
dependencies.  Higher-level commands may compose these primitives, but the legal
research gates remain available to an independently installed skill.
"""

from .analysis import (
    ALLOWED_CONCLUSIONS,
    analyze_reviewed_chains,
    screen_text,
    validate_coding_record,
    validate_thesis_readiness,
)
from .intake import intake_document, public_intake_record
from .plan import freeze_plan, make_research_question, validate_plan

__all__ = [
    "ALLOWED_CONCLUSIONS",
    "analyze_reviewed_chains",
    "freeze_plan",
    "intake_document",
    "make_research_question",
    "public_intake_record",
    "screen_text",
    "validate_coding_record",
    "validate_plan",
    "validate_thesis_readiness",
]

__version__ = "0.1.0"
