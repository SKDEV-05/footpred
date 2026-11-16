# Migrations Guide

**Scope:** creating and applying schema migrations for the SQLite database.
**Verified:** 2026-11-15. `upgrade head` built all 17 tables and revision `0004`;
`alembic check` reported no drift; the full test suite passes; an integration test runs the
migration against a temporary database.
**Decisions:** `ADR-0003` (SQLite), `docs/architecture/database-design.md`.

## 1. How the environment is wired

- `alembic.ini` at the repository root defines the script location.
- `apps/backend/migrations/env.py` reads the URL from application settings, not from
  `alembic.ini`, so the migration and the application cannot target different databases.
- `render_as_batch=True` is set because SQLite cannot `ALTER TABLE` in place for every change.
- All model modules must be imported before autogenerate. `app.models` is imported in `env.py`
  for this reason; adding a model file requires adding it to `app/models/__init__.py`.

## 2. Apply migrations

Preferred, uses the same settings as the application:

```bash
PYTHONPATH=apps/backend .venv/bin/python -m app.cli migrate
```

Equivalent Alembic commands (run from the repository root):

```bash
PYTHONPATH=apps/backend .venv/bin/alembic upgrade head
PYTHONPATH=apps/backend .venv/bin/alembic current
PYTHONPATH=apps/backend .venv/bin/alembic check
```

`alembic check` compares the live schema with the models and exits non-zero on drift. It is the
gate that prevents a model change from shipping without a revision.

## 3. Create a revision

1. Change the model.
2. Generate the revision:

   ```bash
   PYTHONPATH=apps/backend .venv/bin/alembic revision --autogenerate -m "describe the change"
   ```

3. Read the generated file. Autogenerate is a draft, not an authority. Check:
   - the `UTCDateTime` import is present when the revision uses that type;
   - `down_revision` points at the current head;
   - constraints have explicit, stable names;
   - the upgrade is safe for existing rows (new non-null columns need a default or a backfill).
4. Run `upgrade head` on a copy, then the test suite.
5. Run `alembic check` and confirm no drift.

## 4. Safety rules

| Rule | Reason |
| --- | --- |
| Never edit an applied revision | The database records the revision id; editing it makes environments diverge |
| Never run `downgrade` on real data without a verified backup | The initial revision's downgrade drops every table and its data |
| Back up the database file and `RAW_STORAGE_DIR` before a destructive change | The archive is cited evidence |
| Stop and request approval for a destructive migration | Required by `AGENTS.md` §4 and §14 |
| Test against a scratch database, not the development database | A failed migration on the only copy is unrecoverable |
| Keep SQL portable where practical | PostgreSQL is a future option; it is not verified now |

SQLite limitations that affect migrations:

- Dropping or altering a column requires table rebuild; batch mode handles the common cases but
  cannot preserve everything. Test on a copy with representative data.
- Adding a `UNIQUE` constraint creates an index; existing duplicates make it fail.
- `PRAGMA foreign_keys` cannot be changed inside a transaction. Review generated migrations
  before running them.

## 5. Verify a migration locally

```bash
scratch_dir=$(mktemp -d /tmp/opencode/migration-check.XXXXXX)
export DATABASE_URL="sqlite+pysqlite:///$scratch_dir/app.db"
export RAW_STORAGE_DIR="$scratch_dir/raw"
PYTHONPATH=apps/backend .venv/bin/python -m app.cli migrate
PYTHONPATH=apps/backend .venv/bin/alembic check
```

This creates a fresh directory without deleting an earlier check. Retain it until inspected.
The migration test in `apps/backend/tests/integration/test_migrations.py` performs the same
check automatically: it builds the schema from revisions, asserts the exact table set, and
compares metadata for drift.

## 6. Backup and restore (manual, not automated)

There is no backup automation in Phase 3. Before a migration on a database that matters:

1. Stop the API and worker.
2. Copy the database file (`data/football.db`) and the `-wal`/`-shm` files, or use
   `sqlite3 data/football.db ".backup backup.db"`.
3. Copy `RAW_STORAGE_DIR`.
4. Apply the migration.
5. Start the application and check `/api/v1/health`.
6. Keep the backup until the new schema has served real traffic.

A restore rehearsal and retention policy are listed as prerequisites in
`docs/architecture/implementation-plan.md` §6.
