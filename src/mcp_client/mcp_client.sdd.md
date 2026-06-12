# MCP Client SDD

## Purpose

`src/mcp_client` es el cliente local para usuarios y agentes. Construye la
configuracion, expone CLI/REPL, conecta con `mcp_server`, registra el runtime
local de tools, persiste sesiones de usuario y ejecuta flujos agenticos hasta
producir una respuesta final.

Debe permitir trabajo interactivo y no interactivo con trazabilidad opcional:
cada prompt puede derivar en mensajes, tool calls, autowrite, roles
planner-worker-reviewer, subagentes, sesiones reanudables y captura SQLite para
datasets.

## Owns

- CLI de usuario: `info`, `health`, `list-nodes`, `list-tools`,
  `list-prompts`, `doctor`, `setup`, `ask`, `repl`, `sessions`, `cache`,
  `export-dataset`.
- Configuracion de cliente: URL/token del servidor, streaming, max steps,
  salida rich/plain, output mode, planning mode, trazas, sesiones, KV cache,
  contexto y autowrite.
- Transporte hacia `mcp_server` mediante `MCPOrchestratorAPI`.
- Ciclo agentico basico: pedir turno, ejecutar tool calls, agregar resultados y
  cerrar.
- Routing directo/team y prompt de clasificacion.
- Flujo planner-worker-reviewer y politicas de acceso por rol.
- Seleccion dinamica de tools con `request_tools`.
- Delegacion a subagentes con `delegate_agent`.
- Subagentes built-in y carga desde `~/.mcp_agents` / `<base_dir>/.mcp_agents`.
- REPL, slash commands, hotkeys, preguntas del agente y objetivos de consola.
- Persistencia de sesiones de usuario en SQLite separada de trazas.
- Autowrite de codigo Markdown cuando `auto_write_code` esta activo.
- Captura y exportacion de trazas SQLite/JSONL.
- KV cache SQLite local con comandos CLI y slash commands.

## Does Not Own

- Implementacion interna de tools locales. Pertenece a `src/mcp`.
- Routing, discovery o llamadas directas a Ollama. Pertenecen a
  `src/mcp_server`.
- Prompt registry del servidor y render del system prompt final. Pertenece a
  `src/mcp_server` y `prompts/`.
- Politicas de sandbox web y proxy. Pertenecen a `src/mcp`.
- Contratos base `ChatRequest`, `ChatResponse`, `ChatMessage`, `ToolCall` y
  `AgentExecutionContext`. Pertenecen a `src/mcp_shared`.

## Public Interfaces

CLI:

- `python -m src.mcp_client.commands.cli info`
- `python -m src.mcp_client.commands.cli health`
- `python -m src.mcp_client.commands.cli list-nodes`
- `python -m src.mcp_client.commands.cli list-tools`
- `python -m src.mcp_client.commands.cli list-prompts`
- `python -m src.mcp_client.commands.cli doctor`
- `python -m src.mcp_client.commands.cli setup`
- `python -m src.mcp_client.commands.cli ask [--new-session|--session <id>] "<prompt>"`
- `python -m src.mcp_client.commands.cli repl [--continue|--session <id>]`
- `python -m src.mcp_client.commands.cli sessions list|show|rename|close`
- `python -m src.mcp_client.commands.cli cache get|set|delete|list|clear`
- `python -m src.mcp_client.commands.cli export-dataset --output <file.jsonl>`

Console script:

- `rag-agent = "src.mcp_client.commands.cli:main"`

Configuracion publica:

- `--server-url`, `--server-bearer-token`, `--client-name`, `--client-version`
- `--max-steps`, `--request-timeout`, `--no-stream`, `--show-thinking`
- `--no-auto-write-code`, `--plain-output`
- `--output-mode minimal|normal|debug`
- `--planning-mode auto|always|never`, `--no-orchestrate-agents`
- `--planner-max-steps`, `--reviewer-max-steps`, `--review-retries`
- `--trace-db-path`, `--trace-capture off|metadata|full`
- `--trace-thinking off|summary|raw`
- `--allow-remote-sensitive-tracing`
- `--session-db-path`
- `--kv-cache-db-path`, `--no-kv-cache`
- `--context-window-tokens`, `--show-context-meter`, `--no-context-meter`

Variables de entorno:

