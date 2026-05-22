from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.mcp_shared.agent_contracts import AgentExecutionContext

from .prompt_rules import PromptRuleSet


@dataclass(frozen=True)
class OllamaPromptBuilder:
    system_prompt: str
    rules: PromptRuleSet = field(default_factory=PromptRuleSet)

    def build(self, client_context: dict[str, Any]) -> str:
        context = AgentExecutionContext.from_runtime_context(client_context)
        serialized_context = json.dumps(
            self.rules.context_payload(context),
            ensure_ascii=False,
            indent=2,
        )
        return (
            f"{self.system_prompt}\n\n"
            "Contexto actual del cliente:\n"
            f"{serialized_context}\n\n"
            f"{self._role_hint(context)}"
            f"{self.rules.mode_rules(context)}"
        )

    @staticmethod
    def _role_hint(context: AgentExecutionContext) -> str:
        role_hint = ""
        agent_role = context.agent_role
        role_directive = context.role_directive
        if isinstance(agent_role, str) and agent_role:
            role_hint += f"Rol actual del agente: {agent_role}.\n"
        if isinstance(role_directive, str) and role_directive:
            role_hint += f"Directiva del rol:\n{role_directive}\n\n"
        return role_hint
