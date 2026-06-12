# RAG / MCP Orquestado Con Ollama

Este proyecto implementa un cliente local con tools, un orquestador HTTP y
soporte para usar varias maquinas con Ollama como nodos de razonamiento
distribuidos. El cliente conserva el acceso al workspace local; el servidor
solo enruta mensajes hacia Ollama y devuelve respuestas compatibles con el
cliente.

## Componentes

- `src/mcp_client`: CLI/REPL, sesiones, slash commands, workflows agenticos,
  subagentes, autowrite, trazas y renderizado de terminal.
- `src/mcp_server`: servidor HTTP, autenticacion, routing hacia nodos Ollama,
  discovery LAN, auto-promocion de nodos y construccion de prompts.
- `src/mcp`: runtime local de tools, permisos, politicas de ruta, auditoria,
  KV cache, Git, datos, hardware/media y sandbox web.
- `src/mcp_shared`: contratos compartidos, serializacion, helpers SQLite,
  Markdown, URLs y entorno.
- `prompts/`: registry y secciones Markdown usadas para construir prompts por
  modo (`tool_workflow`, `planner`, `reviewer`, `direct_answer`, `compact`).
- `examples/ollama_nodes.example.json`: ejemplo de nodos remotos por rol.

## Documentacion

- [Arquitectura Y Operacion Del Proyecto](docs/arquitectura_y_operacion.md)
- [Uso Del Orquestador Ollama Distribuido](docs/uso_orquestador_ollama_distribuido.md)
- [Trazabilidad SQLite Para Dataset](docs/trazabilidad_dataset_sqlite.md)
- [Specification-Driven Development Para Este Repo](docs/specification_driven_development.md)
- [Plan De Caja Aislada Para Tools Web](docs/plan_sandbox_web_tools.md)
- [Fases De Refactor Del Cliente](docs/mcp_client_refactor_phases.md)
- [Roadmap Hermes-Level CLI](docs/hermes_level_cli_roadmap.md)

Specs fuente-adjacent:

- `src/mcp_client/mcp_client.sdd.md`
- `src/mcp_server/mcp_server.sdd.md`
- `src/mcp/mcp_runtime.sdd.md`

## Instalacion

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

El paquete instala el entry point `rag-agent`, equivalente a
`python -m src.mcp_client.commands.cli`.

## Inicio Rapido

Servidor local:

```powershell
python -m src.mcp_server.server.cli `
  --host 127.0.0.1 `
  --port 8000 `
  --ollama-base-url http://127.0.0.1:11434 `
  --model auto
```

Servidor en LAN con Bearer token y nodos remotos:

```powershell
python -m src.mcp_server.server.cli `
  --host 0.0.0.0 `
  --port 8000 `
  --auth-mode bearer_static `
  --auth-static-tokens supersecreto `
  --nodes-config examples/ollama_nodes.example.json `
  --discover-nodes `
  --discovery-hosts 192.168.1.20,192.168.1.21
```

Cliente:

```powershell
python -m src.mcp_client.commands.cli setup
python -m src.mcp_client.commands.cli --server-bearer-token supersecreto doctor
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 list-nodes
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 ask "analiza este repo"
```

Con el entry point:

```powershell
rag-agent doctor
rag-agent repl --continue
```

## Flujo Agentico

El cliente puede responder directo o usar el equipo
`planner -> worker -> reviewer`, segun `--planning-mode`:

- `auto`: clasifica el prompt y decide.
- `always`: fuerza el equipo planner/worker/reviewer.
- `never`: responde directo sin equipo.

Roles principales:

- `planner`: no recibe tools; produce un plan breve.
- `worker`: ejecuta inspeccion/cambios con tools dinamicas y sandbox-first.
- `reviewer`: valida con tools de lectura.

El worker empieza con una seleccion pequena de tools y puede activar mas con
`request_tools`. Tambien puede delegar subtareas con `delegate_agent` a
subagentes built-in como `file-inspector`, `code-reviewer` y `test-runner`, o a
subagentes Markdown cargados desde `~/.mcp_agents` y `<base_dir>/.mcp_agents`.

## REPL Y Slash Commands

```powershell
python -m src.mcp_client.commands.cli repl --continue
```

Comandos utiles dentro del REPL:

