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


def test_production_rejects_enabled_api_docs():
    with pytest.raises(ValidationError, match="API_DOCS_ENABLED"):
        Settings(_env_file=None, app_env="production", api_docs_enabled=True)


def test_provider_base_url_must_be_https_and_allowlisted():
    with pytest.raises(ValidationError, match="FOOTBALL_DATA_ORG_BASE_URL"):
        Settings(_env_file=None, football_data_org_base_url="http://internal.test/v4")


def test_production_explicitly_disabling_docs_succeeds():
    settings = Settings(_env_file=None, app_env="production", api_docs_enabled=False)
    assert settings.app_env == "production"
    assert settings.api_docs_enabled is False


def test_development_defaults_keep_docs_enabled():
    settings = Settings(_env_file=None, app_env="development")
    assert settings.api_docs_enabled is True
