"""Deterministic, conservative allocation and evidence-planning utilities."""

from .allocation_bounds import classify_shipments
from .evidence_planner import rank_actions

__all__ = ["classify_shipments", "rank_actions"]
