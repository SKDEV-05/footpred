"""Normalisation: names, enums, labels, and metric keys.

This package converts provider-shaped values into canonical values. It performs no I/O
and never invents a value: a value it cannot normalise raises.
"""

from app.normalization.names import clean_display_name, normalize_code, normalize_name
from app.normalization.status import (
    UnknownProviderValueError,
    competition_type,
    group_name,
    match_duration,
    match_status,
    match_winner,
    season_label,
    snake_case,
    stage_name,
)

__all__ = [
    "UnknownProviderValueError",
    "clean_display_name",
    "competition_type",
    "group_name",
    "match_duration",
    "match_status",
    "match_winner",
    "normalize_code",
    "normalize_name",
    "season_label",
    "snake_case",
    "stage_name",
]
