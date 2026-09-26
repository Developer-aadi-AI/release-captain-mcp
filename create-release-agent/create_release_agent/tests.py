from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Sequence


@dataclass(frozen=True)
class ValidationResult:
    command: Sequence[str]
    returncode: int
    stdout: str
    stderr: str


def discover_validation_command(repo_path: str | Path) -> list[str]:
    root = Path(repo_path)
    if (root / "pytest.ini").exists() or (root / "tox.ini").exists() or (root / "setup.py").exists():
        return ["pytest"]
    if (root / "pyproject.toml").exists():
        return ["pytest"]
    if (root / "package.json").exists():
        return ["npm", "test", "--", "--runInBand"]
    if (root / "Cargo.toml").exists():
        return ["cargo", "test"]
    if (root / "go.mod").exists():
        return ["go", "test", "./..."]
    return ["pytest"]


def run_validation(repo_path: str | Path) -> ValidationResult:
    cmd = discover_validation_command(repo_path)
    proc = subprocess.run(
        cmd,
        cwd=str(repo_path),
        capture_output=True,
        text=True,
    )
    return ValidationResult(cmd, proc.returncode, proc.stdout, proc.stderr)