- `MCP_SERVER_URL`
- `MCP_SERVER_BEARER_TOKEN`
- `MCP_CLIENT_NAME`
- `MCP_CLIENT_VERSION`
- `MCP_CLIENT_MAX_STEPS`
- `MCP_CLIENT_REQUEST_TIMEOUT`
- `MCP_CLIENT_STREAM_RESPONSES`
- `MCP_CLIENT_SHOW_THINKING`
- `MCP_CLIENT_AUTO_WRITE_CODE`
- `MCP_CLIENT_RICH_OUTPUT`
- `MCP_CLIENT_OUTPUT_MODE`
- `MCP_CLIENT_ORCHESTRATE_AGENTS`
- `MCP_CLIENT_PLANNING_MODE`
- `MCP_CLIENT_PLANNER_MAX_STEPS`
- `MCP_CLIENT_REVIEWER_MAX_STEPS`
- `MCP_CLIENT_REVIEW_RETRIES`
- `MCP_CLIENT_TRACE_CAPTURE`
- `MCP_CLIENT_TRACE_THINKING`
- `MCP_CLIENT_TRACE_DB_PATH`
- `MCP_TRACE_CAPTURE`
- `MCP_TRACE_THINKING`
- `MCP_TRACE_DB_PATH`
- `MCP_CLIENT_ALLOW_REMOTE_SENSITIVE_TRACING`
- `MCP_CLIENT_SESSION_DB_PATH`
- `MCP_CLIENT_AUTO_SESSION_TITLE`
- `MCP_CLIENT_KV_CACHE_DB_PATH`
- `MCP_CLIENT_KV_CACHE_ENABLED`
- `MCP_CLIENT_CONTEXT_WINDOW_TOKENS`
- `MCP_CLIENT_SHOW_CONTEXT_METER`

Slash commands principales:

- `/help`, `/info`, `/health`, `/tools`, `/prompts`, `/perms`, `/status`
- `/mode [auto|direct|team]`
- `/thinking [on|off|toggle]`
- `/questions [auto|manual|toggle|status]`
- `/output [minimal|normal|debug]`
- `/session list|resume|new|save|compact` con aliases legacy
- `/cache get|set|list`
- `/pwd`, `/ls`, `/tree`, `/read`, `/head`, `/find`, `/files`
- `/clear`, `/exit`

Salida de `ask`:

- JSON con `final`, `steps`, `auto_written_files` y `session_id` cuando aplica.

Persistencia:

- Sesiones: `.mcp_sessions/client_sessions.sqlite`
- KV cache: `.mcp_cache/kv_cache.sqlite`
- Trazas: `.mcp_traces/agent_traces.sqlite` si trace esta activo.

## Architecture

- `app/`: composicion del cliente, lifecycle, sesiones publicas y KV cache.
- `commands/`: parser, dispatch y entrypoint CLI real.
- `config/`: modelo, loader y argumentos.
- `transport/`: API HTTP hacia `mcp_server`.
- `sessions/`: `AgentSession`, `REPLSession`, controller y store SQLite.
- `console/`: input, hotkeys, preguntas, objetivos y ciclo REPL moderno.
- `presentation/`: politicas y formatters de salida.
- `render/`: renderer terminal y renderer nulo.
- `slash/`: lexer, parser, router, completion y handlers.
- `agentic/`: workflow, turns, roles, policies, team, subagentes y trace store.
- `workflows/`: registry/fachada para elegir flujo.
- `integrations/`: cache, ejecucion, estado y lifecycle.
- `autowrite/`: Markdown code blocks e inferencia de rutas.
- `prompts/`: prompts cliente para routing y compactacion.

## Behavior Rules

- `ask` debe unir todos los argumentos del prompt preservando espacios.
- `planning-mode never` desactiva planner-worker-reviewer; `always` lo fuerza;
  `auto` decide mediante router.
- El ciclo agentico debe continuar mientras el asistente emita tool calls y no
  exceda `max_steps`.
- Si se alcanza `max_steps`, el cliente debe pedir cierre final sin tools y
  fallar si el modelo insiste en emitir tool calls.
- El cliente no debe inventar resultados de tools.
- Planner y compact no deben ejecutar tools.
- Worker puede activar tools adicionales con `request_tools` sin replantear el
  flujo desde cero.
- Worker puede delegar con `delegate_agent`; subagentes no deben delegar de
  nuevo salvo opt-in explicito.
- Reviewer debe validar con lectura y usar resultados reales de tools.
- Autowrite solo escribe cuando hay bloques Markdown, una solicitud de escritura
  y una ruta inferible.
- Render terminal muestra Markdown, colores, context meter y thinking solo segun
  configuracion.
- Preguntas del agente pueden resolverse manualmente o con auto-answer
  conservador.
- La captura de trazas debe respetar `trace_capture` y `trace_thinking`.
- `trace_capture=full` y `trace_thinking=raw` contra servidor no loopback
  requieren `allow_remote_sensitive_tracing`.
