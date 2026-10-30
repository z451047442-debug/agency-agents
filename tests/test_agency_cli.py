"""Tests for agency_cli.py dispatch return codes."""
import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("agency_cli", str(ROOT / "agency_cli.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class _FakeQuality:
    @staticmethod
    def main():
        return 1


def test_dispatched_return_code_is_propagated(monkeypatch):
    monkeypatch.setattr(importlib, "import_module", lambda _name: _FakeQuality())
    monkeypatch.setattr(sys, "argv", ["agency", "quality"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1


def test_unknown_command_exits_1(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["agency", "not-a-command"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
