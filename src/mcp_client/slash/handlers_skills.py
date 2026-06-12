from __future__ import annotations

from .models import CommandContext, CommandResult


def handle_skills_list(ctx: CommandContext, args: list[str]) -> CommandResult:
    catalog = ctx.client.list_skills()
    if not catalog:
        ctx.renderer.print_line("No hay skills disponibles. Crea archivos .md en ~/.mcp_skills/ o <proyecto>/.mcp_skills/")
        return CommandResult()
    active = getattr(ctx.client, "active_skill", None)
    lines = []
    for entry in catalog:
        name = entry.get("name", "")
        desc = entry.get("description", "")
        scope = entry.get("scope", "all")
        marker = " [activo]" if name == active else ""
        lines.append(f"  {name}{marker}  ({scope})  — {desc}")
    ctx.renderer.print_line("\n".join(lines))
    return CommandResult()


def handle_skill_show(ctx: CommandContext, args: list[str]) -> CommandResult:
    if not args:
        raise ValueError("Uso: /skill show <nombre>")
    name = args[0]
    skill = ctx.client.skill_registry.get(name)
    if skill is None:
        raise ValueError(f"Skill desconocido: '{name}'. Usa /skills list para ver disponibles.")
    lines = [
        f"name: {skill.name}",
        f"description: {skill.description}",
        f"scope: {skill.scope}",
    ]
    if skill.tags:
        lines.append(f"tags: {', '.join(skill.tags)}")
    if skill.version:
        lines.append(f"version: {skill.version}")
    lines.append(f"source: {skill.source}")
    lines.append("")
    lines.append(skill.directive)
    ctx.renderer.print_line("\n".join(lines))
    return CommandResult()


def handle_skill_activate(ctx: CommandContext, args: list[str]) -> CommandResult:
    if not args:
        raise ValueError("Uso: /skill activate <nombre>")
    name = args[0]
    ctx.client.activate_skill(name)
    ctx.renderer.print_line(f"Skill '{name}' activado. Aplica al próximo turno del agente.")
    return CommandResult()


def handle_skill_deactivate(ctx: CommandContext, args: list[str]) -> CommandResult:
    was_active = getattr(ctx.client, "active_skill", None)
    ctx.client.deactivate_skill()
    if was_active:
        ctx.renderer.print_line(f"Skill '{was_active}' desactivado.")
    else:
        ctx.renderer.print_line("No había ningún skill activo.")
    return CommandResult()
