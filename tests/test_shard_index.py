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
        # Also create _index.json to cover the skip logic (line 124)
        (tmp_path / "_index.json").write_text("{}", encoding="utf-8")

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

    def test_invalid_json_exits_1(self, tmp_path, monkeypatch):
        """check_shards handles invalid JSON in shard file (lines 118-119)."""
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path)
        data = _make_data([_make_agent(1, "eng")])
        # Write corrupt JSON to the shard file
        (tmp_path / "eng.json").write_text("{not valid json!!!", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            check_shards(data)
        assert exc.value.code == 1


# ── load_index ─────────────────────────────────────────────────────────────

class TestLoadIndex:
    def test_file_not_found_exits(self, monkeypatch):
        """load_index exits when AGENTS.json is missing (lines 39-40)."""
        monkeypatch.setattr(mod, "INDEX_PATH", Path("/nonexistent/AGENTS.json"))
        with pytest.raises(SystemExit) as exc:
            mod.load_index()
        assert exc.value.code == 1


# ── print_stats ────────────────────────────────────────────────────────────

class TestPrintStats:
    def _setup_shards(self, tmp_path, monkeypatch, categories=None):
        """Create shard files for print_stats to read."""
        if categories is None:
            categories = {"engineering": 5, "design": 3}
        shard_dir = tmp_path / "shards"
        shard_dir.mkdir()
        for cat, count in categories.items():
            agents = [_make_agent(i, cat) for i in range(count)]
            shard = {
                "category": cat,
                "agent_count": count,
                "agents": agents,
                "generated": "2026-01-01",
            }
            (shard_dir / f"{cat}.json").write_text(
                json.dumps(shard, indent=2, ensure_ascii=False), encoding="utf-8",
            )
        # Create INDEX_PATH pointing to a dummy file so stat works
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        monkeypatch.setattr(mod, "SHARD_DIR", shard_dir)
        return shard_dir

    def test_prints_distribution(self, tmp_path, monkeypatch, capsys):
        self._setup_shards(tmp_path, monkeypatch)
        mod.print_stats()
        captured = capsys.readouterr()
        assert "Shard Size Distribution" in captured.out
        assert "Total:" in captured.out

    def test_shows_largest_shard(self, tmp_path, monkeypatch, capsys):
        self._setup_shards(tmp_path, monkeypatch)
        mod.print_stats()
        captured = capsys.readouterr()
        assert "Largest shard" in captured.out

    def test_shows_category_rows(self, tmp_path, monkeypatch, capsys):
        self._setup_shards(tmp_path, monkeypatch)
        mod.print_stats()
        captured = capsys.readouterr()
        assert "engineering" in captured.out
        assert "design" in captured.out

    def test_no_shards_exits(self, tmp_path, monkeypatch):
        """print_stats exits when SHARD_DIR doesn't exist (line 142-143)."""
        monkeypatch.setattr(mod, "SHARD_DIR", tmp_path / "nonexistent")
        with pytest.raises(SystemExit) as exc:
            mod.print_stats()
        assert exc.value.code == 1

    def test_skips_index_file(self, tmp_path, monkeypatch, capsys):
        """print_stats skips _index.json when iterating shards (line 147)."""
        shard_dir = tmp_path / "shards"
        shard_dir.mkdir()
        # _index.json plus one real shard to avoid the 0-shard crash bug
        (shard_dir / "_index.json").write_text("{}", encoding="utf-8")
        (shard_dir / "engineering.json").write_text(
            json.dumps({"category": "engineering", "agent_count": 1,
                        "agents": [_make_agent(1, "engineering")],
                        "generated": "2026-01-01"}),
            encoding="utf-8",
        )
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        monkeypatch.setattr(mod, "SHARD_DIR", shard_dir)
        mod.print_stats()
        captured = capsys.readouterr()
        # _index.json should be skipped, only engineering shows
        assert "engineering" in captured.out


# ── stdout encoding ────────────────────────────────────────────────────────

class TestStdoutEncoding:
    def test_reconfigure_on_non_utf8(self, monkeypatch):
        """Cover line 29: sys.stdout.reconfigure when encoding != utf-8."""
        import io

        class MockStdout(io.StringIO):
            encoding = "ascii"
            def reconfigure(self, **kwargs):
                pass

        fake_stdout = MockStdout()
        monkeypatch.setattr(sys, "stdout", fake_stdout)
        import importlib.util
        spec2 = importlib.util.spec_from_file_location(
            "shard_index_enc", str(SCRIPTS_DIR / "shard-index.py")
        )
        mod2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mod2)


# ── main ───────────────────────────────────────────────────────────────────

class TestMain:
    def _setup_index(self, tmp_path, monkeypatch, agents=None):
        if agents is None:
            agents = [_make_agent(1, "eng"), _make_agent(2, "eng"), _make_agent(1, "ds")]
        index_path = tmp_path / "AGENTS.json"
        data = _make_data(agents, total_agents=len(agents))
        index_path.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        # Also redirect SHARD_DIR so sharding output goes to tmp
        shard_dir = tmp_path / "by-category"
        monkeypatch.setattr(mod, "SHARD_DIR", shard_dir)
        return index_path

    def test_default_mode_shards_index(self, tmp_path, monkeypatch, capsys):
        """main() runs shard_index by default (lines 186-193)."""
        self._setup_index(tmp_path, monkeypatch)
        monkeypatch.setattr("sys.argv", ["shard-index.py"])
        mod.main()
        captured = capsys.readouterr()
        assert "sharded successfully" in captured.out

    def test_check_mode(self, tmp_path, monkeypatch, capsys):
        """main() --check runs check_shards (lines 181-182)."""
        self._setup_index(tmp_path, monkeypatch)
        # Pre-populate shards in sync so check passes
        shard_dir = tmp_path / "by-category"
        shard_dir.mkdir(parents=True, exist_ok=True)
        _write_shards(shard_dir, _make_data(
            [_make_agent(1, "eng"), _make_agent(2, "eng"), _make_agent(1, "ds")],
            total_agents=3,
        ))

        monkeypatch.setattr("sys.argv", ["shard-index.py", "--check"])
        mod.main()
        captured = capsys.readouterr()
        assert "in sync" in captured.out

    def test_stats_mode(self, tmp_path, monkeypatch, capsys):
        """main() --stats runs print_stats (lines 183-184)."""
        self._setup_index(tmp_path, monkeypatch)
        # Pre-populate shards
        shard_dir = tmp_path / "by-category"
        shard_dir.mkdir(parents=True, exist_ok=True)
        _write_shards(shard_dir, _make_data(
            [_make_agent(1, "eng")], total_agents=1,
        ))
        # Need the INDEX_PATH file itself for the stat call
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(json.dumps(_make_data(
            [_make_agent(1, "eng")], total_agents=1,
        )), encoding="utf-8")

        monkeypatch.setattr("sys.argv", ["shard-index.py", "--stats"])
        mod.main()
        captured = capsys.readouterr()
        assert "Shard Size Distribution" in captured.out
