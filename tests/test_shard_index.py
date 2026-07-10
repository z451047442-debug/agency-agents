"""Tests for scripts/shard-index.py — AGENTS.json sharding logic."""

import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "shard_index_mod", str(SCRIPTS_DIR / "shard-index.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

shard_index = mod.shard_index
check_shards = mod.check_shards


def _make_agent(idx, category):
    return {
        "id": f"{category}-agent-{idx}",
        "name": f"Agent {idx}",
        "category": category,
        "path": f"{category}/{category}-agent-{idx}.md",
    }


def _make_data(agents=None, total_agents=None, generated="2026-01-01"):
    if agents is None:
        agents = []
    return {
        "version": "1.0",
        "generated": generated,
        "total_agents": total_agents if total_agents is not None else len(agents),
        "agents": agents,
    }


def _write_shards(shard_dir, data):
    """Write shard files so check_shards finds them in sync."""
    by_cat = defaultdict(list)
    for ag in data["agents"]:
        by_cat[ag["category"]].append(ag)
    shard_dir.mkdir(parents=True, exist_ok=True)
    for cat, agents in by_cat.items():
        shard = {
            "category": cat, "agent_count": len(agents),
            "agents": agents, "generated": data["generated"],
        }
        (shard_dir / f"{cat}.json").write_text(
            json.dumps(shard, indent=2, ensure_ascii=False), encoding="utf-8")


# ── shard_index ──────────────────────────────────────────────────────────────

class TestShardIndex:
    def test_shards_into_category_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        data = _make_data([
            _make_agent(1, "engineering"), _make_agent(2, "engineering"),
            _make_agent(1, "design"),
        ])
        by_category, total_bytes, cat_index = shard_index(data)

        assert len(by_category["engineering"]) == 2
        assert len(by_category["design"]) == 1
        eng = json.loads((tmp_path / "engineering.json").read_text(encoding="utf-8"))
        assert eng["category"] == "engineering"
        assert eng["agent_count"] == 2

    def test_writes_index_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        data = _make_data([_make_agent(1, "engineering"), _make_agent(1, "design")])
        shard_index(data)

        idx = json.loads((tmp_path / "_index.json").read_text(encoding="utf-8"))
        assert idx["total_agents"] == 2
        assert idx["total_categories"] == 2
        categories = {c["category"] for c in idx["categories"]}
        assert categories == {"engineering", "design"}

    def test_index_entries_have_required_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        shard_index(_make_data([_make_agent(1, "engineering")]))

        idx = json.loads((tmp_path / "_index.json").read_text(encoding="utf-8"))
        entry = idx["categories"][0]
        for key in ("category", "agent_count", "file", "size_kb"):
            assert key in entry, f"Missing field: {key}"
        assert entry["file"] == "engineering.json"

    def test_returns_by_category_dict(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        data = _make_data([
            _make_agent(1, "eng"), _make_agent(2, "eng"), _make_agent(1, "ds"),
        ])
        by_category, _tb, _ci = shard_index(data)
        assert by_category["eng"][0]["id"] == "eng-agent-1"
        assert by_category["ds"][0]["id"] == "ds-agent-1"

    def test_returns_total_bytes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        _by_cat, total_bytes, _ci = shard_index(_make_data([_make_agent(1, "eng")]))
        assert total_bytes > 0
        assert isinstance(total_bytes, int)

    def test_handles_empty_agents_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        by_category, _tb, cat_index = shard_index(_make_data([], total_agents=0))

        assert by_category == {}
        assert cat_index["total_categories"] == 0
        idx = json.loads((tmp_path / "_index.json").read_text(encoding="utf-8"))
        assert idx["categories"] == []

    def test_single_category(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        data = _make_data([_make_agent(i, "solo") for i in range(5)])
        by_category, _tb, _ci = shard_index(data)
        assert list(by_category.keys()) == ["solo"]
        assert len(by_category["solo"]) == 5

    def test_many_categories(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        agents = []
        for cat in ("a", "b", "c", "d", "e"):
            for i in range(3):
                agents.append(_make_agent(i, cat))
        by_category, _tb, cat_index = shard_index(_make_data(agents, total_agents=15))
        assert len(by_category) == 5
        assert cat_index["total_categories"] == 5
        for cat in ("a", "b", "c", "d", "e"):
            assert (tmp_path / f"{cat}.json").exists()

    def test_shard_preserves_all_agent_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        agent = {
            "id": "engineering-custom",
            "name": "Custom Agent",
            "description": "A custom description",
            "emoji": "X",
            "category": "engineering",
            "subcategory": "tools",
            "path": "engineering/engineering-custom.md",
            "depends_on": ["other-agent"],
            "nexus_roles": ["phase-3-build"],
        }
        shard_index(_make_data([agent]))

        shard = json.loads((tmp_path / "engineering.json").read_text(encoding="utf-8"))
        saved = shard["agents"][0]
        for key in agent:
            assert saved[key] == agent[key], f"Mismatch on {key}"


# ── check_shards ─────────────────────────────────────────────────────────────

class TestCheckShards:
    def test_all_in_sync(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        data = _make_data([_make_agent(1, "eng"), _make_agent(2, "eng")])
        _write_shards(tmp_path, data)

        check_shards(data)
        assert "in sync" in capsys.readouterr().out

    def test_missing_shard_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        data = _make_data([_make_agent(1, "eng"), _make_agent(1, "design")])
        _write_shards(tmp_path, _make_data([_make_agent(1, "eng")]))

        with pytest.raises(SystemExit) as exc:
            check_shards(data)
        assert exc.value.code == 1

    def test_stale_shard_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        data = _make_data([_make_agent(1, "eng")])
        _write_shards(tmp_path, data)
        # Add a stale shard from a removed category
        (tmp_path / "legacy.json").write_text(
            json.dumps({"category": "legacy", "agent_count": 3, "agents": [],
                        "generated": "2026-01-01"}), encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            check_shards(data)
        assert exc.value.code == 1

    def test_count_mismatch_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        data = _make_data([_make_agent(i, "eng") for i in range(5)])
        # Write shard with only 3 agents
        shard_content = {
            "category": "eng", "agent_count": 3,
            "agents": [_make_agent(i, "eng") for i in range(3)],
            "generated": "2026-01-01",
        }
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "eng.json").write_text(
            json.dumps(shard_content, indent=2, ensure_ascii=False), encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            check_shards(data)
        assert exc.value.code == 1

    def test_missing_dir_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path / "nonexistent")
        data = _make_data([_make_agent(1, "eng")])
        with pytest.raises(SystemExit) as exc:
            check_shards(data)
        assert exc.value.code == 1
