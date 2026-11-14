"""Static boundary checks for the offline Phase 4 package."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "app" / "intelligence"

FORBIDDEN_MODULES = {
    "app.api",
    "app.cli",
    "app.database",
    "app.ingestion",
    "app.main",
    "app.providers",
    "app.repositories",
    "app.schemas",
    "app.sync",
    "app.worker",
    "fastapi",
    "httpx",
    "sqlalchemy",
    "alembic",
    "apscheduler",
    "requests",
    "socket",
    "subprocess",
}

FORBIDDEN_CALLS = {
    "open",
    "input",
    "print",
    "exec",
    "eval",
}


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _source_files() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def test_package_has_no_forbidden_imports() -> None:
    offenders: list[str] = []
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for module in _imported_names(tree):
            root = ".".join(module.split(".")[:2])
            if module in FORBIDDEN_MODULES or root in FORBIDDEN_MODULES:
                offenders.append(f"{path.relative_to(PACKAGE)}: {module}")
    assert offenders == []


def test_package_performs_no_io_or_dynamic_execution() -> None:
    offenders: list[str] = []
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    offenders.append(f"{path.relative_to(PACKAGE)}: {node.func.id}")
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                offenders.append(f"{path.relative_to(PACKAGE)}: {type(node).__name__}")
    assert offenders == []


def test_package_does_not_read_ambient_time_or_randomness() -> None:
    offenders: list[str] = []
    for path in _source_files():
        source = path.read_text(encoding="utf-8")
        for token in ("datetime.now(", "datetime.utcnow(", "time.time(", "random.", "os.environ"):
            if token in source:
                offenders.append(f"{path.relative_to(PACKAGE)}: {token}")
    assert offenders == []


def test_every_module_declares_future_annotations() -> None:
    missing = [
        str(path.relative_to(PACKAGE))
        for path in _source_files()
        if "from __future__ import annotations" not in path.read_text(encoding="utf-8")
    ]
    assert missing == []
