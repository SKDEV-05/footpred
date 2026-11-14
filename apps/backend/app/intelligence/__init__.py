"""Offline football intelligence and mathematical research primitives.

This package performs no I/O. It does not read the application database, call a provider,
persist predictions, or claim that its synthetic tests validate real football performance.
"""

from __future__ import annotations

from app.intelligence.engine import IntelligenceEngine

__all__ = ["IntelligenceEngine"]
