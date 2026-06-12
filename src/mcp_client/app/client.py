from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from src.mcp.cache import SQLiteKVCacheStore
from src.mcp.runtime import LocalToolRuntime

from ..agentic.memory.provider import MemoryContextProvider
from ..agentic.memory.store import MemoryStore
from ..agentic.skills import SkillRegistry
from ..presentation import PresentationPolicy
from ..presentation.policy import normalize_output_mode
from ..render import TerminalRenderer
from ..console import ConsoleREPLSession
from ..sessions import AgentSession
from ..sessions.store import SQLiteSessionStore, title_from_prompt
from ..transport import MCPOrchestratorAPI
from ..integrations.state import (
    ClientCacheMixin,
    ClientLifecycleMixin,
    ClientSessionsMixin,
)


class MCPClient(ClientCacheMixin, ClientSessionsMixin, ClientLifecycleMixin):
    def __init__(self, config):
        self.config = config
        self.auto_answer_questions = False
        self.runtime = LocalToolRuntime(config.runtime_config)
        self.renderer = TerminalRenderer(
            config.rich_output,
            presentation=PresentationPolicy(config.output_mode),
        )
        self.api = MCPOrchestratorAPI(
            config.server_url,
            timeout=config.request_timeout,
            bearer_token=config.server_bearer_token,
        )
        self.kv_cache = (
            SQLiteKVCacheStore(config.kv_cache_db_path)
            if config.kv_cache_enabled
            else None
        )
        self.skill_registry = self._init_skill_registry()
        self.active_skill: str | None = config.active_skill
        self.memory_provider = self._init_memory_provider()
        self.agent_session = self._new_agent_session()
        self.session_store = SQLiteSessionStore(config.session_db_path)
        self.repl_session = ConsoleREPLSession(self)
        self.slash_router = self.repl_session.slash_router
        self.command_context = self.repl_session.command_context
        self.prompt_session = self.repl_session.prompt_session

    def _init_skill_registry(self) -> SkillRegistry:
        base_dir = self.config.runtime_config.base_dir
        return SkillRegistry.from_paths(
            (Path.home() / ".mcp_skills", base_dir / ".mcp_skills")
        )

    def _init_memory_provider(self) -> MemoryContextProvider | None:
        project_store: MemoryStore | None = None
        user_store: MemoryStore | None = None
        embedding_enabled = self.config.memory_embedding_enabled
        ollama_url = getattr(self.config.runtime_config, "ollama_base_url", "http://127.0.0.1:11434")

        if self.config.memory_project_enabled:
            project_store = MemoryStore(
                self.config.memory_project_db_path,
                embedding_enabled=embedding_enabled,
                ollama_url=ollama_url,
            )

        if self.config.memory_user_enabled:
            user_db = Path(self.config.memory_user_db_path).expanduser()
            user_store = MemoryStore(
                user_db,
                embedding_enabled=embedding_enabled,
                ollama_url=ollama_url,
            )

        if project_store is None and user_store is None:
            return None
        return MemoryContextProvider(
            project_store=project_store,
            user_store=user_store,
            top_k=self.config.memory_top_k,
        )

    def _new_agent_session(self) -> AgentSession:
        return AgentSession(
            config=self.config,
            runtime=self.runtime,
            renderer=self.renderer,
            api=self.api,
            skill_registry=self.skill_registry,
            active_skill_name=self.active_skill,
            memory_provider=self.memory_provider,
        )

    def activate_skill(self, name: str) -> None:
        if self.skill_registry.get(name) is None:
            raise ValueError(f"Skill desconocido: '{name}'. Usa /skills list para ver disponibles.")
        self.active_skill = name
        self.agent_session = self._new_agent_session()

    def deactivate_skill(self) -> None:
        self.active_skill = None
        self.agent_session = self._new_agent_session()

    def list_skills(self) -> list[dict[str, object]]:
        return self.skill_registry.catalog()

    def info(self) -> dict[str, Any]:
        return {
            "client_name": self.config.client_name,
            "client_version": self.config.client_version,
            "server_url": self.config.server_url,
            "max_steps": self.config.max_steps,
            "request_timeout": self.config.request_timeout,
            "stream_responses": self.config.stream_responses,
            "show_thinking": self.config.show_thinking,
            "auto_write_code": self.config.auto_write_code,
            "rich_output": self.config.rich_output,
            "orchestrate_agents": self.config.orchestrate_agents,
            "planning_mode": self.config.planning_mode,
            "auto_answer_questions": self.auto_answer_questions,
            "server_auth_configured": self.config.server_bearer_token is not None,
            "trace_db_path": self.config.trace_db_path,
            "trace_capture": self.config.trace_capture,
            "trace_thinking": self.config.trace_thinking,
            "session_db_path": self.config.session_db_path,
            "kv_cache_enabled": self.config.kv_cache_enabled,
            "kv_cache_db_path": self.config.kv_cache_db_path,
            "context_window_tokens": self.config.context_window_tokens,
            "show_context_meter": self.config.show_context_meter,
            "output_mode": self.config.output_mode,
            "runtime": self.runtime.info(),
        }

    def list_nodes(self) -> dict[str, Any]:
        return self.api.nodes()

    def list_tools(self) -> list[dict[str, Any]]:
        return self.runtime.list_tools()

    def list_prompts(self) -> list[dict[str, Any]]:
        return self.runtime.list_prompts()

    def ask(
        self,
        prompt: str,
        messages: list[dict[str, Any]] | None = None,
        *,
        session_id: str | None = None,
        new_session: bool = False,
        force_team: bool = False,
    ) -> dict[str, Any]:
        if session_id and new_session:
            raise ValueError("Usa --session o --new-session, no ambos.")

        active_session_id = session_id
        if new_session:
            session = self.session_store.create_session(
                title=title_from_prompt(prompt) if self.config.auto_session_title else None,
                metadata={"source": "ask"},
            )
            active_session_id = session.id

        if active_session_id and messages is None:
            messages = self.session_store.load_messages(active_session_id)

        try:
            if force_team:
                result = self.agent_session.run(
                    prompt,
                    messages=messages,
                    force_team=True,
                )
            else:
                result = self.agent_session.run(prompt, messages=messages)
        except Exception as exc:
            if active_session_id:
                failed_messages = list(messages or [])
                failed_messages.append({"role": "user", "content": prompt})
                self.session_store.replace_messages(active_session_id, failed_messages)
                self.session_store.record_error(active_session_id, str(exc))
            raise

        if active_session_id:
            self.session_store.replace_messages(active_session_id, result["messages"])
            result["session_id"] = active_session_id

        return result

    def repl(
        self,
        *,
        session_id: str | None = None,
        continue_session: bool = False,
    ) -> int:
        return self.repl_session.run(
            session_id=session_id,
            continue_session=continue_session,
        )

    def health(self) -> dict[str, Any]:
        return self.api.health()

    def set_planning_mode(self, mode: str) -> None:
        if mode not in {"auto", "always", "never"}:
            raise ValueError("Modo invalido. Usa auto, always o never.")

        self.config = replace(
            self.config,
            planning_mode=mode,
            orchestrate_agents=(mode != "never"),
        )
        self.agent_session = self._new_agent_session()

    def set_show_thinking(self, enabled: bool) -> bool:
        self.config = replace(self.config, show_thinking=enabled)
        self.agent_session = self._new_agent_session()
        return self.config.show_thinking

    def toggle_show_thinking(self) -> bool:
        return self.set_show_thinking(not self.config.show_thinking)

    def is_show_thinking_enabled(self) -> bool:
        return self.config.show_thinking

    def set_auto_answer_questions(self, enabled: bool) -> bool:
        self.auto_answer_questions = enabled
        return self.auto_answer_questions

    def toggle_auto_answer_questions(self) -> bool:
        return self.set_auto_answer_questions(not self.auto_answer_questions)

    def is_auto_answer_questions_enabled(self) -> bool:
        return self.auto_answer_questions

    def set_output_mode(self, mode: str) -> str:
        output_mode = normalize_output_mode(mode)
        self.config = replace(self.config, output_mode=output_mode)
        self.renderer.presentation = PresentationPolicy(output_mode)
        self.agent_session = self._new_agent_session()
        return self.config.output_mode
