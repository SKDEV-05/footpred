# Testing Guide

**Scope:** the Phase 3 test suite and what it does and does not prove.
**Last executed:** 2026-11-14 session — **124 passed**, 1 warning.
**Command:** `PYTHONPATH=apps/backend .venv/bin/python -m pytest`

A passing suite is evidence about the code in this repository under synthetic inputs. It is
not evidence of live provider behaviour, production load, or PostgreSQL compatibility.

## 1. Layout

```text
apps/backend/tests/
  conftest.py                 isolated temporary SQLite database, raw archive, API client
  factories.py                synthetic DTOs and a fake adapter (labelled SYNTHETIC TEST DATA)
  fixtures/*.json             documented response shapes, synthetic values
  unit/                       pure functions and the HTTP client
  integration/                database, ingestion, sync, API, migrations, CLI
```

## 2. What each area covers

| Area | Representative checks |
| --- | --- |
| Normalisation | Accent-insensitive exact keys; display names preserved; unknown enum rejected |
| Configuration | Default page size cannot exceed maximum, including implicit defaults |
| Validation | Required fields, score consistency, date ordering, no invented values |
| HTTP client | Timeout, retry, backoff, `Retry-After`, token bucket, size cap, typed errors |
| Adapter | Documented response shapes; null vs zero; undocumented structure rejected |
| Identity | Mapping → natural key → create; ambiguity quarantined; one mapping per provider/entity |
| Ingestion | Idempotent upsert; change log; absent field does not erase; result only when final |
| Statistics | One row per metric; measured zero stored; missing metric has no row |
| Sync engine | Run lifecycle; partial run; quarantine; provider failure; stale-run sweep |
| API | Read-only routes; filters; pagination limits; UTC formatting; error envelope; honest nulls |
| Migrations | All 17 tables built; no metadata drift; repeat upgrade is a no-op |
| Database | Non-SQLite URL fails closed; foreign keys, WAL, busy timeout enabled |
| Raw archive | Bytes and metadata stored; content-addressed; sensitive params stripped |
| CLI / worker | `migrate`, `status`, `check-provider`; worker refuses invalid configuration |

## 3. Test isolation

- Each test gets a temporary file-backed SQLite database through the `database` fixture.
- Environment variables are set per test, `get_settings.cache_clear()` and `reset_engine()` are
  called, and all tables are created from the models for the ordinary suite.
- Migration tests run Alembic in-process against a separate temporary database.
- No current test contacts a provider. The `live` marker is registered, but registration alone
  does **not** skip tests. Future live tests must explicitly skip without opt-in credentials;
  run offline checks with `-m "not live"` once such tests exist.

## 4. Commands

```bash
# whole suite
PYTHONPATH=apps/backend .venv/bin/python -m pytest

# one file
PYTHONPATH=apps/backend .venv/bin/python -m pytest apps/backend/tests/integration/test_api.py

# one test, with output
PYTHONPATH=apps/backend .venv/bin/python -m pytest -k "statistics" -vv

# show captured log lines
PYTHONPATH=apps/backend .venv/bin/python -m pytest -k "sync" -o log_cli=true
```

`pyproject.toml` sets `pythonpath=apps/backend`, `testpaths=apps/backend/tests`, quiet output,
and treats deprecation warnings raised by `app.*` as errors.

## 5. What the suite does not cover

| Gap | Consequence |
| --- | --- |
| No live provider test | Adapter correctness is proven against documented shapes only |
| No PostgreSQL test | Portability is a design intention, not a verified property |
| No load or concurrency test | SQLite writer contention under concurrent clients is untested |
| No backup/restore test | Operational recovery is manual and unrehearsed |
| No browser or frontend test | There is no frontend |
| No security penetration test | No auth exists to test |
| No long-running worker test | Scheduler behaviour is inspected, not soak-tested |
| No historical coverage test | No provider data exists to measure coverage |
| Independent QA/security review blocked by usage limit | No independent sign-off; self-checks are not acceptance |

Do not describe the suite as "full coverage" or the system as "tested against the provider". It
is a correctness suite over the implemented boundaries with synthetic evidence.

## 6. Adding tests

- A bug fix needs a regression test that fails before the fix.
- A new rule needs a test for the accepted case and the rejected case.
- A new endpoint needs a contract test for success, validation error, and not-found.
- A new migration needs a test that the schema matches the models.
- Never assert a value that the code merely produces; assert the value the domain requires.
- Use synthetic data and label it. Never copy a real match, result, or statistic into a fixture
  without checking the provider's licence.