- `/help`, `/info`, `/health`, `/status`, `/tools`, `/prompts`, `/perms`
- `/mode auto|direct|team`
- `/thinking on|off|toggle`
- `/questions auto|manual|toggle|status`
- `/output minimal|normal|debug`
- `/session list`, `/session resume <id>`, `/session new [titulo]`,
  `/session save [titulo]`, `/session compact [enfoque]`
- `/pwd`, `/ls`, `/tree`, `/read`, `/head`, `/find`, `/files`
- `/cache get|set|list`

## Sesiones, Cache Y Trazas

Sesiones persistentes:

```powershell
python -m src.mcp_client.commands.cli ask --new-session "analiza el repo"
python -m src.mcp_client.commands.cli sessions list
python -m src.mcp_client.commands.cli ask --session <session_id> "continua"
```

KV cache local:

```powershell
python -m src.mcp_client.commands.cli cache set repo last_scan "ok" --ttl-seconds 3600
python -m src.mcp_client.commands.cli cache get repo last_scan
python -m src.mcp_client.commands.cli cache list --namespace repo
python -m src.mcp_client.commands.cli cache clear --expired-only
```

Trazas SQLite para dataset:

```powershell
python -m src.mcp_client.commands.cli `
  --trace-capture full `
  --trace-db-path .mcp_traces/agent_traces.sqlite `
  ask "implementa una mejora"

python -m src.mcp_client.commands.cli export-dataset `
  --db-path .mcp_traces/agent_traces.sqlite `
  --output datasets/sft_conversation.jsonl
```

Contra servidores no loopback, `--trace-capture full` y
`--trace-thinking raw` requieren `--allow-remote-sensitive-tracing`.

## Permisos Y Seguridad

El runtime local aplica permisos antes de ejecutar cualquier tool:

- `--read-only` apaga write, execute, delete, hardware, media input, web y
  sandbox execute.
- `--deny-read`, `--deny-write`, `--deny-execute` reducen capacidades.
- `--allow-delete`, `--allow-hardware`, `--allow-media-input`, `--allow-web` y
  `--allow-sandbox-execute` son opt-in para capacidades de mayor riesgo.
- `--protected-paths` bloquea escritura/borrado en rutas sensibles.
- `--protected-read-paths` bloquea lectura e inspeccion recursiva de secretos.
- `--tool-confirmation-mode sensitive` exige aprobacion previa para tools
  sensibles no incluidas en `--approved-sensitive-tools`.

El servidor HTTP rechaza `--host` no loopback con `--auth-mode off`.

## Tools Web Aisladas

`web_search`, `web_fetch` y `sandbox_run` estan apagadas por defecto. Para
habilitar busqueda/fetch:

```powershell
python -m src.mcp.server `
  --allow-web `
  --sandbox-backend docker `
  --web-allowed-domains example.com `
  list-tools
```

El backend seguro esperado es Docker con imagen `mcp-sandbox:local`. Si la
imagen no existe, el runtime reporta el comando de build esperado:

```powershell
docker build -f docker/sandbox/Dockerfile -t mcp-sandbox:local .
```

`MCP_SANDBOX_BACKEND=local` existe solo para pruebas o desarrollo controlado; no
ofrece el mismo aislamiento que Docker. `web_search` requiere una instancia
SearxNG configurada con `MCP_WEB_SEARCH_BASE_URL`.

## Pruebas

```powershell
python -m pytest
```

Si pytest carga plugins globales incompatibles con Windows, usa:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
python -m pytest --basetemp C:\tmp\pytest-rag
```

La suite actual cubre autowrite, consola/prompts, objetivos de consola, data
tools, prompt context slimming, routing media, permisos de ejecucion del
runtime, slash submenus, subagentes, team prompt/tool guard, seleccion de modelo
vision y politica de ejecucion del worker.

## Artefactos Locales

No commitear caches ni sesiones locales:

- `.mcp_cache/`
- `.mcp_sessions/`
- `.mcp_traces/`
- `.mcp_sandbox/`
- `.pytest_cache/`
- `.pytest_tmp/`

`__pycache__`, `.pytest_cache`, `.pytest_tmp` y `pytest-cache-files-*` pueden
borrarse. Borra `.mcp_cache`, `.mcp_sessions` o `.mcp_traces` solo si quieres
perder cache, sesiones o trazas persistidas.
