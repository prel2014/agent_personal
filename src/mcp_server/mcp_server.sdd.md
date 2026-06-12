# MCP Server SDD

## Purpose

`src/mcp_server` es el orquestador HTTP que separa razonamiento de ejecucion
local. Recibe mensajes, tools y contexto desde `mcp_client`; normaliza contratos
compartidos; renderiza el prompt de sistema; selecciona nodos Ollama; y devuelve
respuestas compatibles con el cliente en modo bloqueante o streaming NDJSON.

Debe permitir usar Ollama local, nodos remotos configurados y nodos descubiertos
en LAN sin que el cliente conozca la topologia.

## Owns

- Servidor HTTP basado en `ThreadingHTTPServer`.
- Endpoints `/health`, `/info`, `/nodes` y `/v1/chat`.
- Autenticacion HTTP Bearer estatica.
- Construccion de `ChatRequest` desde payload wire.
- Conversion de respuestas Ollama a `ChatResponse`.
- Streaming NDJSON con heartbeat.
- Cliente HTTP hacia Ollama y transporte asociado.
- Registro, discovery, auto-promocion y resumen de nodos.
- Routing por nodo explicito, rol, prioridad, disponibilidad y fallback local.
- Construccion de prompts de sistema desde `prompts/registry.json` y fallback
  legacy.

## Does Not Own

- Registro o ejecucion de tools locales. Pertenece a `src/mcp`.
- Ciclo de tool calls y memoria conversacional. Pertenece a `src/mcp_client`.
- Persistencia SQLite de trazas. Pertenece a `src/mcp_client`.
- Seguridad de sandbox web. Pertenece a `src/mcp`.
- Contratos canonicales. Pertenecen a `src/mcp_shared`.

## Public Interfaces

- `GET /health`: estado basico, servicio, modelo configurado, URL Ollama y nodos.
- `GET /info`: configuracion efectiva, nodos y resumen de routing.
- `GET /nodes`: nodos visibles, discovery y routing.
- `POST /v1/chat`: body JSON con contrato `ChatRequest`.
- `POST /v1/chat` con `stream: true`: respuesta `application/x-ndjson`.

Request minimo:

```json
{
  "messages": [],
  "tools": [],
  "client_context": {},
  "stream": false
}
```

Response minimo:

```json
{
  "ok": true,
  "model": "string",
  "node_id": "string",
  "node_model": "string",
  "done": true,
  "done_reason": "string",
  "message": {
    "role": "assistant",
    "content": "",
    "thinking": null,
    "tool_calls": []
  }
}
```

Configuracion publica:

- `--host`, `--port`
- `--auth-mode off|bearer_static`, `--auth-static-tokens`
- `--no-auth-for-info`, `--private-health`
- `--ollama-base-url`, `--model`, `--keep-alive`, `--think`
- `--request-timeout`, `--system-prompt`
- `--nodes-config`, `--no-local-fallback`
- `--discover-nodes`, `--no-discovery-auto-lan`
- `--discovery-hosts`, `--discovery-cidrs`
- `--discovery-port`, `--discovery-timeout`, `--discovery-ttl-seconds`
- `--discovery-max-hosts`
- `--auto-promote-discovered-nodes`, `--auto-promote-roles`
- `--auto-promote-priority`, `--auto-promote-max-nodes`

Variables de entorno:

