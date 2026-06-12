# MCP Runtime SDD

## Purpose

`src/mcp` es el runtime local de tools, prompts, permisos, auditoria y sandbox
web. Es la frontera entre el modelo y la maquina del usuario. Debe permitir
trabajo util con archivos, sistema, codigo, Git, datos, hardware, media y web,
pero siempre con permisos explicitos, rutas protegidas y trazabilidad de
ejecucion.

## Owns

- CLI de runtime local: `info`, `list-tools`, `list-prompts`, `call-tool`,
  `render-prompt`.
- Carga de configuracion de runtime y variables `MCP_*`.
- `LocalToolRuntime`: listado y ejecucion de tools/prompts.
- `ToolRegistry`, `ToolDefinition`, `RuntimeToolCall` y `ToolResult`.
- Categorias de permisos: meta, read, write, execute, delete, hardware, media
  input, web y sandbox execute.
- `PermissionPolicy`, rutas protegidas y `ToolAuditTrail`.
- Helpers de tools: system, code, Git, KV, hardware/media, web y datos.
- KV cache SQLite local usado por tools `kv_*`.
- Prompts por defecto del runtime.
- Sandbox web Docker/local: manager, backend, worker, proxy, operaciones,
  network guard y extraccion HTML.
- Deteccion local de perfil de proyecto para contexto (`detected_languages`,
  `primary_language`, `tooling`).

## Does Not Own

- Orquestacion de mensajes con Ollama. Pertenece a `src/mcp_server`.
- Decisiones planner-worker-reviewer. Pertenecen a `src/mcp_client`.
- Persistencia de trazas agenticas SQLite. Pertenece a `src/mcp_client`.
- Contratos HTTP entre cliente y servidor. Pertenecen a `src/mcp_shared` y
  `src/mcp_server`.

## Public Interfaces

CLI:

- `python -m src.mcp.server info`
- `python -m src.mcp.server list-tools`
- `python -m src.mcp.server list-prompts`
- `python -m src.mcp.server call-tool <name> --arguments <json>`
- `python -m src.mcp.server render-prompt <name> --arguments <json>`

Configuracion principal:

- `--base-dir`, `--server-name`, `--server-version`, `--transport`,
  `--encoding`
- `--read-only`, `--deny-read`, `--deny-write`, `--allow-execute`,
  `--deny-execute`
- `--allow-delete`, `--allow-hardware`, `--allow-media-input`
- `--vision-model`, `--vision-ollama-base-url`
- `--allow-web`, `--allow-sandbox-execute`
- `--allowed-tools`, `--blocked-tools`
- `--protected-paths`, `--protected-read-paths`
- `--tool-confirmation-mode off|sensitive`, `--approved-sensitive-tools`
- `--kv-cache-db-path`, `--no-kv-cache`
- `--sandbox-backend docker|local`, `--sandbox-image`, `--sandbox-timeout`
- `--web-allowed-domains`, `--web-denied-domains`, `--allow-private-web`
- `--web-max-response-bytes`, `--web-search-provider`, `--web-search-base-url`

Variables de entorno:

- `MCP_BASE_DIR`
- `MCP_SERVER_NAME`, `MCP_SERVER_VERSION`, `MCP_TRANSPORT`, `MCP_ENCODING`
- `MCP_READ_ONLY`
- `MCP_ALLOW_READ`, `MCP_ALLOW_WRITE`, `MCP_ALLOW_EXECUTE`
- `MCP_ALLOW_DELETE`, `MCP_ALLOW_HARDWARE`, `MCP_ALLOW_MEDIA_INPUT`
- `MCP_VISION_MODEL`, `OLLAMA_VISION_MODEL`
- `MCP_VISION_OLLAMA_BASE_URL`, `OLLAMA_BASE_URL`
- `MCP_ALLOW_WEB`, `MCP_ALLOW_SANDBOX_EXECUTE`
- `MCP_ALLOWED_TOOLS`, `MCP_BLOCKED_TOOLS`
- `MCP_PROTECTED_PATHS`, `MCP_PROTECTED_READ_PATHS`
- `MCP_TOOL_CONFIRMATION_MODE`, `MCP_APPROVED_SENSITIVE_TOOLS`
- `MCP_CLIENT_KV_CACHE_DB_PATH`, `MCP_CLIENT_KV_CACHE_ENABLED`
- `MCP_SANDBOX_BACKEND`, `MCP_SANDBOX_IMAGE`, `MCP_SANDBOX_TIMEOUT`
- `MCP_WEB_ALLOWED_DOMAINS`, `MCP_WEB_DENIED_DOMAINS`
- `MCP_WEB_BLOCK_PRIVATE_NETWORKS`
- `MCP_WEB_MAX_RESPONSE_BYTES`
- `MCP_WEB_SEARCH_PROVIDER`, `MCP_WEB_SEARCH_BASE_URL`

Tool families:

- System/files: `pwd`, `listdir`, `list_tree`, `find_files`, `fileinfo`,
  `readfile`, `read_lines`, `search_code`, write/replace/move/mkdir/delete.
- Code: Python, Node/TS and .NET helpers exposed by `code_tools`.
- Git read-only: `git_status`, `git_diff`, `git_log`, `git_show`,
  `git_branches`, `git_blame`, `git_ls_files`.
- KV: `kv_get`, `kv_list`, `kv_set`, `kv_delete`, `kv_clear_expired`.
- Hardware/media: serial tools and `image_describe`.
- Web/sandbox: `web_search`, `web_fetch`, `sandbox_run`.
- Data: `determinar_tipo_dato`, `generar_grafico_barras`.

## Behavior Rules

- `base_dir` debe existir y ser directorio.
- `read_only` apaga write, execute, delete, hardware, media input, web y
  sandbox execute.
