# Fases De Refactor Del Cliente

Objetivo: hacer `mcp_client` expandible sin fragmentarlo en exceso. La
estructura actual separa composicion, workflows, interfaz interactiva,
subagentes e integraciones, manteniendo CLI estable.

## Fase 1. Motor De Workflows

- [x] Crear `workflows/` para composicion y ejecucion de flujos.
- [x] Mover decision de routing y orquestacion fuera de `sessions/agent.py`.
- [x] Mantener `AgentWorkflow` y `AgentTeamOrchestrator` detras de una fachada.
- [x] Cubrir routing directo/team con pruebas (`tests/test_routing_media.py`).

## Fase 2. Superficie Interactiva

- [x] Aislar el ciclo REPL para que no conozca detalles de composicion interna.
- [x] Mantener `slash/` como adaptador de comandos.
- [x] Definir puntos separados para preguntas, hotkeys, objetivos y streaming.
- [x] Agregar slash commands jerarquicos y compatibilidad con nombres legacy.

## Fase 3. Integraciones

- [x] Mantener transporte, renderizado, autowrite y trazas como adaptadores.
- [x] Agrupar cache, sesiones y lifecycle del cliente en `integrations/`.
- [x] Reducir imports cruzados entre `sessions/`, `app/` y `agentic/`.
- [x] Preparar reemplazo de adaptadores sin tocar workflows.

## Fase 4. Compatibilidad

- [x] Revisar reexports y aliases antiguos.
- [x] Retirar rutas viejas sin consumidores.
- [x] Consolidar contratos publicos finales en specs y README.

## Ajustes Posteriores Implementados

- [x] Planner sin tools: tool calls en fase sin tools se convierten en texto
  util y no se ejecutan.
- [x] Worker sandbox-first: las tools del worker quedan limitadas al sandbox por
  defecto y solo salen al host si el usuario lo pide explicitamente.
- [x] Contexto multiarchivo: tools de escritura/reemplazo devuelven preview,
  hash y tamanos del archivo final.
- [x] Streaming Markdown: salida rich acumula respuesta y renderiza Markdown al
  final del turno.
- [x] `thinking` apagado por defecto y alternable con `Ctrl+T` o `/thinking`.
- [x] Prompt registry fuera de handlers (`prompts/registry.json` y secciones
  Markdown).
- [x] Seleccion dinamica de tools con `request_tools`.
- [x] Subagentes built-in y custom con frontmatter Markdown.
- [x] Medidor de contexto configurable.
- [x] Modo de salida `minimal|normal|debug`.

## Archivos Clave

- `src/mcp_client/workflows/registry.py`
- `src/mcp_client/sessions/controller.py`
- `src/mcp_client/sessions/repl.py`
- `src/mcp_client/integrations/state.py`
- `src/mcp_client/integrations/execution.py`
- `src/mcp_client/app/client.py`
- `src/mcp_client/slash/registry.py`
- `src/mcp_client/agentic/team/factory.py`
- `src/mcp_client/agentic/subagents/`
- `src/mcp_client/prompts/`

## Pruebas Relevantes Actuales

- `tests/test_console_and_prompts.py`
- `tests/test_prompt_context_slimming.py`
- `tests/test_routing_media.py`
- `tests/test_slash_submenus.py`
- `tests/test_subagents.py`
- `tests/test_team_prompt_and_tool_guard.py`
- `tests/test_worker_execute_policy.py`
- `tests/test_autowrite_markdown.py`
