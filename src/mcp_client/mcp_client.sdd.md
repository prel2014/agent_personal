# MCP Client SDD

## Purpose

`src/mcp_client` es el cliente local para usuarios y agentes. Construye la
configuracion, expone CLI/REPL, conecta con `mcp_server`, registra el runtime
local de tools, persiste sesiones de usuario y ejecuta el ciclo agentico hasta
producir una respuesta final.

El cliente debe permitir trabajo interactivo y no interactivo sin perder
trazabilidad: cada prompt puede derivar en mensajes, tool calls, autowrite,
roles planner-worker-reviewer, sesiones reanudables y captura SQLite para
datasets.

## Owns

- CLI de usuario: `info`, `health`, `list-nodes`, `list-tools`, `list-prompts`, `doctor`, `setup`, `ask`, `repl`, `sessions`, `export-dataset`.
- Configuracion de cliente: URL del servidor, streaming, max steps, salida rich/plain, planning mode, trazas, sesiones y autowrite.
- Transporte hacia `mcp_server` mediante `MCPOrchestratorAPI`.
- Flujos de sesion: `AgentSession`, `REPLSession`, comandos slash y renderizado terminal.
- Persistencia de sesiones de usuario en SQLite separada de trazas.
- Ciclo agentico basico: pedir turno al modelo, ejecutar tool calls, agregar resultados y cerrar.
- Flujo planner-worker-reviewer y politicas de acceso por rol.
- Autowrite de codigo devuelto por el asistente cuando `auto_write_code` esta activo.
- Captura y exportacion de trazas SQLite/JSONL.
- KV cache SQLite local con comandos CLI y slash commands.

## Does Not Own

- Implementacion interna de tools locales. Pertenece a `src/mcp`.
- Routing, discovery o llamadas directas a Ollama. Pertenecen a `src/mcp_server`.
- Politicas de sandbox web y proxy. Pertenecen a `src/mcp`.
- El formato base de `ChatRequest`, `ChatResponse`, `ChatMessage` y `ToolCall`. Pertenece a `src/mcp_shared`.

## Public Interfaces

- CLI:
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
- Configuracion publica:
  - `--server-url`, `--server-bearer-token`, `--client-name`, `--client-version`
  - `--max-steps`, `--request-timeout`, `--no-stream`, `--show-thinking`
  - `--no-auto-write-code`, `--plain-output`
  - `--planning-mode auto|always|never`, `--no-orchestrate-agents`
  - `--planner-max-steps`, `--reviewer-max-steps`, `--review-retries`
  - `--trace-db-path`, `--trace-capture off|metadata|full`, `--trace-thinking off|summary|raw`
  - `--allow-remote-sensitive-tracing`
  - `--session-db-path`
  - `--kv-cache-db-path`, `--no-kv-cache`
  - `--context-window-tokens`, `--no-context-meter`
- Variables de entorno equivalentes:
  - `MCP_SERVER_URL`
  - `MCP_SERVER_BEARER_TOKEN`
  - `MCP_CLIENT_MAX_STEPS`
  - `MCP_CLIENT_STREAM_RESPONSES`
  - `MCP_CLIENT_SHOW_THINKING`
  - `MCP_CLIENT_AUTO_WRITE_CODE`
  - `MCP_CLIENT_PLANNING_MODE`
  - `MCP_CLIENT_TRACE_CAPTURE`
  - `MCP_CLIENT_TRACE_THINKING`
  - `MCP_CLIENT_TRACE_DB_PATH`
  - `MCP_CLIENT_ALLOW_REMOTE_SENSITIVE_TRACING`
  - `MCP_TRACE_CAPTURE`
  - `MCP_TRACE_DB_PATH`
  - `MCP_CLIENT_SESSION_DB_PATH`
  - `MCP_CLIENT_KV_CACHE_DB_PATH`
  - `MCP_CLIENT_KV_CACHE_ENABLED`
  - `MCP_CLIENT_CONTEXT_WINDOW_TOKENS`
  - `MCP_CLIENT_SHOW_CONTEXT_METER`
