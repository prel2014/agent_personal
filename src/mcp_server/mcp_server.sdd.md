# MCP Server SDD

## Purpose

`src/mcp_server` es el orquestador HTTP que separa el razonamiento del cliente
local. Recibe mensajes, tools y contexto desde `mcp_client`; normaliza contratos
compartidos; selecciona nodos Ollama; y devuelve respuestas compatibles con el
cliente en modo bloqueante o streaming NDJSON.

Debe permitir ejecutar razonamiento en un nodo local, en nodos remotos
configurados o en nodos descubiertos en LAN sin que el cliente tenga que conocer
la topologia.

## Owns

- Servidor HTTP basado en `ThreadingHTTPServer`.
- Endpoints de health, info, nodes y chat.
- Construccion de `ChatRequest` desde payload wire.
- Conversion de respuestas Ollama a `ChatResponse`.
- Streaming NDJSON con heartbeat.
- Cliente HTTP hacia Ollama y transporte asociado.
- Registro, discovery, promocion y resumen de nodos.
- Routing por modelo, rol, prioridad, disponibilidad y fallback local.
- Prompt de sistema del orquestador.

## Does Not Own

- Registro o ejecucion de tools locales. Pertenece a `src/mcp`.
- Ciclo de tool calls y memoria conversacional. Pertenece a `src/mcp_client`.
- Persistencia SQLite de trazas. Pertenece a `src/mcp_client`.
- Seguridad de sandbox web. Pertenece a `src/mcp`.
- Definicion canonical de contratos compartidos. Pertenece a `src/mcp_shared`.

## Public Interfaces

- `GET /health`: estado basico, servicio, modelo configurado, URL Ollama y nodos.
- `GET /info`: configuracion efectiva, nodos y resumen de routing.
- `GET /nodes`: nodos visibles, discovery y routing.
- `POST /v1/chat`: body JSON con contrato `ChatRequest`.
- `POST /v1/chat` con `stream: true`: respuesta `application/x-ndjson`.

Contrato de request:

```json
{
  "messages": [],
  "tools": [],
  "client_context": {},
  "stream": false
}
```

Contrato de response:

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

Configuracion publica principal:

- `--host`, `--port`
- `--auth-mode off|bearer_static`, `--auth-static-tokens`
- `--no-auth-for-info`, `--private-health`
- `--ollama-base-url`, `--model`, `--keep-alive`, `--think`
- `--request-timeout`
- `--nodes-config`
- `--allow-local-fallback`
- `--discover-nodes`, `--discovery-hosts`, `--discovery-cidrs`
- `--discovery-port`, `--discovery-timeout`, `--discovery-ttl-seconds`, `--discovery-max-hosts`
- `--auto-promote-discovered-nodes`, `--auto-promote-roles`

## Behavior Rules

- Rutas desconocidas deben devolver 404 con JSON `{ "ok": false, "error": ... }`.
- Si `auth_mode=bearer_static`, `/v1/chat` debe exigir `Authorization: Bearer <token>`.
- Si `require_auth_for_info` esta activo, `/info` y `/nodes` deben exigir autenticacion.
- Si `public_health` es falso, `/health` tambien debe exigir autenticacion.
- El servidor debe rechazar configuraciones con `host` no loopback y `auth_mode=off`.
- Bodies no JSON u objetos no JSON deben devolver 400.
- Errores `OllamaAPIError` deben preservar status code.
- Otros errores durante chat deben devolver 500 con mensaje de error.
- Streaming debe enviar un heartbeat inicial y heartbeats durante esperas largas.
- En streaming, cada chunk debe serializarse como una linea JSON terminada en `\n`.
- Si Ollama falla durante streaming, el servidor debe emitir un chunk final con `ok: false`, `done: true` y mensaje assistant vacio.
- Discovery solo debe ejecutarse cuando esta habilitado y debe respetar TTL, max hosts y timeouts.
- El fallback local solo puede usarse si `allow_local_fallback` esta activo.
- El servidor no debe ejecutar tools locales ni asumir acceso al filesystem del cliente.

## Security And Permissions

- El servidor recibe definiciones de tools, pero no las ejecuta.
- Los tokens de autenticacion no deben exponerse en `to_dict()` ni en `/info`.
- Discovery LAN debe estar limitado por configuracion: hosts, CIDRs, puerto, timeout y max hosts.
- El prompt de sistema debe recordar que el modelo no invente resultados de tools.
- `client_context` puede contener rutas locales; no debe loguearse o persistirse innecesariamente.
- El servidor no debe exponer endpoints administrativos no documentados.

## Failure Modes

- Ollama no disponible: devolver error controlado desde `OllamaAPIError`.
- Nodo seleccionado no responde: routing debe intentar alternativas permitidas o fallar explicitamente.
- Payload invalido: 400 con mensaje claro.
- Cliente corta conexion streaming: ignorar `BrokenPipeError`.
- Discovery sin nodos alcanzables: reportar `reachable_count: 0` sin impedir arranque si fallback local aplica.

## Agent Instructions

- Antes de tocar `src/mcp_server`, leer este archivo y `.specdd/bootstrap.md`.
- Si se modifica `/v1/chat`, revisar contratos en `src/mcp_shared/contracts.py`.
- Si se modifica streaming, revisar `tests/test_server_streaming.py`.
- Si se modifica discovery/routing, revisar `src/mcp_server/nodes/`, `src/mcp_server/ollama/client.py` y `tests/test_node_routing.py`.
- No agregar dependencias de frameworks web pesados sin una decision explicita; el servidor actual usa libreria estandar.

## Acceptance Criteria

- Health/info/nodes siguen devolviendo JSON serializable.
- Chat bloqueante y streaming aceptan el mismo `ChatRequest`.
- Las respuestas hacia el cliente siguen siendo compatibles con `ChatResponse.from_wire`.
- Los errores no dejan conexiones colgadas.
- Routing y discovery son observables via `/nodes` e `/info`.

## Test Map

- HTTP streaming:
  - `tests/test_server_streaming.py`
- Auth HTTP:
  - `tests/test_server_auth.py`
- Routing/discovery:
  - `tests/test_node_routing.py`
- Compatibilidad de tool calls y contratos:
  - `tests/test_tool_call_compat.py`

Comandos recomendados:

```powershell
python -m pytest tests/test_server_streaming.py tests/test_server_auth.py tests/test_node_routing.py tests/test_tool_call_compat.py
```
