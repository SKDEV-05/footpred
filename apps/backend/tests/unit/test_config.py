"""Configuration invariants, without reading a developer's .env file."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(("default", "maximum"), [(300, 100), (25, 10)])
def test_default_page_size_cannot_exceed_maximum(default, maximum):
    with pytest.raises(
        ValidationError, match="API_PAGE_SIZE_DEFAULT must not exceed API_PAGE_SIZE_MAX"
    ):
        Settings(
            _env_file=None,
            api_page_size_default=default,
            api_page_size_max=maximum,
        )


def test_implicit_default_page_size_is_checked_against_maximum(monkeypatch):
    monkeypatch.delenv("API_PAGE_SIZE_DEFAULT", raising=False)
    with pytest.raises(
        ValidationError, match="API_PAGE_SIZE_DEFAULT must not exceed API_PAGE_SIZE_MAX"
    ):
        Settings(_env_file=None, api_page_size_max=10)


def test_default_page_size_may_equal_maximum():
    settings = Settings(
        _env_file=None, api_page_size_default=10, api_page_size_max=10
    )
    assert settings.api_page_size_default == settings.api_page_size_max == 10
