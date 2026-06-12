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

Objetivo: convertir procedimientos repetibles en capacidades versionadas.

Parcialmente cubierto por subagentes Markdown, pero no por un sistema completo
de skills.

Pendiente:

- Carpeta `skills/` con formato `SKILL.md`.
- Comandos `skills list|show|create|install`.
- Carga explicita por CLI: `--skill <name>`.
- Slash commands `/skills` y `/skill <name>`.
- Memoria de preferencias por proyecto y usuario.
- Busqueda de memoria sin exponer secretos.

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
