
#!/usr/bin/env python3

import os
import zipfile
from pathlib import Path

# Pasta principal do projeto
ROOT = Path(__file__).resolve().parent

# O ZIP será criado fora da pasta do projeto
OUTPUT = ROOT.parent / "BarberPro_atualizacao.zip"

# Pastas que não precisam ser enviadas
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "venv312",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "htmlcov",
    "coverage",
    ".next",
    "dist",
    ".agents",
    ".claude",
    ".vscode",
    ".idea",
}

# Arquivos gerados ou bancos locais
EXCLUDED_FILES = {
    ".DS_Store",
    ".coverage",
    "db.sqlite3",
    "test.db",
}

def should_skip_file(path):
    name = path.name

    # Não incluir arquivos de ambiente com segredos.
    # Mantém o .env.example.
    if name == ".env":
        return True

    if name.startswith(".env.") and name != ".env.example":
        return True

    if name in EXCLUDED_FILES:
        return True

    if path.suffix.lower() in {
        ".pyc",
        ".pyo",
        ".sqlite3",
        ".db",
        ".log",
    }:
        return True

    return False


def main():
    total_files = 0

    print("Gerando ZIP do BarberPro...")

    with zipfile.ZipFile(
        OUTPUT,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:

        for current, dirs, files in os.walk(ROOT):

            # Remove pastas desnecessárias da varredura
            dirs[:] = sorted(
                directory
                for directory in dirs
                if directory not in EXCLUDED_DIRS
            )

            for filename in sorted(files):
                file_path = Path(current) / filename

                if should_skip_file(file_path):
                    continue

                if file_path.resolve() == OUTPUT.resolve():
                    continue

                relative_path = (
                    Path(ROOT.name) / file_path.relative_to(ROOT)
                )

                archive.write(
                    file_path,
                    relative_path.as_posix()
                )

                total_files += 1

        # Verifica a integridade do arquivo
        corrupted_file = archive.testzip()

        if corrupted_file:
            raise RuntimeError(
                f"Erro no ZIP: {corrupted_file}"
            )

    size_mb = OUTPUT.stat().st_size / (1024 * 1024)

    print("\nZIP criado com sucesso!")
    print(f"Arquivo: {OUTPUT}")
    print(f"Arquivos incluídos: {total_files}")
    print(f"Tamanho: {size_mb:.2f} MB")
    print("\nAgora envie BarberPro_atualizacao.zip no ChatGPT.")


if __name__ == "__main__":
    main()