- `export-dataset` debe usar `--db-path`, luego `--trace-db-path`, luego el
  path por defecto si aplica.
- `ask --new-session` crea sesion, ejecuta prompt y guarda conversacion.
- `ask --session <id>` carga mensajes previos, ejecuta prompt y reemplaza la
  conversacion persistida por el estado final.
- `repl --continue` abre la sesion activa mas reciente no cerrada.
- `/clear` limpia memoria del REPL; una sesion activa solo se sobrescribe cuando
  se guarda o termina un prompt.
- `doctor` reporta checks de servidor, base_dir, permisos, DB de sesiones y KV.
- `setup` crea directorios/SQLite locales sin activar permisos peligrosos.

## Security And Permissions

- El cliente hereda la configuracion del runtime local y no debe saltarse
  `PermissionPolicy`.
- Si el servidor usa Bearer auth, el cliente debe enviar
  `Authorization: Bearer <token>`.
- Autowrite no debe escribir fuera de permisos activos del runtime.
- Planner no recibe tools; reviewer debe recibir solo lectura.
- El worker corre sandbox-first salvo instruccion explicita del usuario para
  usar host.
- `thinking` puede ser sensible; solo se muestra o persiste segun configuracion.
- Trazas `full`, sesiones y KV cache pueden contener datos sensibles.
- Namespaces KV reservados como secrets/auth/tokens/credentials deben
  rechazarse.
- Las sesiones no deben persistir `thinking`.

## Failure Modes

- URL invalida de servidor: error de configuracion antes de llamadas HTTP.
- Error HTTP o timeout del orquestador: mensaje util sin ocultar fallo remoto.
- Tool call invalido: registrar resultado como error de tool y permitir
  correccion si quedan pasos.
- Limite de pasos agotado y cierre con mas tool calls: `RuntimeError`.
- Export dataset con SQLite inexistente o invalido: error claro desde trace
  store.
- Sesion inexistente: fallar antes de llamar al modelo.
- Error durante `ask` con sesion activa: guardar prompt de usuario y metadata
  de error sin cerrar sesion.
- Subagente desconocido: devolver error con catalogo disponible.
- Tool inactiva en `SelectableToolRuntimeView`: indicar que use
  `request_tools`.

## Agent Instructions

- Antes de tocar `src/mcp_client`, leer este archivo.
- Si se modifica CLI/config, actualizar README/docs cuando cambie el uso
  publico.
- Si se modifica planner-worker-reviewer, revisar `agentic/team/`,
  `roles.py`, `policies.py` y pruebas de team/subagentes.
- Si se modifica el ciclo de tool calls, revisar `agentic/workflow.py`,
  `turns.py`, `integrations/execution.py` y pruebas de tool guard.
- Si se modifica trazabilidad, actualizar `docs/trazabilidad_dataset_sqlite.md`.
- Si se modifica persistencia de sesiones o slash commands, actualizar README y
  esta spec.

## Acceptance Criteria

- Comandos CLI existentes conservan nombre, argumentos y forma de salida salvo
  cambio documentado.
- Flujos directo y team terminan con respuesta final o error explicito.
- Resultados de tools quedan en memoria conversacional antes de la siguiente
  llamada al modelo.
- Autowrite devuelve rutas escritas en `auto_written_files`.
- Trazas exportables siguen generando JSONL valido.
- Sesiones pueden crearse, listarse, reanudarse, renombrarse, cerrarse y
  mostrarse desde CLI.
- REPL puede crear, guardar, compactar y reanudar sesiones con slash commands.
- `thinking` no aparece en mensajes persistidos en sesiones.
- Subagentes cargados desde Markdown validan frontmatter y tool access.

## Test Map

- Prompting/consola:
  - `tests/test_console_and_prompts.py`
  - `tests/test_prompt_context_slimming.py`
  - `tests/test_console_objectives.py`
- Routing y roles:
  - `tests/test_routing_media.py`
  - `tests/test_team_prompt_and_tool_guard.py`
  - `tests/test_worker_execute_policy.py`
- Subagentes y tools dinamicas:
  - `tests/test_subagents.py`
- Slash/REPL:
  - `tests/test_slash_submenus.py`
- Autowrite:
  - `tests/test_autowrite_markdown.py`

Comandos recomendados:

```powershell
python -m pytest tests/test_console_and_prompts.py tests/test_prompt_context_slimming.py tests/test_console_objectives.py
python -m pytest tests/test_routing_media.py tests/test_team_prompt_and_tool_guard.py tests/test_worker_execute_policy.py
python -m pytest tests/test_subagents.py tests/test_slash_submenus.py tests/test_autowrite_markdown.py
```
