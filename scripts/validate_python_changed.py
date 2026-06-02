"""Valida arquivos Python alterados antes de commit.

Executa `py_compile` e `flake8` nos arquivos Python modificados/rastreados
pelo Git. Use sem argumentos para validar o diff atual ou informe caminhos
explicitamente.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _changed_python_files() -> list[str]:
    result = _run(["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"])
    paths = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip().endswith(".py")
    ]
    return [path for path in paths if (REPO / path).exists()]


def main() -> int:
    paths = sys.argv[1:] or _changed_python_files()
    if not paths:
        print("Nenhum arquivo Python alterado para validar.")
        return 0

    print("Validando Python:")
    for path in paths:
        print(f" - {path}")

    compile_cmd = [sys.executable, "-m", "py_compile", *paths]
    flake8_cmd = [sys.executable, "-m", "flake8", *paths]

    exit_code = 0
    for cmd in (compile_cmd, flake8_cmd):
        result = _run(cmd)
        if result.stdout:
            print(result.stdout, end="")
        if result.returncode:
            exit_code = result.returncode

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
