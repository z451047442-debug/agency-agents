"""Tests for scripts/check-deps.py — thin subprocess wrapper."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_mod():
    spec = importlib.util.spec_from_file_location(
        "check_deps", str(SCRIPTS_DIR / "check-deps.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCheckDeps:
    def test_default_mode_calls_validate(self):
        """main() with no flags runs --validate."""
        with patch.object(sys, "argv", ["check-deps.py"]):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mod = _load_mod()
                with pytest.raises(SystemExit) as exc:
                    mod.main()
                assert exc.value.code == 0

    def test_manifest_flag_adds_json(self):
        """main() with --manifest appends --json to args."""
        with patch.object(sys, "argv", ["check-deps.py", "--manifest"]):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mod = _load_mod()
                with pytest.raises(SystemExit):
                    mod.main()
                args_list = mock_run.call_args[0][0]
                assert "--json" in args_list

    def test_subprocess_failure_propagates(self):
        """main() propagates subprocess return code."""
        with patch.object(sys, "argv", ["check-deps.py"]):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 2
                mod = _load_mod()
                with pytest.raises(SystemExit) as exc:
                    mod.main()
                assert exc.value.code == 2
