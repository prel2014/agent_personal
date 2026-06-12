# Arquitectura Y Operacion Del Proyecto

## Vista General

El sistema separa tres responsabilidades:

- `mcp_client` mantiene la experiencia del usuario: CLI, REPL, sesiones,
  slash commands, workflows, subagentes, autowrite, trazas y salida de terminal.
- `mcp_server` recibe requests HTTP, construye el prompt final, elige el nodo
  Ollama y devuelve respuestas bloqueantes o streaming NDJSON.
- `mcp` ejecuta tools locales dentro de una politica de permisos, rutas
  protegidas y auditoria.

El servidor no ejecuta tools ni toca el filesystem del usuario. Las tools se
ejecutan en el cliente contra `base_dir`.

## Flujo De Un Prompt

1. El usuario llama `ask` o escribe en el REPL.
2. El cliente decide ruta directa o equipo segun `planning_mode`.
3. El runtime expone tools permitidas y contexto compacto del proyecto.
4. El servidor renderiza el prompt usando `prompts/registry.json` si existe.
5. El servidor selecciona nodo Ollama por rol, prioridad, disponibilidad y
   fallback local.
6. El cliente procesa tool calls reales, agrega resultados y repite hasta la
   respuesta final o `max_steps`.
7. Si aplica, autowrite escribe bloques Markdown inferidos, sesiones guardan
   mensajes sin `thinking` y trazas guardan eventos segun configuracion.

## Paquetes

- `src/mcp_client/app`: composicion del cliente y operaciones publicas.
- `src/mcp_client/commands`: parser y dispatch del CLI.
- `src/mcp_client/console`: entrada interactiva, hotkeys, preguntas y objetivos.
- `src/mcp_client/slash`: router y handlers de slash commands.
- `src/mcp_client/agentic`: workflows, roles, policies, team, subagentes y
  trace store.
- `src/mcp_client/autowrite`: extraccion de codigo Markdown e inferencia de
  rutas.
- `src/mcp_server/server`: HTTP, streaming y servicio.
- `src/mcp_server/ollama`: cliente Ollama, prompt builder, registry y reglas.
- `src/mcp_server/nodes`: config de nodos, discovery, auto-promocion y routing.
- `src/mcp/runtime`: normalizacion de argumentos, perfil de proyecto, runtime y
  composicion de tool registry.
- `src/mcp/tools/helpers`: tools de sistema, codigo, Git, KV, hardware, web y
  datos.
- `src/mcp/sandbox`: modelos, manager, backend Docker/local, proxy, worker y
  operaciones web.
- `src/mcp_shared`: contratos wire, URLs, entorno, SQLite, Markdown y storage.

## Interfaces Publicas

Cliente:

```powershell
python -m src.mcp_client.commands.cli info
python -m src.mcp_client.commands.cli health
python -m src.mcp_client.commands.cli list-nodes
python -m src.mcp_client.commands.cli list-tools
python -m src.mcp_client.commands.cli list-prompts
python -m src.mcp_client.commands.cli doctor
python -m src.mcp_client.commands.cli setup
python -m src.mcp_client.commands.cli ask "prompt"
python -m src.mcp_client.commands.cli repl --continue
python -m src.mcp_client.commands.cli sessions list
python -m src.mcp_client.commands.cli cache list
python -m src.mcp_client.commands.cli export-dataset --output salida.jsonl
```

Servidor:

```powershell
python -m src.mcp_server.server.cli --host 127.0.0.1 --port 8000
```

Runtime local:

```powershell
python -m src.mcp.server info
python -m src.mcp.server list-tools
python -m src.mcp.server call-tool readfile --arguments '{"path":"README.md"}'
```

Endpoints HTTP:

- `GET /health`
- `GET /info`
- `GET /nodes`
- `POST /v1/chat`

## Configuracion Principal

Cliente:

