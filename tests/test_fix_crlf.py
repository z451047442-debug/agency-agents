"""Tests for scripts/fix-crlf.py — CRLF → LF batch converter."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
FIX_SCRIPT = SCRIPTS_DIR / "fix-crlf.py"


def _run_fix(cwd: Path) -> subprocess.CompletedProcess:
    """Run fix-crlf.py patched to use *cwd* as ROOT instead of the real repo."""
    script = FIX_SCRIPT.read_text(encoding="utf-8")
    script = script.replace(
        "ROOT = pathlib.Path(__file__).resolve().parent.parent",
        f"ROOT = pathlib.Path(r'{cwd}')",
    )
    temp_script = cwd / "_fix_crlf.py"
    temp_script.write_text(script, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(temp_script)],
        capture_output=True, text=True, timeout=30,
    )


def _make_category(tmp_path: Path, name: str) -> Path:
    d = tmp_path / name
    d.mkdir()
    return d


class TestFixCrlf:
    def test_converts_crlf_to_lf(self, tmp_path):
        """Files with CRLF are converted to LF."""
        d = _make_category(tmp_path, "testing")
        f = d / "testing-agent.md"
        f.write_bytes(b"---\r\nname: Test\r\n---\r\n\r\n## Identity\r\nHello.\r\n")
        result = _run_fix(tmp_path)
        assert "CONVERTED: 1 files" in result.stdout
        assert b"\r\n" not in f.read_bytes()

    def test_skips_lf_only(self, tmp_path):
        """Files already in LF are skipped."""
        d = _make_category(tmp_path, "testing")
        d / "testing-agent.md"
        f = d / "testing-agent.md"
        f.write_bytes(b"---\nname: Test\n---\n\n## Identity\nHello.\n")
        result = _run_fix(tmp_path)
        assert "CONVERTED: 0 files" in result.stdout

    def test_skips_excluded_dirs(self, tmp_path):
        """Files in excluded directories (docs, tests, etc.) are not touched."""
        excluded = tmp_path / "docs"
        excluded.mkdir()
        f = excluded / "readme.md"
        f.write_bytes(b"---\r\nname: Excluded\r\n---\r\n")
        result = _run_fix(tmp_path)
        assert "CONVERTED: 0 files" in result.stdout
        assert b"\r\n" in f.read_bytes()

    def test_handles_no_md_files(self, tmp_path):
        """No errors when no .md files exist."""
        _make_category(tmp_path, "empty-cat")
        result = _run_fix(tmp_path)
        assert result.returncode == 0
        assert "CONVERTED: 0 files" in result.stdout
