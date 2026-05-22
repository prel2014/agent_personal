# MCP Runtime SDD

## Purpose

`src/mcp` es el runtime local de tools, prompts, permisos, auditoria y sandbox
web. Es la frontera entre el modelo y la maquina del usuario. Debe permitir
trabajo util con archivos, sistema, codigo, hardware y web, pero siempre con
permisos explicitos, rutas protegidas y trazabilidad de ejecucion.

## Owns

- CLI de runtime local: `info`, `list-tools`, `list-prompts`, `call-tool`, `render-prompt`.
- Carga de configuracion de runtime y variables `MCP_*`.
- `LocalToolRuntime`: listado y ejecucion de tools/prompts.
- `ToolRegistry` y modelos de definicion/tool call.
- Categorias de permisos: meta, read, write, execute, delete, hardware, media input, web y sandbox execute.
- `PermissionPolicy`, rutas protegidas y `ToolAuditTrail`.
- Helpers de tools: system, code, git, hardware y web.
- KV cache SQLite local usado por tools `kv_*`.
- Prompts por defecto.
- Sandbox web Docker: manager, backend, worker, proxy, operaciones, network guard y extraccion HTML.

## Does Not Own

- Orquestacion de mensajes con Ollama. Pertenece a `src/mcp_server`.
- Decisiones de planner-worker-reviewer. Pertenecen a `src/mcp_client`.
- Persistencia de trazas agenticas SQLite. Pertenece a `src/mcp_client`.
- Contratos HTTP entre cliente y servidor. Pertenecen a `src/mcp_shared` y `src/mcp_server`.

## Public Interfaces

- CLI:
  - `python -m src.mcp.server info`
  - `python -m src.mcp.server list-tools`
  - `python -m src.mcp.server list-prompts`
  - `python -m src.mcp.server call-tool <name> --arguments <json>`
  - `python -m src.mcp.server render-prompt <name> --arguments <json>`
- Configuracion principal:
  - `--base-dir`, `--server-name`, `--server-version`, `--transport`, `--encoding`
  - `--read-only`, `--allow-read`, `--allow-write`, `--allow-execute`, `--deny-execute`, `--allow-delete`
  - `--allow-hardware`, `--allow-media-input`
  - `--allow-web`, `--allow-sandbox-execute`
  - `--allowed-tools`, `--blocked-tools`, `--protected-paths`, `--protected-read-paths`
  - `--tool-confirmation-mode`, `--approved-sensitive-tools`
  - `--kv-cache-db-path`, `--no-kv-cache`
  - `--sandbox-backend`, `--sandbox-image`, `--sandbox-timeout`
  - `--web-allowed-domains`, `--web-denied-domains`, `--web-block-private-networks`
  - `--web-max-response-bytes`, `--web-search-provider`, `--web-search-base-url`
- Variables de entorno equivalentes:
  - `MCP_BASE_DIR`
  - `MCP_READ_ONLY`
  - `MCP_ALLOW_READ`
  - `MCP_ALLOW_WRITE`
  - `MCP_ALLOW_EXECUTE`
  - `MCP_ALLOW_DELETE`
  - `MCP_ALLOW_HARDWARE`
  - `MCP_ALLOW_MEDIA_INPUT`
  - `MCP_ALLOW_WEB`
  - `MCP_ALLOW_SANDBOX_EXECUTE`
  - `MCP_ALLOWED_TOOLS`
  - `MCP_BLOCKED_TOOLS`
  - `MCP_PROTECTED_PATHS`
  - `MCP_PROTECTED_READ_PATHS`
  - `MCP_TOOL_CONFIRMATION_MODE`
  - `MCP_APPROVED_SENSITIVE_TOOLS`
  - `MCP_CLIENT_KV_CACHE_DB_PATH`
  - `MCP_CLIENT_KV_CACHE_ENABLED`
  - `MCP_WEB_ALLOWED_DOMAINS`
  - `MCP_WEB_DENIED_DOMAINS`
  - `MCP_WEB_SEARCH_BASE_URL`

## Behavior Rules