- Salida de `ask`: JSON con `final`, `steps`, `auto_written_files` y `session_id` cuando aplica.
- Export JSONL: ejemplos derivados desde SQLite por `SQLiteTraceStore.export_dataset_jsonl`.
- Sesiones SQLite:
  - DB por defecto: `.mcp_sessions/client_sessions.sqlite`
  - Tablas: `sessions` y `session_messages`
  - Mensajes persistidos sin `thinking`
- KV cache SQLite:
  - DB por defecto: `.mcp_cache/kv_cache.sqlite`
  - Tabla: `kv_entries`
  - Clave primaria: `(namespace, key)`
- Console script instalable: `rag-agent = "src.mcp_client.commands.cli:main"`.

Arquitectura de paquetes:

- `app/`: composicion del cliente, lifecycle, sesiones publicas y KV cache.
- `commands/`: parser, dispatch y entrypoint CLI real.
- `config/`, `transport/`, `sessions/`, `agentic/`, `render/`, `slash/`, `autowrite/`: dominios internos.
- La raiz del paquete solo conserva `__init__.py`; no debe crecer con fachadas de compatibilidad.

## Behavior Rules

- `ask` debe convertir todos los argumentos del prompt en un unico string preservando espacios entre tokens.
- El ciclo agentico debe continuar mientras el asistente emita tool calls y no exceda `max_steps`.
- Si el asistente deja de emitir tool calls, el cliente debe ejecutar autowrite y devolver respuesta final.
- Si se alcanza `max_steps`, el cliente debe pedir un cierre final sin tools y fallar si el modelo insiste en emitir tool calls.
- `planning-mode never` desactiva planner-worker-reviewer; `always` lo fuerza; `auto` decide mediante el router existente.
- El cliente no debe inventar resultados de tools. Solo debe agregar a la conversacion resultados devueltos por `ToolCallProcessor`.
- El render terminal puede mostrar Markdown, colores y thinking solo segun configuracion.
- La captura de trazas debe respetar `trace_capture` y `trace_thinking`; `off` no debe persistir contenido.
- `trace_capture=full` y `trace_thinking=raw` contra un servidor no loopback requieren `allow_remote_sensitive_tracing`.
- `export-dataset` debe usar `--db-path`, luego `--trace-db-path`, luego el path por defecto si aplica.
- `ask --new-session` debe crear sesion, ejecutar el prompt y guardar la conversacion completa.
- `ask --session <id>` debe cargar mensajes previos, ejecutar el prompt y reemplazar la conversacion persistida por el estado final.
- `repl --continue` debe abrir la sesion activa mas reciente no cerrada.
- `/clear` limpia el buffer conversacional en memoria; una sesion activa solo se sobrescribe cuando se guarda o termina un prompt.
- `doctor` debe reportar checks de DB de sesiones, base_dir, permisos y servidor.
- `doctor` debe reportar estado del KV cache cuando este habilitado.
- `setup` debe crear directorios/SQLite locales sin activar permisos peligrosos, incluido KV si esta habilitado.
- Antes de cada request al modelo, el cliente debe poder mostrar un medidor estimado de tokens usados contra `context_window_tokens`.

## Security And Permissions

- El cliente hereda la configuracion del runtime local y no debe saltarse `PermissionPolicy`.
- Si el servidor HTTP usa Bearer auth, el cliente debe enviar `Authorization: Bearer <token>` cuando `server_bearer_token` este configurado.
- Autowrite no debe escribir fuera de los permisos activos del runtime.
- Los roles agenticos deben mantener su politica de tools: planner y reviewer no deben obtener permisos de escritura por accidente.
- El campo `thinking` puede ser sensible; solo se muestra o persiste segun configuracion explicita.
- Las trazas en modo `full` deben tratarse como datos de desarrollo sensibles porque pueden contener prompts, outputs y rutas locales.
- La DB de sesiones tambien es sensible porque contiene prompts, outputs y rutas locales.
- El KV cache puede contener datos sensibles por error; namespaces reservados como secrets/auth/tokens/credentials deben rechazarse.
- Las sesiones de usuario no deben persistir `thinking`; ese dato solo pertenece a trazas cuando `trace_thinking` lo permite.

