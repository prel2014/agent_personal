# Roadmap Hermes-Level CLI

## Estado Actual

La base actual ya incluye:

- Cliente CLI/REPL con slash commands jerarquicos, autocomplete y streaming.
- `rag-agent` como console script instalable.
- Orquestador HTTP hacia nodos Ollama locales/remotos.
- Auth Bearer para exponer el servidor fuera de loopback.
- Discovery LAN y auto-promocion opcional de nodos detectados.
- Runtime local con permisos, rutas protegidas, auditoria, KV cache, Git,
  datos, hardware/media y sandbox web.
- Flujo `planner -> worker -> reviewer`.
- Seleccion dinamica de tools con `request_tools`.
- Delegacion del worker a subagentes con `delegate_agent`.
- Subagentes built-in y carga desde `~/.mcp_agents` / `<base_dir>/.mcp_agents`.
- Prompt registry en `prompts/` con templates por modo.
- Sesiones persistentes SQLite.
- Trazas SQLite exportables a JSONL.
- Medidor de contexto y modos de salida `minimal|normal|debug`.

## Hito 1: CLI Producto

Implementado:

- `setup` y `doctor`.
- `sessions list|show|rename|close`.
- `ask --new-session` y `ask --session <id>`.
- `repl --session <id>` y `repl --continue`.
- Slash commands de sesiones: `/session list`, `/session resume`,
  `/session new`, `/session save`, `/session compact`.
- Slash commands de inspeccion: `/pwd`, `/ls`, `/tree`, `/read`, `/head`,
  `/find`, `/files`.
- KV cache CLI y slash commands.
- SQLite de sesiones separado de trazas.

Pendiente:

- Mejorar mensajes de error para configuraciones mixtas de server/runtime.
- Documentar recipes de uso por tipo de proyecto.

## Hito 2: Skills Y Memoria

Implementado:

- Carpeta `~/.mcp_skills/` y `<base_dir>/.mcp_skills/` con archivos `.md`
  como formato de skill (frontmatter YAML + directiva).
- CLI: `skills list`, `skills show <nombre>`.
- Flag `--skill <nombre>` para activar un skill desde el arranque.
- Slash commands `/skills`, `/skills list`, `/skill show <nombre>`,
  `/skill activate <nombre>`, `/skill off`.
- Memoria de proyecto (`<base_dir>/.mcp_memory/`) y de usuario
  (`~/.mcp_memory/`) persistidas en SQLite.
- CLI: `memory list|add|forget|search|clear` y
  `memory user add|forget`.
- Slash commands `/memory`, `/memory list`, `/memory add <clave> <valor>`,
  `/memory search <query>`, `/memory forget <clave>`,
  `/memory user add <clave> <valor>`, `/memory user forget <clave>`.
- Flag `--no-memory` para desactivar memoria en una sesion.
- Busqueda semantica opcional via embeddings (Ollama + `nomic-embed-text`).
- Memoria inyectada automaticamente en el contexto del agente.

Pendiente:

- Documentar recipes de uso de skills por tipo de proyecto.

## Hito 3: Multi-Provider

Objetivo: mantener Ollama como provider local y permitir otros backends.

Pendiente:

- Interfaz `ModelProvider`.
- Providers OpenAI-compatible y OpenRouter.
- `model list`, `model set`, `model test`.
- Routing por provider, rol, contexto, latencia y disponibilidad.
- Configuracion por perfil.

## Hito 4: Workflows Git Y Checkpoints

Objetivo: hacer cambios de codigo con control de riesgo.

Estado actual:

- Git expone tools de solo lectura (`git_status`, `git_diff`, `git_log`,
  `git_show`, `git_branches`, `git_blame`, `git_ls_files`).

Pendiente:

- Crear worktree/branch por tarea.
- Checkpoint antes de editar.
- Diff resumido y diff completo desde CLI.
- Rollback selectivo.
- Commit message generado.
- Modo review sobre cambios existentes.

## Hito 5: Background Jobs Y Subagentes

Estado actual:

- Subagentes built-in.
- Subagentes Markdown por proyecto/usuario.
- Delegacion desde worker con `delegate_agent`.
- Seleccion dinamica de tools por subagente.

Pendiente:

- `jobs list|show|cancel`.
- Slash command `/background <prompt>`.
- Sesiones de job con DB y logs separados.
- Ejecucion realmente asincrona sin bloquear REPL.
- Recoleccion de resultados al volver al REPL.

## Hito 6: Gateways Y Scheduler

Objetivo: operar el agente fuera de la terminal.

Pendiente:

- Gateway daemon.
- Adaptadores Telegram/Discord/Slack.
- Usuarios permitidos y scopes por workspace.
- Scheduler persistente con sintaxis natural controlada.
- Historial de ejecuciones, retry y reporte.

## Criterio De Producto

Cada hito debe cumplir:

- Spec SDD actualizada.
- Tests focalizados y regresion del flujo agente.
- Permisos peligrosos opt-in.
- Datos persistidos documentados como sensibles cuando contengan prompts,
  outputs o rutas locales.
- README/docs actualizados cuando cambie la experiencia publica.
