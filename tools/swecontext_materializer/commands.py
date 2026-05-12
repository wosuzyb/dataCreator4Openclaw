from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


class CommandError(RuntimeError):
    def __init__(self, result: CommandResult):
        super().__init__(f"command failed with exit {result.returncode}: {' '.join(result.args)}")
        self.result = result


def run_command(args: list[str], cwd: Path | None, dry_run: bool = False) -> CommandResult:
    if dry_run:
        return CommandResult(args=args, returncode=0, stdout="", stderr="")
    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result = CommandResult(
        args=args,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if result.returncode != 0:
        raise CommandError(result)
    return result
