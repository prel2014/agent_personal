# Roadmap Hermes-Level CLI

## Estado Actual

El repo ya tiene una base fuerte para agentes locales:

- Cliente CLI/REPL con slash commands, autocomplete y streaming.
- Orquestador HTTP hacia nodos Ollama locales/remotos.
- Runtime local de tools con permisos, auditoria y sandbox web.
- Flujo planner-worker-reviewer.
- Trazas SQLite exportables para datasets.
- Sesiones persistentes SQLite para UX de usuario.

## Hito 1: CLI Producto

Implementado como primer paso:

- `setup` y `doctor`.
- `rag-agent` como console script.
- `sessions list|show|rename|close`.
- `ask --new-session` y `ask --session <id>`.
- `repl --session <id>` y `repl --continue`.
- Slash commands: `/sessions`, `/resume`, `/new`, `/save`, `/status`.
- SQLite de sesiones separado de trazas en `.mcp_sessions/client_sessions.sqlite`.

## Hito 2: Skills Y Memoria

Objetivo: convertir procedimientos repetibles en capacidades versionadas.

- Carpeta `skills/` con formato `SKILL.md`.
- Comandos `skills list|show|create|install`.
- Carga explicita por CLI: `--skill <name>`.
- Slash commands `/skills` y `/skill <name>`.
- Memoria de preferencias por proyecto y usuario.
- Busqueda de memoria sin exponer secretos.

## Hito 3: Multi-Provider

Objetivo: mantener Ollama como provider local, pero permitir otros backends.

- Interfaz `ModelProvider`.
- Providers: Ollama, OpenAI-compatible y OpenRouter.
- `model list`, `model set`, `model test`.
- Routing por rol, contexto, latencia y disponibilidad.
- Configuracion por perfil.

## Hito 4: Workflows Git Y Checkpoints

Objetivo: hacer cambios de codigo con control de riesgo.

- Crear worktree/branch por tarea.
- Checkpoint antes de editar.
- Diff resumido y diff completo.
- Rollback selectivo.
- Commit message generado.
- Modo review sobre cambios existentes.

## Hito 5: Background Jobs Y Subagentes

Objetivo: ejecutar tareas largas sin bloquear la sesion principal.

- `jobs list|show|cancel`.
- Slash command `/background <prompt>`.
- Sesiones de job con DB y logs separados.
- Subagentes con contexto propio.
- Recoleccion de resultados al volver al REPL.

## Hito 6: Gateways Y Scheduler

Objetivo: operar el agente fuera de la terminal.

- Gateway daemon.
- Adaptadores Telegram/Discord/Slack.
- Usuarios permitidos y scopes por workspace.
- Scheduler persistente con sintaxis natural controlada.
- Historial de ejecuciones, retry y reporte.

## Criterio De Producto

Cada hito debe cumplir:

- Spec SDD actualizada antes o junto al codigo.
- Tests focalizados y regresion del flujo agente.
- Permisos peligrosos opt-in.
- Datos persistidos documentados como sensibles cuando contengan prompts, outputs o rutas locales.
