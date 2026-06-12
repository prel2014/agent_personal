# Trazabilidad SQLite Para Dataset

El cliente puede persistir ejecuciones agenticas en SQLite para construir
datasets a partir de prompts, fases, tool calls, revisiones, autowrite y
respuestas finales.

La captura esta apagada por defecto para no guardar prompts ni rutas locales sin
intencion explicita.

## Activacion

```powershell
python -m src.mcp_client.commands.cli `
  --trace-capture full `
  --trace-db-path .mcp_traces/agent_traces.sqlite `
  ask "implementa una mejora"
```

Variables equivalentes:

```powershell
$env:MCP_CLIENT_TRACE_CAPTURE="full"
$env:MCP_CLIENT_TRACE_DB_PATH=".mcp_traces/agent_traces.sqlite"
$env:MCP_CLIENT_TRACE_THINKING="raw"
```

Tambien existen aliases historicos:

- `MCP_TRACE_CAPTURE`
- `MCP_TRACE_DB_PATH`
- `MCP_TRACE_THINKING`

## Modos

- `off`: no crea DB ni registra eventos.
- `metadata`: guarda etapas, nodos, modelos, duraciones, errores, nombres de
  tools y conteos, pero omite contenido completo.
- `full`: guarda conversaciones, resultados de tools y ejemplos dataset
  sanitizados.

Politica de `thinking`:

- `off`: no guarda razonamiento.
- `summary`: guarda solo marcador con cantidad de caracteres.
- `raw`: guarda texto crudo sanitizado.

Cuando `--trace-capture` esta activo y no se indica `--trace-thinking`, el
cliente usa `raw`. Cuando trace esta apagado, `thinking` tambien queda apagado.

## Proteccion Remota

Si `--server-url` apunta a un host no loopback, estos modos requieren opt-in:

- `--trace-capture full`
- `--trace-thinking raw`

Usa:

```powershell
python -m src.mcp_client.commands.cli `
  --server-url http://192.168.1.10:8000 `
  --allow-remote-sensitive-tracing `
  --trace-capture full `
  ask "tarea"
```

Esto evita persistir prompts, reasoning y outputs sensibles por accidente
cuando el razonamiento corre contra un servidor remoto.

## Tablas

- `runs`: ejecucion completa del usuario.
- `phases`: fases como `planner`, `worker`, `reviewer`, `single` o
  `direct_answer`.
- `events`: eventos append-only de etapas, respuestas, tools, autowrite y
  errores.
- `messages`: mensajes de usuario, assistant y tools.
- `artifacts`: archivos escritos por autowrite.
- `dataset_examples`: ejemplos listos para exportar.

La DB de trazas puede contener prompts, rutas locales, outputs de tools y
fragmentos de archivos. No debe commitearse.

## Exportacion JSONL

```powershell
python -m src.mcp_client.commands.cli export-dataset `
  --db-path .mcp_traces/agent_traces.sqlite `
  --example-type sft_conversation `
  --output datasets/sft_conversation.jsonl
```

Para exportar el resultado consolidado del equipo:

```powershell
python -m src.mcp_client.commands.cli export-dataset `
  --db-path .mcp_traces/agent_traces.sqlite `
  --example-type team_final `
  --output datasets/team_final.jsonl
```

Opciones:

- `--db-path`: DB de trazas. Si se omite, usa `--trace-db-path` o el default
  cuando aplica.
- `--output`: archivo JSONL de salida. Es obligatorio.
- `--example-type`: tipo de ejemplo, por defecto `sft_conversation`.
- `--limit`: maximo de ejemplos exportados.

Cada linea exportada incluye `input`, `output`, `tags`, `run_id` y `phase_id`.

## Buenas Practicas

- Usa `metadata` para auditoria ligera.
- Usa `full` solo cuando realmente vayas a construir dataset o depurar un flujo.
- Borra o protege `.mcp_traces/` como dato sensible.
- No mezcles trazas de proyectos con distinta sensibilidad en la misma DB.
- Documenta en el PR si una feature nueva cambia contenido persistido.
