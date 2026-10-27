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

install_agents = mod.install_agents


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

    def test_rejects_non_https_url(self):
        with pytest.raises(ValueError, match="non-HTTPS"):
            mod._open_url("http://example.com/file")

    def test_unsupported_tool_raises(self):
        with pytest.raises(ValueError, match="not supported"):
            install_agents("https://example.com/repo/main", "cursor", None, None)

    def _agent_responses(self, payload):
        index = MagicMock()
        index.read.return_value = (
            b'{"agents":[{"id":"eng-dev","category":"engineering","path":"eng/eng-dev.md"}]}'
        )
        index.__enter__.return_value = index
        body = MagicMock()
        body.read.return_value = payload
        body.__enter__.return_value = body
        return index, body

    def test_rejects_missing_frontmatter(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)
        index, body = self._agent_responses(b"not an agent")
        with patch.object(mod, "urlopen", side_effect=[index, body]):
            result = install_agents(
                "https://example.com/repo/main", "claude-code", None, None,
            )
        assert result == -1

    def test_rejects_oversized_payload(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)
        index, body = self._agent_responses(b"x" * (mod.MAX_AGENT_BYTES + 1))
        with patch.object(mod, "urlopen", side_effect=[index, body]):
            result = install_agents(
                "https://example.com/repo/main", "claude-code", None, None,
            )
        assert result == -1

    def test_rejects_invalid_utf8(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)
        index, body = self._agent_responses(b"\xff\xfe")
        with patch.object(mod, "urlopen", side_effect=[index, body]):
            result = install_agents(
                "https://example.com/repo/main", "claude-code", None, None,
            )
        assert result == -1

    def test_rejects_checksum_mismatch(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)
        payload = b"---\nname: Test\n---\n# Body"
        index, body = self._agent_responses(payload)
        with patch.object(mod, "urlopen", side_effect=[index, body]):
            result = install_agents(
                "https://example.com/repo/main", "claude-code", None, None,
                checksums={"eng/eng-dev.md": "0" * 64},
            )
        assert result == -1

    def test_load_checksums_rejects_non_object(self, tmp_path):
        manifest = tmp_path / "checksums.json"
        manifest.write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            mod._load_checksums(str(manifest))
