from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.mcp_shared.agent_contracts import AgentExecutionContext

from .prompt_registry import PromptRegistry, load_default_prompt_registry
from .prompt_renderer import PromptRenderer
from .prompt_rules import PromptRuleSet


@dataclass(frozen=True)
class OllamaPromptBuilder:
    system_prompt: str
    rules: PromptRuleSet = field(default_factory=PromptRuleSet)
    registry: PromptRegistry | None = None
    renderer: PromptRenderer = field(default_factory=PromptRenderer)

    def build(self, client_context: dict[str, Any]) -> str:
        context = AgentExecutionContext.from_runtime_context(client_context)
        registry = (
            self.registry
            if self.registry is not None
            else load_default_prompt_registry()
        )
        if registry is not None:
            template = registry.resolve(_prompt_mode(context))
            if template is not None:
                try:
                    return self.renderer.render(
                        system_prompt=self.system_prompt,
                        context=context,
                        registry=registry,
                        template=template,
                        mode_rules=self.rules.mode_rules(context),
                    )
                except Exception:
                    pass
        return self._legacy_build(context)

    def _legacy_build(self, context: AgentExecutionContext) -> str:
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


def _prompt_mode(context: AgentExecutionContext) -> str:
    if context.prompt_mode:
        return context.prompt_mode
    if context.direct_answer_mode:
        return "direct_answer"
    return context.agent_role or "tool_workflow"