- `--server-url` / `MCP_SERVER_URL`
- `--server-bearer-token` / `MCP_SERVER_BEARER_TOKEN`
- `--planning-mode auto|always|never` / `MCP_CLIENT_PLANNING_MODE`
- `--max-steps` / `MCP_CLIENT_MAX_STEPS`
- `--output-mode minimal|normal|debug` / `MCP_CLIENT_OUTPUT_MODE`
- `--session-db-path` / `MCP_CLIENT_SESSION_DB_PATH`
- `--trace-capture off|metadata|full` / `MCP_CLIENT_TRACE_CAPTURE`
- `--trace-thinking off|summary|raw` / `MCP_CLIENT_TRACE_THINKING`
- `--kv-cache-db-path` / `MCP_CLIENT_KV_CACHE_DB_PATH`
- `--context-window-tokens` / `MCP_CLIENT_CONTEXT_WINDOW_TOKENS`

Servidor:

- `--host`, `--port`
- `--auth-mode off|bearer_static`
- `--auth-static-tokens` / `MCP_SERVER_AUTH_TOKENS`
- `--ollama-base-url` / `OLLAMA_BASE_URL`
- `--model` / `OLLAMA_MODEL`
- `--nodes-config` / `MCP_SERVER_NODES_CONFIG`
- `--discover-nodes` / `MCP_SERVER_DISCOVERY_ENABLED`
- `--auto-promote-discovered-nodes` /
  `MCP_SERVER_AUTO_PROMOTE_DISCOVERED_NODES`

Runtime:

- `--base-dir` / `MCP_BASE_DIR`
- `--read-only`, `--deny-read`, `--deny-write`, `--deny-execute`
- `--allow-delete`, `--allow-hardware`, `--allow-media-input`, `--allow-web`
- `--allow-sandbox-execute`
- `--protected-paths`, `--protected-read-paths`
- `--allowed-tools`, `--blocked-tools`
- `--tool-confirmation-mode sensitive`

## Prompting

`prompts/registry.json` define templates por modo. Cada template referencia
secciones Markdown en:

- `prompts/system`
- `prompts/context`
- `prompts/modes`

El builder del servidor intenta renderizar desde el registry. Si el registry no
existe o falla, cae al builder legacy de `PromptRuleSet`.

El contexto que llega al prompt se compone desde providers:

- runtime, permisos, sandbox, media y tooling
- tools activas y categorias
- catalogo de subagentes
- reglas de seguridad para tools no confiables y confirmaciones

## Subagentes

Subagentes built-in:

- `planner`
- `worker`
- `reviewer`
- `file-inspector`
- `code-reviewer`
- `test-runner`

Tambien se pueden definir archivos Markdown en `~/.mcp_agents` o
`<base_dir>/.mcp_agents` con frontmatter:

```markdown
---
name: auditor
description: Revisa riesgos de seguridad.
tool_access: read_only
tools: [pwd, listdir, readfile, search_code]
---
Eres auditor. Revisa solo evidencia concreta y reporta hallazgos accionables.
```

`tool_access` acepta `none`, `read_only` o `full`. Si `tools` esta presente,
limita el catalogo a esos nombres.

## Persistencia Local

- Sesiones: `.mcp_sessions/client_sessions.sqlite`
- KV cache: `.mcp_cache/kv_cache.sqlite`
- Trazas: `.mcp_traces/agent_traces.sqlite` cuando `trace_capture` esta activo.
- Sandbox: `.mcp_sandbox/sessions/<id>` para requests/responses temporales.

Estos archivos pueden contener prompts, rutas locales, outputs o informacion
sensible y no deben commitearse.

## Validacion

Suite completa:

```powershell
python -m pytest
```

En Windows, si pytest intenta cargar plugins globales incompatibles, ejecuta:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
python -m pytest --basetemp C:\tmp\pytest-rag
```

Validaciones enfocadas actuales:

```powershell
python -m pytest tests/test_console_and_prompts.py tests/test_prompt_context_slimming.py
python -m pytest tests/test_subagents.py tests/test_worker_execute_policy.py
python -m pytest tests/test_runtime_execute_defaults.py tests/test_data_tools.py
python -m pytest tests/test_slash_submenus.py tests/test_autowrite_markdown.py
```

Si se cambia discovery/routing Ollama, agregar o actualizar pruebas porque el
checkout actual no conserva una suite especifica de nodos HTTP.
