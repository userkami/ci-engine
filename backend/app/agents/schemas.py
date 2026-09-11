"""Pydantic schemas for the battlecard report.

Contract for the final deliverable produced by the synthesis node and
stored in the ``battlecards.report_data`` JSONB column (Phase 2).
Field names follow BUILD_GUIDE.md Phase 3 / SPEC.md §5 exactly.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class PricingTier(BaseModel):
    """A single competitor pricing plan tier."""

    name: str = Field(description="Name of the plan tier")
    price: str = Field(
        description="Normalized monthly cost or 'Contact Sales'"
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Excluded features or user-seat minimums",
    )
    source_url: str = Field(
        description="Direct URL to pricing or documentation"
    )


class ChurnDriver(BaseModel):
    """A verified reason customers churn, with a rebuttal talk track."""

    pain_point: str = Field(
        description="Core operational failure or reason for switching"
    )
    exact_quote: str = Field(
        description="Verbatim user complaint from G2/Capterra/Reddit"
    )
    source_platform: str = Field(description="e.g. G2, Capterra, Reddit")
    source_url: str = Field(description="Direct URL to the review")
    objection_rebuttal: str = Field(
        description="Actionable sales objection script"
    )


class SWOTAnalysis(BaseModel):
    """SWOT decomposition of the competitor's position."""

    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    threats: List[str] = Field(default_factory=list)


class BattlecardOutput(BaseModel):
    """The final structured battlecard delivered by the synthesis node."""

    executive_summary: str = Field(
        description="3-5 sentence battlecard summary for the sales team"
    )
    swot: SWOTAnalysis
    pricing: List[PricingTier] = Field(default_factory=list)
    churn_drivers: List[ChurnDriver] = Field(default_factory=list)
    landmine_questions: List[str] = Field(
        default_factory=list,
        description="Questions to trap the competitor on sales calls",
    )