- Tools meta pueden ejecutarse aunque exista allowlist restrictiva.
- Cualquier tool sin categoria registrada debe ser denegada.
- `blocked_tools` tiene prioridad sobre allowlist.
- `allowed_tools` restringe tools no meta cuando esta definida.
- Rutas protegidas por defecto incluyen `.env`, claves privadas y `.git`.
- `protected_paths` bloquea write, delete y media input sobre rutas sensibles.
- `protected_read_paths` bloquea lectura e inspeccion directa de rutas sensibles.
- Herramientas recursivas como `listdir`, `find_files`, `search_code` y
  `list_tree` deben ocultar rutas protegidas de lectura.
- Si `tool_confirmation_mode=sensitive`, tools mutantes o de alto impacto deben
  devolver `approval_required` salvo que esten en `approved_sensitive_tools`.
- Si `kv_cache_enabled` esta activo, exponer tools `kv_*`.
- `kv_get` y `kv_list` son categoria `read`; mutaciones KV son `write`.
- Entradas KV con TTL expirado deben tratarse como miss y limpiarse lazy.
- Cada ejecucion de tool pasa por `before_tool` y `after_tool`.
- `ToolAuditTrail` conserva solo ultimos eventos segun limite.
- Web tools estan apagadas por defecto.
- `web_fetch` y `web_search` devuelven contenido `untrusted`.
- Si `web_allowed_domains` esta vacio, se permiten dominios publicos no
  bloqueados; redes privadas, localhost y metadata cloud siguen bloqueadas
  cuando `web_block_private_networks` esta activo.
- `web_search` requiere SearxNG por `MCP_WEB_SEARCH_BASE_URL`.
- `sandbox_run` requiere `allow_sandbox_execute`.
- Tools Git son solo lectura mientras no exista confirmacion para mutaciones.
- Tools Git ejecutan Git sin pager ni diff externo.
- Data tools de lectura devuelven datos tabulares como `untrusted`.

## Security And Permissions

- No agregar una tool nueva sin categoria de permiso.
- No permitir escritura en `.env`, `.git`, `.pem`, `.key` o patrones protegidos.
- No permitir lectura directa o descubrimiento recursivo de rutas protegidas.
- Ejecucion local esta activa por defecto para validar trabajo; debe poder
  apagarse con `--deny-execute`, `MCP_ALLOW_EXECUTE=false` o `--read-only`.
- Borrado, hardware, media input, web y sandbox execute no deben activarse por
  defecto.
- No introducir Git mutante sin politica de confirmacion mas estricta que read.
- Sandbox web debe mantener worker sin salida directa y proxy con control de
  dominios.
- Proxy debe bloquear localhost, redes privadas/link-local y metadata cloud.
- Salidas `untrusted` no pueden modificar prompts o instrucciones del agente.
- Salidas KV de lectura son `untrusted`.
- Namespaces KV reservados como `secrets`, `auth`, `tokens` y `credentials`
  deben rechazarse.
- Credenciales y archivos sensibles nunca deben incluirse en fixtures o
  snapshots.

## Failure Modes

- Tool no registrada: error claro de herramienta inexistente.
- Tool sin categoria: denegacion por politica.
- Permiso faltante: `PermissionError` con razon concreta.
- JSON de argumentos invalido: error antes de ejecutar tool.
- Ruta base invalida: error de configuracion.
- Sandbox Docker no disponible: error de backend sin fallback inseguro.
- Imagen Docker ausente: error con comando de build esperado.
- Dominio web bloqueado: respuesta de tool indica bloqueo.
- Respuesta web demasiado grande: truncar o fallar segun limite configurado.
- SearxNG no configurado: `web_search` falla con mensaje accionable.
- Data file inexistente o extension no soportada: error claro.

## Agent Instructions

- Antes de tocar `src/mcp`, leer este archivo.
- Si se agrega una tool, registrar categoria, permisos, documentacion minima y
  prueba.
- Si se modifica `PermissionPolicy`, correr pruebas de permisos/runtime.
- Si se modifica sandbox web, actualizar `docs/plan_sandbox_web_tools.md`.
- No introducir dependencias de red o ejecucion que esquiven `LocalToolRuntime`.
- Mantener compatibilidad Pydantic v1/v2 donde existan helpers de serializacion.

## Acceptance Criteria

- `list-tools` solo expone tools registradas con metadata serializable.
- `call-tool` aplica permisos antes de ejecutar.
- `read_only` produce runtime sin capacidades mutantes.
- Web tools no funcionan si `allow_web` esta apagado.
- Sandbox web bloquea redes privadas y dominios denegados por defecto.
- Auditoria conserva tool, categoria, rutas candidatas, exito/error y duracion.
- Contexto runtime evita cargar catalogos pesados innecesarios.

## Test Map

Cobertura actual:

- Runtime execute defaults:
  - `tests/test_runtime_execute_defaults.py`
- Worker/tool policy:
  - `tests/test_worker_execute_policy.py`
- Data tools:
  - `tests/test_data_tools.py`
- Vision model selection:
  - `tests/test_vision_model_selection.py`
- Prompt context from runtime:
  - `tests/test_prompt_context_slimming.py`

Cobertura faltante a agregar antes de cambios grandes:

- `PermissionPolicy` granular.
- Auditoria runtime.
- Git tools.
- KV cache store/integration.
- Web sandbox domain/network/proxy.
- Hardware/media integration.

Comandos recomendados actuales:

```powershell
python -m pytest tests/test_runtime_execute_defaults.py tests/test_worker_execute_policy.py tests/test_data_tools.py tests/test_vision_model_selection.py tests/test_prompt_context_slimming.py
```
