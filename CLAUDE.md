# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos esenciales

**Instalación:**
```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

**Tests:**
```powershell
python -m pytest                          # suite completa
python -m pytest tests/test_subagents.py # un solo archivo
python -m pytest -k "test_nombre"        # un test específico
```

**Ejecutar el cliente:**
```powershell
rag-agent repl                            # REPL interactivo
rag-agent ask "prompt"                    # single shot
rag-agent setup                           # crear DBs y directorios locales
rag-agent doctor                          # validar configuración
rag-agent skills list                     # listar skills disponibles
rag-agent skills show <nombre>            # ver un skill
rag-agent ask --skill <nombre> "prompt"   # activar skill por sesión
rag-agent memory list                     # listar memorias
rag-agent memory add <clave> <valor>      # guardar memoria de proyecto
rag-agent memory search <query>           # buscar memoria
rag-agent memory forget <clave>           # borrar memoria
```

**Ejecutar el servidor:**
```powershell
python -m src.mcp_server.server.cli --host 127.0.0.1 --port 8000 --ollama-base-url http://127.0.0.1:11434
```

**Ejecutar el runtime local directamente:**
```powershell
python -m src.mcp.server list-tools
python -m src.mcp.server call-tool readfile --arguments '{"path":"README.md"}'
```

No hay linter configurado. La config de pytest está en `pyproject.toml`.

## Arquitectura

El sistema tiene tres capas que se pueden desplegar en máquinas distintas:

```
mcp_client  ──HTTP──►  mcp_server  ──HTTP──►  Ollama (LLM)
    │                                              │
    └──────  mcp (runtime local, tools)  ◄─────────┘
                                              (tool calls)
