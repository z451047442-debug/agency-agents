"""Tests for scripts/install-remote.py — remote agent installer."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "install_remote", str(SCRIPTS_DIR / "install-remote.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

slugify = mod.slugify
install_agents = mod.install_agents


class TestSlugify:
    def test_simple(self):
        assert slugify("Frontend Developer") == "frontend-developer"

    def test_special_chars(self):
        assert slugify("C++ Expert (Embedded)") == "c-expert-embedded"

    def test_multiple_dashes(self):
        assert slugify("A & B -- Co.") == "a-b-co"

    def test_leading_trailing_dash(self):
        assert slugify("-hello world-") == "hello-world"

    def test_numbers(self):
        assert slugify("Model 3.0 Pro") == "model-3-0-pro"


class TestInstallAgents:
    def test_empty_index(self, tmp_path):
        """No agents in index should return 0."""
        with patch.object(mod, "Path") as mock_path:
            mock_path.home.return_value = tmp_path
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"agents":[]}'
            mock_resp.__enter__.return_value = mock_resp
            with patch.object(mod, "urlopen", return_value=mock_resp):
                result = install_agents(
                    "https://example.com/repo/main",
                    "claude-code", None, None,
                )
                assert result == 0

    def test_with_division_filter(self, tmp_path):
        """Division filter should skip non-matching agents."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b'{"agents":['
            b'{"id":"eng-dev","category":"engineering","path":"eng/eng-dev.md"},'
            b'{"id":"des-ux","category":"design","path":"des/des-ux.md"}'
            b']}'
        )
        mock_resp.__enter__.return_value = mock_resp

        mock_resp2 = MagicMock()
        mock_resp2.read.return_value = b"---\nname: Test\n---\n# Hello"
        mock_resp2.__enter__.return_value = mock_resp2

        with patch.object(mod, "Path") as mock_path:
            mock_path.home.return_value = tmp_path
            with patch.object(mod, "urlopen", side_effect=[mock_resp, mock_resp2]):
                result = install_agents(
                    "https://example.com/repo/main",
                    "claude-code", {"engineering"}, None,
                )
                assert result == 1

    def test_with_agent_filter(self, tmp_path):
        """Agent filter should only install matching agent."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b'{"agents":['
            b'{"id":"eng-dev","category":"engineering","path":"eng/eng-dev.md"},'
            b'{"id":"des-ux","category":"design","path":"des/des-ux.md"}'
            b']}'
        )
        mock_resp.__enter__.return_value = mock_resp

        mock_resp2 = MagicMock()
        mock_resp2.read.return_value = b"---\nname: Test\n---\n# Hello"
        mock_resp2.__enter__.return_value = mock_resp2

        with patch.object(mod, "Path") as mock_path:
            mock_path.home.return_value = tmp_path
            with patch.object(mod, "urlopen", side_effect=[mock_resp, mock_resp2]):
                result = install_agents(
                    "https://example.com/repo/main",
                    "claude-code", None, "eng-dev",
                )
                assert result == 1

    def test_download_writes_file(self, tmp_path):
        """Downloaded agent should be written to dest directory."""
        dest = tmp_path / ".claude" / "agents"
        agent_content = b"---\nname: My Agent\n---\n# Body"

        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b'{"agents":['
            b'{"id":"eng-dev","category":"engineering","path":"eng/eng-dev.md"}'
            b']}'
        )
        mock_resp.__enter__.return_value = mock_resp

        mock_resp2 = MagicMock()
        mock_resp2.read.return_value = agent_content
        mock_resp2.__enter__.return_value = mock_resp2

        with patch.object(mod, "Path") as mock_path:
            mock_path.home.return_value = tmp_path
            with patch.object(mod, "urlopen", side_effect=[mock_resp, mock_resp2]):
                result = install_agents(
                    "https://example.com/repo/main",
                    "claude-code", None, None,
                )
                assert result == 1
                written = dest / "eng-dev.md"
                assert written.exists()
                assert written.read_bytes() == agent_content
