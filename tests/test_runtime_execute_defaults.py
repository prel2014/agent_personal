from __future__ import annotations

import argparse

from src.mcp.settings.argparse import add_config_arguments
from src.mcp.settings.model import Config


def test_runtime_allows_execute_by_default(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("MCP_ALLOW_EXECUTE", raising=False)

    config = Config.from_sources(argparse.Namespace(base_dir=str(tmp_path)))

    assert config.allow_execute is True


def test_runtime_execute_can_be_disabled_by_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MCP_ALLOW_EXECUTE", "false")

    config = Config.from_sources(argparse.Namespace(base_dir=str(tmp_path)))

    assert config.allow_execute is False


def test_runtime_execute_can_be_disabled_by_cli(tmp_path) -> None:
    parser = add_config_arguments(argparse.ArgumentParser())
    args = parser.parse_args(["--base-dir", str(tmp_path), "--deny-execute"])

    config = Config.from_sources(args)

    assert config.allow_execute is False


def test_read_only_still_disables_execute(tmp_path) -> None:
    config = Config.from_sources(
        argparse.Namespace(base_dir=str(tmp_path), read_only=True)
    )

    assert config.allow_execute is False