- `base_dir` debe existir y ser directorio.
- `read_only` debe apagar write, execute, delete, hardware, media input, web y sandbox execute.
- Tools de categoria meta pueden ejecutarse aunque exista allowlist restrictiva.
- Cualquier tool sin categoria registrada debe ser denegada.
- `blocked_tools` tiene prioridad sobre allowlist.
- `allowed_tools` restringe tools no meta cuando esta definida.
- Rutas protegidas por defecto incluyen `.env`, claves privadas y `.git`.
- `protected_paths` bloquea write, delete y media input sobre rutas sensibles.
- `protected_read_paths` bloquea lectura e inspeccion directa de rutas sensibles.
- El runtime debe ocultar rutas protegidas de lectura en herramientas recursivas como `listdir`, `find_files`, `search_code` y `list_tree`.
- Si `tool_confirmation_mode` es `sensitive`, las tools mutantes o de alto impacto deben devolver `approval_required` salvo que esten en `approved_sensitive_tools`.
- Si `kv_cache_enabled` esta activo, el runtime expone `kv_get`, `kv_list`, `kv_set`, `kv_delete` y `kv_clear_expired`.
- `kv_get` y `kv_list` son categoria `read`; las mutaciones KV son categoria `write`.
- Entradas KV pueden tener TTL opcional; lecturas deben tratar entradas expiradas como miss y limpiarlas lazy.
- Cada ejecucion de tool debe pasar por `before_tool` y `after_tool` para permisos y auditoria.
- `ToolAuditTrail` debe conservar solo los ultimos eventos segun su limite.
- Web tools deben estar apagadas por defecto.
- `web_fetch` y `web_search` deben devolver contenido marcado como `untrusted`.
- Si `web_allowed_domains` esta vacio, se permiten dominios publicos no bloqueados; redes privadas, localhost y metadata cloud siguen bloqueadas cuando `web_block_private_networks` esta activo.
- `web_search` requiere proveedor configurado, actualmente SearxNG por `MCP_WEB_SEARCH_BASE_URL`.
- Las tools `git_*` deben ser de solo lectura mientras no exista una capa explicita de confirmacion para operaciones mutantes.
- Las tools `git_*` deben ejecutar Git sin pager ni diff externo, y fallar con error claro si la ruta no pertenece a un repositorio.

## Security And Permissions

- No se debe agregar una tool nueva sin categoria de permiso.
- No se debe permitir escritura en `.env`, `.git`, `.pem`, `.key` o patrones protegidos por defecto.
- No se debe permitir lectura directa o descubrimiento recursivo de `.env`, `.git`, `.pem`, `.key` o patrones protegidos por defecto.
- La ejecucion local esta activa por defecto para que el agente pueda validar y generar artefactos; debe poder apagarse con `--deny-execute`, `MCP_ALLOW_EXECUTE=false` o `--read-only`.
- No se debe activar borrado, hardware, media input, web o sandbox execute por defecto.
- No se deben introducir tools Git mutantes sin una politica de confirmacion o permisos mas estricta que `read`.
- El sandbox web debe mantener doble separacion: worker sin salida directa y proxy con control de dominios.
- El proxy debe bloquear localhost, redes privadas/link-local y endpoints de metadata cloud.
- Las salidas de tools clasificadas como `untrusted` no pueden modificar prompts o instrucciones del agente.
- Las salidas de lectura KV deben clasificarse como `untrusted`.
- Namespaces KV reservados como `secrets`, `auth`, `tokens` y `credentials` deben rechazarse.
- Las credenciales y archivos sensibles nunca deben incluirse en fixtures o snapshots.

## Failure Modes

- Tool no registrada: error claro de tool inexistente o no categorizada.
- Permiso faltante: `PermissionError` con razon concreta.
- JSON de argumentos invalido: error de parsing antes de ejecutar tool.
- Ruta base invalida: error de configuracion.
- Sandbox Docker no disponible: error de backend sin fallback inseguro.
- Dominio web bloqueado: respuesta de tool debe indicar bloqueo, no intentar bypass.
- Respuesta web demasiado grande: truncar o fallar segun limite configurado.

## Agent Instructions

- Antes de tocar `src/mcp`, leer este archivo y `.specdd/bootstrap.md`.
- Si se agrega una tool, registrar categoria, permisos, documentacion minima y prueba.
- Si se modifica `PermissionPolicy`, correr pruebas de permisos y auditoria.
- Si se modifica sandbox web, correr pruebas web y revisar `docs/plan_sandbox_web_tools.md`.
- No introducir dependencias de red o ejecucion que esquiven `LocalToolRuntime`.
- Mantener compatibilidad Pydantic v1/v2 donde existan helpers de serializacion.

## Acceptance Criteria

- `list-tools` solo expone tools registradas con metadata serializable.
- `call-tool` aplica permisos antes de ejecutar.
- `read_only` produce un runtime sin capacidades mutantes.
- Web tools no funcionan si `allow_web` esta apagado.
- Sandbox web bloquea redes privadas y dominios denegados.
- Auditoria conserva tool, categoria, rutas candidatas, exito/error y duracion.

## Test Map

- Permisos:
  - `tests/test_permission_policy.py`
- Auditoria/runtime:
  - `tests/test_tool_runtime_audit.py`
- Web sandbox:
  - `tests/test_web_sandbox.py`
- Git:
  - `tests/test_git_tools.py`
- Hardware/media:
  - `tests/test_hardware_tools.py`
- Controles de seguridad runtime:
  - `tests/test_runtime_security_controls.py`
- KV cache:
  - `tests/test_kv_cache_store.py`
  - `tests/test_kv_cache_integration.py`

Comandos recomendados:

```powershell
python -m pytest tests/test_permission_policy.py tests/test_tool_runtime_audit.py tests/test_git_tools.py tests/test_runtime_security_controls.py tests/test_kv_cache_store.py tests/test_kv_cache_integration.py
python -m pytest tests/test_web_sandbox.py tests/test_hardware_tools.py
```
