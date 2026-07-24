"""Tests for scripts/quality.py — pipeline runner."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import quality


class TestQualityPipeline:
    def test_all_steps_pass(self, monkeypatch):
        """All in-process and subprocess steps succeed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            monkeypatch.setattr(quality, "_run_script", lambda *a, **kw: True)
            result = quality.main()
            assert result == 0
            assert mock_run.call_count == 2

    def test_some_steps_fail(self, monkeypatch):
        """External step failure causes non-zero exit."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            monkeypatch.setattr(quality, "_run_script", lambda *a, **kw: True)
            result = quality.main()
            assert result == 1

    # ── _run_script() unit tests ──────────────────────────────────────────

    def test_run_script_with_real_module_returns_true(self):
        """_run_script loads a real Python module with a main() and returns True."""
        script_path = SCRIPTS_DIR / "ab-test.py"
        result = quality._run_script("ab_test", script_path, [])
        assert result is True

    def test_run_script_nonexistent_file_returns_false(self):
        """_run_script returns False when the file path does not exist."""
        result = quality._run_script(
            "nonexistent", Path("nonexistent_file_xyz.py"), []
        )
        assert result is False

    def test_run_script_systemexit_zero_returns_true(self, tmp_path):
        """_run_script returns True when the script calls sys.exit(0)."""
        script = tmp_path / "exit_zero.py"
        script.write_text(
            "import sys\n"
            "def main():\n"
            "    print('ok')\n"
            "    sys.exit(0)\n"
        )
        result = quality._run_script("exit_zero", script, [])
        assert result is True

    def test_run_script_systemexit_nonzero_returns_false(self, tmp_path):
        """_run_script returns False when the script calls sys.exit(1)."""
        script = tmp_path / "exit_one.py"
        script.write_text(
            "import sys\n"
            "def main():\n"
            "    sys.exit(1)\n"
        )
        result = quality._run_script("exit_one", script, [])
        assert result is False

    def test_run_script_exception_returns_false(self, tmp_path):
        """_run_script returns False when the script raises an unhandled exception."""
        script = tmp_path / "raise_err.py"
        script.write_text(
            "def main():\n"
            "    raise RuntimeError('simulated failure')\n"
        )
        result = quality._run_script("raise_err", script, [])
        assert result is False

    def test_run_script_args_none_defaults_to_empty_list(self):
        """_run_script defaults args to [] when called with args=None (line 21)."""
        script_path = SCRIPTS_DIR / "ab-test.py"
        result = quality._run_script("ab_test", script_path, args=None)
        assert result is True

    def test_run_script_spec_loader_none_returns_false(self, monkeypatch):
        """_run_script returns False when spec has loader=None (lines 27-28)."""
        import importlib.util as _iu
        fake_spec = _iu.spec_from_file_location("x", SCRIPTS_DIR / "ab-test.py")
        fake_spec.loader = None  # force missing loader
        monkeypatch.setattr(quality.importlib.util, "spec_from_file_location",
                            lambda *a, **kw: fake_spec)
        result = quality._run_script("x", Path("dummy.py"), [])
        assert result is False

    # ── pipeline in-process failure  ──────────────────────────────────────

    def test_in_process_step_fails(self, monkeypatch):
        """Pipeline returns 1 when an in-process step fails (line ~63 branch)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0  # external steps pass

            calls = {"count": 0}

            def failing_run_script(_name, _path, _args=None):
                calls["count"] += 1
                return calls["count"] != 2  # second in-process step fails

            monkeypatch.setattr(quality, "_run_script", failing_run_script)
            result = quality.main()
            assert result == 1
            assert calls["count"] == 3   # all 3 in-process steps still ran
            assert mock_run.call_count == 2  # both external steps still ran
