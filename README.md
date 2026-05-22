# RAG / MCP Orquestado Con Ollama

Este proyecto implementa un cliente local con tools, un orquestador HTTP y soporte para usar varias maquinas con Ollama como nodos de razonamiento distribuidos.

## Componentes

- `src/mcp_client`: cliente CLI, tools locales y orquestacion `planner -> worker -> reviewer`
- `src/mcp_server`: servidor HTTP y router hacia nodos Ollama
- `src/mcp`: runtime local de tools, permisos y contexto
- `examples/ollama_nodes.example.json`: ejemplo de configuracion de nodos remotos

## Casos De Uso

- usar un solo nodo Ollama local
- asignar distintos modelos por rol en varias maquinas
- autodetectar instancias Ollama disponibles en la red local
- ejecutar cambios sobre tu workspace local mientras el razonamiento corre en otros equipos

## Guia Principal

La documentacion completa de despliegue y uso esta aqui:

[Uso Del Orquestador Ollama Distribuido](docs/uso_orquestador_ollama_distribuido.md)

## Specification-Driven Development

Este repo documenta sus contratos para agentes en `.specdd/` y en specs
fuente-adjacent por subsistema:

- `src/mcp_client/mcp_client.sdd.md`
- `src/mcp_server/mcp_server.sdd.md`
- `src/mcp/mcp_runtime.sdd.md`

Guia de uso: [Specification-Driven Development Para Este Repo](docs/specification_driven_development.md)

## Inicio Rapido

Servidor:

```powershell
python -m src.mcp_server.server.cli `
  --host 0.0.0.0 `
  --port 8000 `
  --auth-mode bearer_static `
  --auth-static-tokens supersecreto `
  --nodes-config examples/ollama_nodes.example.json `
  --discover-nodes `
  --discovery-hosts 192.168.1.20,192.168.1.21,192.168.1.22
```

Si no tienes un archivo de nodos, omite `--nodes-config` y usa solo el nodo
local configurado por `--ollama-base-url` / `--model`.

Cliente:

```powershell
python -m src.mcp_client.commands.cli setup
python -m src.mcp_client.commands.cli --server-bearer-token supersecreto doctor
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 list-nodes
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 --server-bearer-token supersecreto ask "haz este cambio"
```

Si instalas el paquete, el entrypoint equivalente es:

```powershell
rag-agent doctor
rag-agent repl --continue
```

## Flujo Agentico Del Cliente

El cliente puede enrutar cada prompt a una respuesta directa o al flujo
`planner -> worker -> reviewer`, segun `--planning-mode`:

- `auto`: decide segun la solicitud.
- `always`: fuerza el equipo planner/worker/reviewer.
- `never`: usa respuesta directa sin orquestacion de equipo.

Roles:

- `planner`: no tiene tools. Produce un plan breve y delega la inspeccion real.
- `worker`: usa tools dentro del sandbox por defecto. Solo puede salir al host si
  el usuario lo pide explicitamente con frases como "fuera del sandbox" o "usa el host".
- `reviewer`: usa lectura para validar el resultado del worker.

Para trabajo multiarchivo, las tools de escritura devuelven resumen del archivo
final (`content_preview`, `content_sha256`, tamanos) para que el worker conserve
contexto entre archivos y no genere cada archivo de forma aislada.

El REPL renderiza Markdown cuando `rich` esta disponible. `thinking` esta apagado
por defecto; se activa con `--show-thinking`, `MCP_CLIENT_SHOW_THINKING=true`,
`Ctrl+T` o `/thinking on`, y se apaga con:

```text
/thinking off
```

## Sesiones Persistentes

El cliente puede guardar y reanudar conversaciones en SQLite separado de las
trazas de dataset:

```powershell
python -m src.mcp_client.commands.cli ask --new-session "analiza el repo"
python -m src.mcp_client.commands.cli sessions list
python -m src.mcp_client.commands.cli repl --continue
python -m src.mcp_client.commands.cli ask --session <session_id> "continua"
```

Dentro del REPL:

```text
/sessions
/resume <session_id>
/new investigacion
/save
/status
```

Roadmap de producto CLI: [Roadmap Hermes-Level CLI](docs/hermes_level_cli_roadmap.md)

## KV Cache Local

El cliente incluye un KV cache SQLite local en `.mcp_cache/kv_cache.sqlite`.
Sirve para guardar datos reutilizables por namespace/key, con TTL opcional.

```powershell
python -m src.mcp_client.commands.cli cache set repo last_scan "ok" --ttl-seconds 3600
python -m src.mcp_client.commands.cli cache get repo last_scan
python -m src.mcp_client.commands.cli cache list --namespace repo
python -m src.mcp_client.commands.cli cache clear --expired-only
```

Tambien esta disponible para el agente como tools locales `kv_get`, `kv_list`,
`kv_set`, `kv_delete` y `kv_clear_expired`. Las lecturas se marcan como
`untrusted`; las mutaciones son categoria `write` y respetan permisos y
confirmacion sensible.

Configuracion:

- `--kv-cache-db-path` / `MCP_CLIENT_KV_CACHE_DB_PATH`
- `--no-kv-cache` / `MCP_CLIENT_KV_CACHE_ENABLED=false`

## Medidor De Contexto

El REPL y los flujos agenticos muestran una barra estimada de uso de ventana de
contexto antes de cada llamada al modelo:

```text
[context worker step 1] [------------------------] 2% (2,048/131,072 tokens)
```

El calculo es local y aproximado; usa el historial de mensajes, tools expuestas
y `client_context`. Por defecto usa 131,072 tokens y el cliente envia ese valor
al servidor como `options.num_ctx` para Ollama. Puedes ajustar u ocultar el
medidor con:

- `--context-window-tokens 131072`
- `--no-context-meter`
- `MCP_CLIENT_CONTEXT_WINDOW_TOKENS`
- `MCP_CLIENT_SHOW_CONTEXT_METER=false`

## Tools Web Aisladas

Las tools `web_search` y `web_fetch` estan apagadas por defecto. Para usarlas con el backend Docker seguro:

```powershell
docker build -f docker/sandbox/Dockerfile -t mcp-sandbox:local .

