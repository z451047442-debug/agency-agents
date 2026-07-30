import pytest
from pathlib import Path
from unittest.mock import patch
import importlib.util, sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
spec = importlib.util.spec_from_file_location(
    "batch_add_hardening_v2", str(SCRIPTS_DIR / "batch-add-hardening-v2.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestBatchAddHardeningV2:
    def test_repo_root(self):
        assert mod.ROOT.is_dir()

    def test_needs_hardening_true(self):
        body = "## Testing\nI specialize in testing, qa, code review, security audit, and vulnerability assessment."
        assert mod.needs_hardening(body) is True

    def test_needs_hardening_false(self):
        body = "## Discovery\nI do market research and user interviews."
        assert mod.needs_hardening(body) is False

    def test_add_hardening_role_inserts_after_date_added(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Tester\ndate_added: '2026-07-01'\n---\nBody",
            encoding="utf-8",
        )
        mod.add_hardening_role(f)
        content = f.read_text(encoding="utf-8")
        assert "phase-4-hardening" in content

    def test_add_hardening_role_idempotent(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Tester\ndate_added: '2026-07-01'\nnexus_roles:\n  - phase-4-hardening\n---\nBody",
            encoding="utf-8",
        )
        mod.add_hardening_role(f)
        content = f.read_text(encoding="utf-8")
        assert content.count("phase-4-hardening") == 1

    def test_dry_run_no_write(self, tmp_path, monkeypatch):
        d = tmp_path / "testing"
        d.mkdir()
        f = d / "testing-sdet.md"
        f.write_text(
            "---\nname: SDET\ndate_added: '2026-07-01'\n---\nI do testing and qa.",
            encoding="utf-8",
        )
        import _shared.discovery as discovery_mod
        monkeypatch.setattr(discovery_mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "ROOT", tmp_path)
        import io
        with patch.object(sys, "argv",
                          ["batch-add-hardening-v2.py", "--dry-run", "--min-confidence", "1"]):
            with patch.object(sys, "stdout", io.StringIO()) as mock_stdout:
                try:
                    mod.main()
                except SystemExit:
                    pass
        content_after = f.read_text(encoding="utf-8")
        assert "phase-4-hardening" not in content_after  # dry-run shouldn't modify
