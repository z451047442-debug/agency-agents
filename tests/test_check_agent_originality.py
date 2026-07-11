"""Tests for scripts/check-agent-originality.py — originality detection."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "check_agent_originality", str(SCRIPTS_DIR / "check-agent-originality.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

strip_frontmatter = mod.strip_frontmatter
tokens = mod.tokens
shingles = mod.shingles
jaccard = mod.jaccard
is_agent = mod.is_agent
build_corpus = mod.build_corpus
check_originality = mod.check_originality


class TestStripFrontmatter:
    def test_strips_valid_frontmatter(self):
        text = "---\nname: Test\n---\nBody content here"
        result = strip_frontmatter(text)
        assert result == "\nBody content here"

    def test_no_frontmatter_passes_through(self):
        text = "Plain text without frontmatter"
        assert strip_frontmatter(text) == text

    def test_only_one_delimiter(self):
        text = "---\npartial frontmatter"
        assert strip_frontmatter(text) == text


class TestTokens:
    def test_lowercases(self):
        assert "hello" in tokens("HELLO World")

    def test_neutralizes_entities(self):
        result = tokens("A vietnam market specialist for tiktok campaigns")
        assert "vietnam" not in result
        assert "tiktok" not in result

    def test_returns_word_list(self):
        result = tokens("one two three")
        assert isinstance(result, list)
        assert result == ["one", "two", "three"]


class TestShingles:
    def test_8_word_shingles(self):
        words = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]
        result = shingles(words, k=8)
        assert len(result) == 2
        assert "a b c d e f g h" in result
        assert "b c d e f g h i" in result

    def test_short_input(self):
        words = ["a", "b", "c"]
        result = shingles(words, k=8)
        assert result == set()

    def test_exact_k_words(self):
        words = ["a", "b", "c", "d", "e", "f", "g", "h"]
        result = shingles(words, k=8)
        assert len(result) == 1


class TestJaccard:
    def test_identical_sets(self):
        assert jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_empty_set(self):
        assert jaccard(set(), {"a"}) == 0.0

    def test_partial_overlap(self):
        result = jaccard({"a", "b"}, {"b", "c"})
        assert result == 1 / 3


class TestIsAgent:
    def test_agent_file(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text("---\nname: Test\n---\nBody", encoding="utf-8")
        assert is_agent(f) is True

    def test_non_agent_file(self, tmp_path):
        f = tmp_path / "readme.md"
        f.write_text("# README\nSome content", encoding="utf-8")
        assert is_agent(f) is False

    def test_missing_file(self, tmp_path):
        assert is_agent(tmp_path / "nonexistent.md") is False


class TestBuildCorpus:
    def test_builds_from_directory(self, tmp_path, monkeypatch):
        d = tmp_path / "engineering"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: Test\n---\nUnique content for testing purposes", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        corpus = build_corpus(["engineering"])
        assert len(corpus) == 1

    def test_skips_non_agent_files(self, tmp_path, monkeypatch):
        d = tmp_path / "engineering"
        d.mkdir()
        (d / "README.md").write_text("not an agent", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        corpus = build_corpus(["engineering"])
        assert len(corpus) == 0


class TestCheckOriginality:
    def test_unique_agents_pass(self, tmp_path):
        f1 = tmp_path / "a1.md"
        f1.write_text("---\nname: A\n---\n" + ("alpha " * 200), encoding="utf-8")
        f2 = tmp_path / "a2.md"
        f2.write_text("---\nname: B\n---\n" + ("beta " * 200), encoding="utf-8")
        corpus = {
            str(f1.resolve()): shingles(tokens(f1.read_text(encoding="utf-8"))),
            str(f2.resolve()): shingles(tokens(f2.read_text(encoding="utf-8"))),
        }
        exit_code, lines = check_originality([f1, f2], corpus)
        assert exit_code == 0

    def test_near_duplicates_fail(self, tmp_path):
        content = "---\nname: A\n---\n" + ("shared content block. " * 100)
        f1 = tmp_path / "a1.md"
        f1.write_text(content, encoding="utf-8")
        f2 = tmp_path / "a2.md"
        f2.write_text(content, encoding="utf-8")
        corpus = {
            str(f1.resolve()): shingles(tokens(content)),
            str(f2.resolve()): shingles(tokens(content)),
        }
        exit_code, lines = check_originality([f1, f2], corpus)
        assert exit_code == 1

    def test_entity_neutralization(self, tmp_path):
        common = ("We are a marketing agency that helps businesses expand their "
                  "digital presence through social media campaigns and content "
                  "strategy across all major platforms with proven results")
        f1 = tmp_path / "a1.md"
        f1.write_text(f"---\nname: VN\n---\n{common} we focus on vietnam market and tiktok strategy", encoding="utf-8")
        f2 = tmp_path / "a2.md"
        f2.write_text(f"---\nname: ID\n---\n{common} we focus on indonesia market and instagram strategy", encoding="utf-8")
        corpus = {
            str(f1.resolve()): shingles(tokens(f1.read_text(encoding="utf-8"))),
            str(f2.resolve()): shingles(tokens(f2.read_text(encoding="utf-8"))),
        }
        exit_code, _ = check_originality(
            [f1, f2], corpus, fail_threshold=50, warn_threshold=20,
        )
        assert exit_code == 1

    def test_respects_warn_threshold(self, tmp_path):
        f1 = tmp_path / "a1.md"
        f1.write_text("---\nname: A\n---\n" + ("common " * 50) + ("unique a " * 100), encoding="utf-8")
        f2 = tmp_path / "a2.md"
        f2.write_text("---\nname: B\n---\n" + ("common " * 50) + ("unique b " * 100), encoding="utf-8")
        corpus = {
            str(f1.resolve()): shingles(tokens(f1.read_text(encoding="utf-8"))),
            str(f2.resolve()): shingles(tokens(f2.read_text(encoding="utf-8"))),
        }
        exit_code, _ = check_originality([f1, f2], corpus, warn_threshold=90, fail_threshold=95)
        assert exit_code == 0


class TestCheckOriginalityExtra:
    def test_warns_not_fails(self, tmp_path):
        content = ("The quick brown fox jumps over the lazy dog. " * 30).strip()
        f1 = tmp_path / "a1.md"
        f1.write_text("---\nname: A\n---\n" + content, encoding="utf-8")
        f2 = tmp_path / "a2.md"
        f2.write_text("---\nname: B\n---\n" + content + " extra unique suffix here", encoding="utf-8")
        corpus = {
            str(f1.resolve()): shingles(tokens(f1.read_text(encoding="utf-8"))),
            str(f2.resolve()): shingles(tokens(f2.read_text(encoding="utf-8"))),
        }
        exit_code, lines = check_originality(
            [f1, f2], corpus, fail_threshold=95, warn_threshold=30,
        )
        assert exit_code == 0
        assert any("warning" in l.lower() for l in lines)

    def test_same_change_set_beats_corpus(self, tmp_path):
        content = "shared common text for testing purposes across all files. " * 20
        f1 = tmp_path / "a1.md"
        f1.write_text("---\nname: A\n---\n" + content, encoding="utf-8")
        f2 = tmp_path / "a2.md"
        f2.write_text("---\nname: B\n---\n" + content, encoding="utf-8")
        # Corpus only has one entry — the other candidate must be the closer match
        corpus = {str(f1.resolve()): shingles(tokens(content))}
        exit_code, _ = check_originality([f1, f2], corpus)
        assert exit_code == 1


class TestMainFunction:
    def test_skip_non_agent(self, tmp_path, monkeypatch, capsys):
        f = tmp_path / "readme.md"
        f.write_text("not an agent", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["check-agent-originality.py", str(f)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0
        assert "skip" in capsys.readouterr().out

    def test_skip_not_found(self, monkeypatch, capsys):
        with patch.object(sys, "argv",
                          ["check-agent-originality.py", "/nonexistent/file.md"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0
        assert "skip" in capsys.readouterr().out

    def test_no_files_audit_mode(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "DEFAULT_AGENT_DIRS", [])
        with patch.object(sys, "argv", ["check-agent-originality.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0

    def test_non_agent_outside_repo(self, tmp_path, monkeypatch, capsys):
        """Non-agent file that's outside REPO → ValueError path."""
        f = tmp_path / "notes.txt"
        f.write_text("not an agent file", encoding="utf-8")
        # Set REPO to a different dir so relative_to fails
        monkeypatch.setattr(mod, "REPO", tmp_path / "subdir")
        (tmp_path / "subdir").mkdir()
        with patch.object(sys, "argv", ["check-agent-originality.py", str(f)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0
        assert "skip" in capsys.readouterr().out

    def test_valid_agent_file_passed(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "engineering"
        d.mkdir()
        f1 = d / "agent1.md"
        f1.write_text("---\nname: Test A\n---\n" + ("unique alpha words. " * 50), encoding="utf-8")
        f2 = d / "agent2.md"
        f2.write_text("---\nname: Test B\n---\n" + ("distinct beta content. " * 50), encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "DEFAULT_AGENT_DIRS", ["engineering"])
        with patch.object(sys, "argv", ["check-agent-originality.py", str(f1)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            # Unique agent should pass
            assert exc.value.code == 0