## Failure Modes

- URL invalida de servidor: error de configuracion antes de iniciar llamadas HTTP.
- Error HTTP o timeout del orquestador: propagar mensaje util al usuario sin ocultar que fallo el servidor.
- Tool call invalido: registrar el resultado como error de tool y permitir que el modelo corrija si quedan pasos.
- Limite de pasos agotado y cierre con mas tool calls: lanzar `RuntimeError`.
- Export dataset con SQLite inexistente o invalido: fallar con error claro desde `SQLiteTraceStore`.
- Sesion inexistente: fallar con mensaje claro antes de llamar al modelo.
- Error durante `ask` con sesion activa: guardar el prompt de usuario y metadata de error sin cerrar la sesion.

## Agent Instructions

- Antes de tocar `src/mcp_client`, leer este archivo y `.specdd/bootstrap.md`.
- Si se modifica el ciclo de tool calls, revisar `src/mcp_client/agentic/workflow.py` y pruebas de workflow.
- Si se modifica planner-worker-reviewer, revisar `src/mcp_client/agentic/team.py`, `roles.py`, `policies.py` y pruebas de team/planning.
- Si se modifica CLI o config, actualizar README/docs cuando cambie el uso publico.
- Si se modifica trazabilidad, actualizar `docs/trazabilidad_dataset_sqlite.md` y pruebas de trace store.
- Si se modifica persistencia de sesiones, actualizar esta spec y `docs/hermes_level_cli_roadmap.md`.

## Acceptance Criteria

- Los comandos CLI existentes conservan nombre, argumentos y forma de salida salvo cambio documentado.
- El flujo directo y planner-worker-reviewer terminan con respuesta final o error explicito.
- Los resultados de tools quedan en memoria conversacional antes de la siguiente llamada al modelo.
- Autowrite devuelve rutas escritas en `auto_written_files`.
- Las trazas exportables siguen generando JSONL valido.
- Las sesiones pueden crearse, listarse, reanudarse, renombrarse, cerrarse y mostrarse desde CLI.
- REPL puede crear, guardar y reanudar sesiones con slash commands.
- `thinking` no aparece en mensajes persistidos en sesiones.

## Test Map

- Workflow y limite de tools:
  - `tests/test_agent_workflow.py`
  - `tests/test_agentic_refactor.py`
- Planner-worker-reviewer:
  - `tests/test_team_orchestrator.py`
  - `tests/test_planning_router.py`
- CLI/REPL/render:
  - `tests/test_slash_menu.py`
  - `tests/test_streaming_render.py`
  - `tests/test_repl_session_commands.py`
- Sesiones persistentes:
  - `tests/test_session_store.py`
  - `tests/test_client_sessions.py`
  - `tests/test_doctor_setup.py`
- Tool call compatibility:
  - `tests/test_tool_call_compat.py`
- Trazabilidad:
  - `tests/test_trace_store.py`
- KV cache:
  - `tests/test_kv_cache_store.py`
  - `tests/test_kv_cache_integration.py`

Comandos recomendados:

```powershell
python -m pytest tests/test_agent_workflow.py tests/test_team_orchestrator.py tests/test_trace_store.py
python -m pytest tests/test_planning_router.py tests/test_tool_call_compat.py tests/test_slash_menu.py
python -m pytest tests/test_session_store.py tests/test_client_sessions.py tests/test_repl_session_commands.py tests/test_doctor_setup.py
python -m pytest tests/test_kv_cache_store.py tests/test_kv_cache_integration.py
```
