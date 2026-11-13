"""Read repositories.

Reads only: no provider calls, no writes, no session leakage to the API layer.
"""

from app.repositories.base import Page, count_of, fetch_page
from app.repositories.fixtures import (
    get_match,
    list_fixtures,
    statistics_for_match,
    team_matches,
)
from app.repositories.reference import (
    get_competition,
    get_season,
    get_team,
    list_competitions,
    list_seasons,
    list_teams,
    match_count_for_team,
    season_count,
)
from app.repositories.sync import (
    count_stale_running,
    last_finished_run,
    last_run_any_status,
    last_success_per_job_type,
    list_runs,
)

__all__ = [
    "Page",
    "count_of",
    "count_stale_running",
    "fetch_page",
    "get_competition",
    "get_match",
    "get_season",
    "get_team",
    "last_finished_run",
    "last_run_any_status",
    "last_success_per_job_type",
    "list_competitions",
    "list_fixtures",
    "list_runs",
    "list_seasons",
    "list_teams",
    "match_count_for_team",
    "season_count",
    "statistics_for_match",
    "team_matches",
]
