"""Tests for scripts/quality.py — pipeline runner."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_mod():
    spec = importlib.util.spec_from_file_location(
        "quality", str(SCRIPTS_DIR / "quality.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestQualityPipeline:
    def test_all_steps_pass(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with pytest.raises(SystemExit) as exc:
                _load_mod()
            assert exc.value.code == 0
            assert mock_run.call_count == 5

    def test_some_steps_fail(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            with pytest.raises(SystemExit) as exc:
                _load_mod()
            assert exc.value.code == 1

    def test_mixed_results_count(self):
        with patch("subprocess.run") as mock_run:
            results = [MagicMock(returncode=0), MagicMock(returncode=1),
                       MagicMock(returncode=0), MagicMock(returncode=0),
                       MagicMock(returncode=0)]
            mock_run.side_effect = results
            with pytest.raises(SystemExit) as exc:
                _load_mod()
            assert exc.value.code == 1
