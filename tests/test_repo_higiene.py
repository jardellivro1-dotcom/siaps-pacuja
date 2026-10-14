"""Higiene do repositório: sem segredos versionados e arquivos sensíveis ignorados."""

import re
import subprocess
import unittest

from helpers import config

RAIZ = config.ROOT
PADROES = {
    "chave privada": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "token GitHub": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "chave AWS": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "token Slack": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "senha/segredo atribuído": re.compile(
        r"(?i)\b(password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
    ),
}
EXTENSOES = {".py", ".js", ".html", ".css", ".md", ".yml", ".yaml", ".toml", ".txt", ".json", ".bat"}


def arquivos_versionados():
    try:
        saida = subprocess.run(  # noqa: S603 - comando fixo, sem entrada externa
            ["git", "ls-files"],  # noqa: S607 - git do PATH, comando fixo
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,  # noqa: S607
        ).stdout.splitlines()
        return [RAIZ / f for f in saida]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in RAIZ.rglob("*") if p.is_file() and ".git" not in p.parts]


class Higiene(unittest.TestCase):
    def test_sem_segredos_nos_arquivos_do_projeto(self):
        for arq in arquivos_versionados():
            if arq.suffix not in EXTENSOES or "vendor" in arq.parts or arq.name == "test_repo_higiene.py":
                continue
            texto = arq.read_text(encoding="utf-8", errors="ignore")
            for nome, padrao in PADROES.items():
                self.assertIsNone(padrao.search(texto), f"{nome} em {arq.relative_to(RAIZ)}")

    def test_gitignore_cobre_arquivos_sensiveis(self):
        ignorados = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
        for item in (".env", "logs/", "*.pem", "*.key"):
            self.assertIn(item, ignorados)

    def test_versao_do_app_consta_no_changelog_e_na_metodologia(self):
        changelog = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{config.VERSAO_APP}]", changelog)
        self.assertIn(config.METODOLOGIA["id"], (RAIZ / "docs" / "METODOLOGIA.md").read_text(encoding="utf-8"))

    def test_dependencias_de_runtime_continuam_zero(self):
        pyproject = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)


if __name__ == "__main__":
    unittest.main()
