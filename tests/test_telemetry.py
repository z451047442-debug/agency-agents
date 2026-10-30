"""Tests for scripts/telemetry.py best-effort writes."""
import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("telemetry", str(SCRIPTS_DIR / "telemetry.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_record_event_swallows_write_errors(monkeypatch):
    monkeypatch.setattr(mod, "is_enabled", lambda: True)
    monkeypatch.setattr(mod, "_load", lambda: {"events": []})

    def _boom(_data):
        raise OSError("disk full")

    monkeypatch.setattr(mod, "_save", _boom)
    mod.record_event("lint")  # telemetry must never break the caller