```

### `src/mcp_client` — Cliente/CLI
Dueño del ciclo de vida del usuario: CLI, REPL, sesiones persistentes, slash commands, autowrite de código desde Markdown, y el workflow agentico (Planner → Worker → Reviewer).

- `agentic/` — orquestación: roles, políticas, team, subagentes, trazas, skills, memoria
- `sessions/` — persistencia SQLite de conversaciones
- `slash/` — lexer, parser, router, completion de slash commands
- `autowrite/` — extrae bloques de código de respuestas Markdown e infiere rutas
- `transport/` — HTTP hacia `mcp_server`
- `prompts/` — prompts de routing y compactación de contexto
- `workflows/` — registry de workflows y trazado de ejecuciones

### `src/mcp_server` — Orquestador HTTP
Dueño del routing hacia nodos Ollama: auth Bearer estática, discovery LAN, auto-promoción de nodos, selección por rol/prioridad, rendering de prompts desde `prompts/registry.json`, streaming NDJSON con heartbeat.

- `ollama/` — cliente Ollama, prompt builder, registry, reglas
- `nodes/` — configuración, discovery, routing

### `src/mcp` — Runtime local de tools
Dueño de la ejecución de tools: `LocalToolRuntime`, `PermissionPolicy`, sandbox web (Docker/local), KV cache SQLite, auditoria.

- `tools/` — helpers: sistema de archivos, código, Git (read-only), KV, hardware/media, web, datos
- `security.py` — `PermissionPolicy`, rutas protegidas por defecto (`.env`, `.git`, `.pem`)
- `sandbox/` — backend Docker/local para ejecución sandboxed

### `src/mcp_shared` — Contratos compartidos
`ChatMessage`, `ChatRequest`, `ChatResponse`, `ToolCall`, `AgentExecutionContext`. Helpers: SQLite, Markdown, URLs, env.

## Patrones clave

### Workflow Team (Planner → Worker → Reviewer)
El cliente usa tres roles especializados en secuencia cuando `--planning-mode` no es `never`:
- **Planner** — sin tools, produce plan breve: OBJETIVO, HALLAZGOS, PLAN, RIESGOS
- **Worker** — tools completos, sandbox-first, ejecuta pragmáticamente
- **Reviewer** — read-only, valida contra la solicitud original (APROBADO o REQUIERE_CAMBIOS)

Cada rol puede llamar `request_tools(["tool"])` para activar más tools dinámicamente, o `delegate_agent("nombre", "tarea", "contexto")` para delegar a un subagente.

### Tool Access Policy
`RoleRuntimeView` filtra tools por rol. Las categorías de tools son: `read`, `write`, `execute`, `delete`, `meta`, `hardware`, `media_input`, `web`, `sandbox_execute`. Las categorías peligrosas (delete, hardware, media, web, sandbox_execute) son **opt-in**. `--read-only` desactiva todas las categorías mutantes.

### Prompt Registry
`prompts/registry.json` define templates por modo, referenciando archivos en `prompts/system/`, `prompts/context/`, `prompts/modes/`. El servidor renderiza las secciones. Ejemplo de entrada:
```json
{
  "id": "mcp.tool_workflow",
  "modes": ["tool_workflow", "worker"],
  "sections": ["system/base.md", "context/runtime_context.md", "modes/tool_workflow.md"]
}
```

### Subagentes custom (Markdown)
Se cargan desde `~/.mcp_agents/` o `<base_dir>/.mcp_agents/` como archivos `.md` con frontmatter YAML:
```markdown
---
name: auditor
tool_access: read_only
tools: [pwd, listdir, readfile, search_code]
---
Eres auditor. Revisa riesgos...
```

### Skills (Markdown)
Se cargan desde `~/.mcp_skills/` o `<base_dir>/.mcp_skills/`. Un skill inyecta una directiva en el prompt del agente para la sesión activa:
```markdown
---
name: concise-responder
description: Responde siempre en 3 líneas o menos
scope: all
---
Responde siempre con un máximo de 3 líneas. Sé directo.
```
Se activa con `--skill <nombre>` o con `/skill activate <nombre>` en el REPL.

### Memoria Persistente
`MemoryStore` persiste pares clave-valor en SQLite (sobre `SQLiteKVCacheStore`) en dos scopes:
- **Proyecto**: `<base_dir>/.mcp_memory/` — preferencias del proyecto actual.
- **Usuario**: `~/.mcp_memory/` — preferencias globales del usuario.

La memoria se inyecta automáticamente en el contexto del agente. Si Ollama expone `nomic-embed-text`, la búsqueda usa embeddings; si no, cae back a BM25 textual. Deshabilitar con `--no-memory`.

### Specification-Driven Development (SDD)
Cada subsistema mayor tiene un `.sdd.md` junto al código que define sus límites: qué posee, qué no posee, interfaces públicas, reglas de comportamiento, y mapa de tests. Jerarquía de autoridad ante conflictos: **Usuario → Código actual → Spec → README → Roadmaps**.

Los specs `.sdd.md` están en:
- `src/mcp/mcp_runtime.sdd.md`
- `src/mcp_client/mcp_client.sdd.md`
- `src/mcp_server/mcp_server.sdd.md`

## Persistencia local (no commitear)

| Directorio | Contenido |
|---|---|
| `.mcp_sessions/` | Conversaciones SQLite (sin campo `thinking`) |
| `.mcp_traces/` | Eventos agenticos SQLite (si `trace-capture` activo) |
| `.mcp_cache/` | KV cache SQLite con TTL |
| `.mcp_memory/` | Memoria de proyecto SQLite (clave-valor persistente) |
| `~/.mcp_memory/` | Memoria de usuario SQLite (global entre proyectos) |
| `.mcp_sandbox/` | Archivos del sandbox web |

## Convenciones de código

- 4-space indentation, type hints en funciones públicas, `snake_case` para functions/variables/modules, `PascalCase` para classes y modelos Pydantic.
- Config parsing va en `settings/` o `config/`. Transport concerns en `transport/`. Lógica de comandos en `commands/` o `slash/`.
- Tests en `tests/` con nombres `test_<subsistema>_<comportamiento>.py`.
- Actualizar el `.sdd.md` correspondiente si cambia la interfaz pública de un módulo.
