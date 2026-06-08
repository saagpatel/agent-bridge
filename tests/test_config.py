from __future__ import annotations

from pathlib import Path

from agent_bridge import config


def test_default_agents():
    agents = config.agents()
    assert "claude-code" in agents
    assert "human" in agents


def test_agents_env_override(monkeypatch):
    monkeypatch.setenv("AGENT_BRIDGE_AGENTS", "cursor, aider ,human")
    assert config.agents() == ("cursor", "aider", "human")


def test_agents_empty_override_falls_back(monkeypatch):
    monkeypatch.setenv("AGENT_BRIDGE_AGENTS", "   ,  ")
    assert config.agents() == ("claude-code", "codex", "claude-ai", "human")


def test_is_known_agent(monkeypatch):
    monkeypatch.setenv("AGENT_BRIDGE_AGENTS", "cursor")
    assert config.is_known_agent("cursor")
    assert not config.is_known_agent("codex")


def test_db_path_env_override(monkeypatch):
    monkeypatch.setenv("AGENT_BRIDGE_DB_PATH", "/tmp/custom/bridge.db")
    assert config.db_path() == Path("/tmp/custom/bridge.db")


def test_db_path_xdg(monkeypatch):
    monkeypatch.delenv("AGENT_BRIDGE_DB_PATH", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", "/tmp/xdg")
    assert config.db_path() == Path("/tmp/xdg/agent-bridge/bridge.db")


def test_markdown_path_defaults_next_to_db(monkeypatch):
    monkeypatch.setenv("AGENT_BRIDGE_DB_PATH", "/tmp/x/bridge.db")
    monkeypatch.delenv("AGENT_BRIDGE_MARKDOWN_PATH", raising=False)
    assert config.markdown_path() == Path("/tmp/x/bridge.md")