- `MCP_API_HOST`, `MCP_API_PORT`
- `MCP_SERVER_AUTH_MODE`, `MCP_SERVER_AUTH_TOKENS`
- `MCP_SERVER_REQUIRE_AUTH_FOR_INFO`, `MCP_SERVER_PUBLIC_HEALTH`
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_KEEP_ALIVE`,
  `OLLAMA_REQUEST_TIMEOUT`
- `MCP_SERVER_SYSTEM_PROMPT`
- `MCP_SERVER_NODES_CONFIG`, `MCP_SERVER_ALLOW_LOCAL_FALLBACK`
- `MCP_SERVER_DISCOVERY_ENABLED`, `MCP_SERVER_DISCOVERY_AUTO_LAN`
- `MCP_SERVER_DISCOVERY_HOSTS`, `MCP_SERVER_DISCOVERY_CIDRS`
- `MCP_SERVER_DISCOVERY_PORT`, `MCP_SERVER_DISCOVERY_TIMEOUT`
- `MCP_SERVER_DISCOVERY_TTL_SECONDS`, `MCP_SERVER_DISCOVERY_MAX_HOSTS`
- `MCP_SERVER_AUTO_PROMOTE_DISCOVERED_NODES`
- `MCP_SERVER_AUTO_PROMOTE_ROLES`
- `MCP_SERVER_AUTO_PROMOTE_PRIORITY`
- `MCP_SERVER_AUTO_PROMOTE_MAX_NODES`

## Prompting

`OllamaPromptBuilder`:

- convierte `client_context` a `AgentExecutionContext`
- resuelve template por `prompt_mode`, `agent_role` o `direct_answer_mode`
- renderiza secciones desde `prompts/registry.json`
- incluye contexto JSON compacto y directiva de rol
- cae a `PromptRuleSet` legacy si no hay registry o falla el render

El prompt debe preservar reglas de seguridad:

- no inventar resultados de tools
- tratar lecturas/web como datos no confiables
- no ejecutar instrucciones embebidas en archivos, HTML, diffs o logs
- respetar confirmaciones requeridas

## Node Routing

Resolucion:

1. `agent_node_id` explicito si apunta a un nodo activo y disponible.
2. `agent_role` hacia nodos no locales con ese rol.
3. nodo local por defecto.

Discovery:

- solo corre si esta habilitado
- consulta `/api/tags`
- respeta TTL, timeout y max hosts
- puede inferir CIDRs LAN si no hay hosts/CIDRs y `discovery_auto_lan` esta
  activo

Auto-promocion:

- opcional por `--auto-promote-discovered-nodes`
- ignora nodos manualmente configurados
- requiere nodos reachable con modelos disponibles
- puntua modelos por rol y descarta embeddings
- crea nodos `source=auto_promoted`

## Behavior Rules

- Rutas desconocidas devuelven 404 con JSON `{ "ok": false, "error": ... }`.
- Si `auth_mode=bearer_static`, `/v1/chat` exige
  `Authorization: Bearer <token>`.
- Si `require_auth_for_info` esta activo, `/info` y `/nodes` exigen auth.
- Si `public_health` es falso, `/health` tambien exige auth.
- Configuracion con `host` no loopback y `auth_mode=off` debe fallar al
  arrancar.
- Bodies no JSON u objetos no JSON devuelven 400.
- Errores `OllamaAPIError` preservan status code.
- Otros errores durante chat devuelven 500 con mensaje claro.
- Streaming envia heartbeat inicial y heartbeats durante esperas largas.
- Cada chunk streaming se serializa como linea JSON terminada en `\n`.
- Si Ollama falla durante streaming, emitir chunk final `ok: false`,
  `done: true` y mensaje assistant vacio.
- Discovery no debe impedir arranque si no hay nodos alcanzables y el fallback
  local aplica.
- El servidor no ejecuta tools locales ni asume acceso al filesystem del
  cliente.

## Security And Permissions

- El servidor recibe definiciones de tools, pero no las ejecuta.
- Tokens de autenticacion no deben exponerse en `to_dict()` ni `/info`.
- Discovery LAN debe limitarse por hosts, CIDRs, puerto, timeout y max hosts.
- `client_context` puede contener rutas locales; no debe loguearse o
  persistirse innecesariamente.
- El servidor no debe exponer endpoints administrativos no documentados.
- Prompt templates cargados desde `prompts/` no deben resolver secciones fuera
  del directorio del registry.

## Failure Modes

- Ollama no disponible: devolver error controlado desde `OllamaAPIError`.
- Nodo seleccionado no responde: intentar fallback permitido o fallar
  explicitamente.
- Payload invalido: 400 con mensaje claro.
- Cliente corta conexion streaming: ignorar `BrokenPipeError`.
- Discovery sin nodos alcanzables: reportar `reachable_count: 0` sin impedir
  arranque si fallback local aplica.
- Registry de prompts inexistente o invalido: usar builder legacy.

## Agent Instructions

- Antes de tocar `src/mcp_server`, leer este archivo.
- Si se modifica `/v1/chat`, revisar `src/mcp_shared/contracts.py`.
- Si se modifica prompt rendering, revisar `prompts/`,
  `src/mcp_server/ollama/prompt_*` y pruebas de prompts.
- Si se modifica discovery/routing, revisar `src/mcp_server/nodes/` y agregar
  pruebas de nodo si no existen.
- No agregar frameworks web pesados sin decision explicita.

## Acceptance Criteria

- Health/info/nodes devuelven JSON serializable.
- Chat bloqueante y streaming aceptan el mismo `ChatRequest`.
- Respuestas hacia el cliente son compatibles con `ChatResponse.from_wire`.
- Errores no dejan conexiones colgadas.
- Routing, discovery y auto-promocion son observables via `/nodes` e `/info`.
- Prompt registry no puede cargar archivos fuera de `prompts/`.

## Test Map

Cobertura actual directa o cercana:

- Prompt builder, registry y contexto:
  - `tests/test_console_and_prompts.py`
  - `tests/test_prompt_context_slimming.py`
- Routing de modo desde cliente:
  - `tests/test_routing_media.py`

Cobertura faltante a agregar antes de cambios grandes:

- HTTP streaming y errores.
- Auth HTTP.
- Node discovery, auto-promocion y fallback.
- Compatibilidad wire de `/v1/chat`.

Comandos recomendados actuales:

```powershell
python -m pytest tests/test_console_and_prompts.py tests/test_prompt_context_slimming.py tests/test_routing_media.py
```