python -m src.mcp.server `
  --allow-web `
  --sandbox-backend docker `
  --web-allowed-domains example.com `
  list-tools
```

`web_fetch` descarga paginas desde un worker Docker sin salida directa a internet; el egreso pasa por `src.mcp.sandbox.proxy`, que bloquea redes privadas/localhost/metadata cloud y aplica allowlist/denylist de dominios. Si `--web-allowed-domains` queda vacio, se permiten dominios publicos no bloqueados.

Para `web_search`, configura una instancia SearxNG:

```powershell
$env:MCP_WEB_SEARCH_BASE_URL="http://tu-searxng:8080"
```

Los resultados web se marcan como `untrusted`; el agente debe usarlos como evidencia, no como instrucciones.

## Limpieza De Artefactos Locales

Los directorios `__pycache__`, `.pytest_cache`, `.pytest_tmp` y
`pytest-cache-files-*` son artefactos de ejecucion y pueden borrarse. No borres
`.mcp_cache` ni `.mcp_sessions` salvo que quieras perder cache local y sesiones
persistentes.

## Seguridad HTTP Y Runtime

El `mcp_server` ahora soporta autenticacion HTTP por Bearer token. Si intentas
levantarlo fuera de loopback con `--auth-mode off`, el arranque falla por
seguridad.

Flags principales del servidor:

- `--auth-mode bearer_static`
- `--auth-static-tokens token1,token2`
- `--no-auth-for-info` para dejar `/info` y `/nodes` publicos
- `--private-health` para proteger tambien `/health`

Flags principales del cliente:

- `--server-bearer-token <token>`
- `--allow-remote-sensitive-tracing` si realmente quieres `--trace-capture full`
  o `--trace-thinking raw` contra un servidor remoto no loopback

En el runtime local tambien se agregaron dos controles nuevos:

- `--protected-read-paths` / `MCP_PROTECTED_READ_PATHS`: bloquea lectura e
  inspeccion de rutas sensibles como `.env`, `.git`, `*.pem` y `*.key`
- `--deny-execute` / `MCP_ALLOW_EXECUTE=false`: deshabilita tools de ejecucion
  local. Por defecto estan habilitadas para que el agente pueda validar trabajo
  con Python, tests y comandos de proyecto permitidos.
- `--tool-confirmation-mode sensitive`: exige aprobacion previa para tools
  sensibles de escritura, ejecucion, borrado, hardware, media input y sandbox
- `--approved-sensitive-tools`: allowlist explicita para permitir tools
  sensibles concretas cuando el modo de confirmacion esta activo

## Tools Git De Solo Lectura

El runtime expone tools Git de inspeccion como `git_status`, `git_diff`, `git_log`,
`git_show`, `git_branches`, `git_blame` y `git_ls_files`. Todas son de solo
lectura y funcionan solo cuando la ruta consultada pertenece a un repositorio
Git dentro de `base_dir`.

Estas tools ejecutan Git sin pager ni diff externo. Las operaciones mutantes
como `add`, `commit`, `merge`, `rebase`, `reset` o `push` no se exponen todavia
porque el runtime actual no tiene una capa de confirmacion por herramienta.

## Trazabilidad Y Dataset SQLite

La captura de ejecuciones agenticas puede activarse para guardar planner, worker,
reviewer, tool calls, correcciones, `thinking` crudo y ejemplos entrenables en
SQLite:

```powershell
python -m src.mcp_client.commands.cli `
  --trace-capture full `
  --trace-db-path .mcp_traces/agent_traces.sqlite `
  ask "implementa una mejora"
```

Contra un servidor remoto no loopback, `--trace-capture full` y
`--trace-thinking raw` requieren ademas `--allow-remote-sensitive-tracing`.

Luego puedes exportar ejemplos JSONL:

```powershell
python -m src.mcp_client.commands.cli export-dataset `
  --db-path .mcp_traces/agent_traces.sqlite `
  --output datasets/sft_conversation.jsonl
```

Detalles: [Trazabilidad SQLite Para Dataset](docs/trazabilidad_dataset_sqlite.md)
