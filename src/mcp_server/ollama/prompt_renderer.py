from __future__ import annotations

import json
from dataclasses import dataclass, field

from src.mcp_shared.agent_contracts import AgentExecutionContext

from .prompt_context import PromptContextComposer
from .prompt_registry import PromptRegistry, PromptTemplate
from .prompt_templates import PromptRenderError, PromptTemplateEngine


@dataclass(frozen=True)
class PromptRenderer:
    context_composer: PromptContextComposer = field(
        default_factory=PromptContextComposer
    )

    def render(
        self,
        *,
        system_prompt: str,
        context: AgentExecutionContext,
        registry: PromptRegistry,
        template: PromptTemplate,
        mode_rules: str,
    ) -> str:
        context_payload = self.context_composer.payload(context)
        _validate_required_context(template, context_payload)
        serialized_context = json.dumps(
            context_payload,
            ensure_ascii=False,
            indent=2,
        )
        role_hint = _role_hint(context).strip()
        variables = {
            "system_prompt": system_prompt.strip(),
            "context_json": serialized_context,
            "role_hint": role_hint,
            "mode_rules": mode_rules.strip(),
        }
        engine = PromptTemplateEngine(registry.root)
        sections = [
            engine.render_file(registry.section_path(section), variables)
            for section in template.sections
        ]
        blocks = [
            system_prompt.strip(),
            "Contexto actual del cliente:\n" + serialized_context,
            role_hint,
            *sections,
        ]
        return "\n\n".join(block for block in blocks if block).rstrip()


def _role_hint(context: AgentExecutionContext) -> str:
    role_hint = ""
    agent_role = context.agent_role
    role_directive = context.role_directive
    if isinstance(agent_role, str) and agent_role:
        role_hint += f"Rol actual del agente: {agent_role}.\n"
    if isinstance(role_directive, str) and role_directive:
        role_hint += f"Directiva del rol:\n{role_directive}\n"
    return role_hint


def _validate_required_context(
    template: PromptTemplate,
    context_payload: dict[str, object],
) -> None:
    missing = [
        key
        for key in template.required_context
        if context_payload.get(key) in (None, {}, [])
    ]
    if missing:
        raise PromptRenderError(
            f"Contexto requerido ausente para {template.id}: {', '.join(missing)}"
        )
