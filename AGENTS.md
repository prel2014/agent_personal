# Repository Guidelines

## Project Structure & Module Organization

This is a Python 3.10+ project using a `src/` layout. Core runtime and tool permissions live in `src/mcp/`; the CLI client, sessions, rendering, slash commands, and agentic workflows live in `src/mcp_client/`; the HTTP server, Ollama routing, settings, and node discovery live in `src/mcp_server/`; shared helpers are in `src/mcp_shared/`. Documentation is under `docs/`, runnable examples are under `examples/`, and local caches such as `.mcp_cache/` and `.mcp_sessions/` should remain uncommitted. Specification-driven notes live beside subsystems as `*.sdd.md`.

## Build, Test, and Development Commands

- `python -m pip install -e .`: install the package in editable mode with the `rag-agent` entry point.
- `python -m pip install -r requirements.txt`: install runtime dependencies.
- `python -m src.mcp_server.server.cli --host 127.0.0.1 --port 8000`: start the MCP/Ollama server locally.
- `python -m src.mcp_client.commands.cli doctor`: validate client configuration.
- `python -m src.mcp_client.commands.cli repl --continue`: start or resume an interactive client session.
- `python -m pytest`: run the test suite configured for `tests/`.

## Coding Style & Naming Conventions

Use 4-space indentation, type hints for public functions, and small modules that follow existing package boundaries. Prefer `snake_case` for functions, variables, modules, CLI flags, and JSON keys; use `PascalCase` for classes and Pydantic models. Keep configuration parsing in `settings/` or `config/`, transport concerns in `transport/`, and command behavior in `commands/` or `slash/`. Comment only non-obvious control flow or security decisions.

## Testing Guidelines

Pytest is configured in `pyproject.toml` with `testpaths = ["tests"]`; add tests under `tests/` using names like `test_sessions_store.py` and functions named `test_<behavior>()`. Cover command parsing, settings resolution, sandbox/security policy, and serialization changes before touching user-facing workflows. For network, Docker, Ollama, or hardware code, prefer fakes and document integration setup in `docs/`.

## Commit & Pull Request Guidelines

This checkout has no Git history available, so use clear imperative commit messages such as `Add session resume validation` or `Fix sandbox domain filtering`. Pull requests should include a problem statement, implementation summary, test results, and any configuration or security implications. Link related issues or docs, and include terminal output or screenshots only when they clarify CLI behavior.

## Security & Configuration Tips

Do not commit bearer tokens, node credentials, generated SQLite caches, or local machine paths. Use `examples/ollama_nodes.example.json` as the template for node configuration, and document new environment variables or CLI flags in `README.md` or the relevant `docs/` page.
