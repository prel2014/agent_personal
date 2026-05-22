# Trazabilidad SQLite Para Dataset

El cliente puede persistir ejecuciones agenticas en SQLite para construir datasets
personalizados a partir de prompts, planes, tool calls, revisiones y respuestas
finales.

## Activacion

Por defecto la captura esta apagada para no guardar prompts ni datos locales sin
intencion explicita.

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

## Modos

- `off`: no crea base de datos ni registra eventos.
- `metadata`: guarda etapas, nodos, modelos, duraciones, errores, tool calls y
  conteos de caracteres, pero omite contenido de mensajes, prompt final y dataset.
- `full`: guarda conversaciones, resultados de tools y ejemplos dataset
  sanitizados.

`thinking` se guarda crudo por defecto cuando `--trace-capture` esta activo.
`--trace-thinking` permite cambiar esa politica:

- `raw`: guarda el texto crudo sanitizado.
- `summary`: guarda solo marcador con cantidad de caracteres.
- `off`: no guarda razonamiento interno.

Si `--server-url` apunta a un host remoto no loopback, `--trace-capture full`
o `--trace-thinking raw` requieren `--allow-remote-sensitive-tracing`. Esto
evita persistir prompts, reasoning y salidas sensibles por accidente contra un
servidor remoto.

## Tablas

- `runs`: ejecucion completa del usuario.
- `phases`: fases como `planner`, `worker`, `reviewer`, `single` o
  `direct_answer`.
- `events`: eventos append-only de etapas, respuestas, tools y autowrite.
- `messages`: mensajes de entrada, respuestas assistant y resultados de tools.
- `artifacts`: archivos escritos por autowrite.
- `dataset_examples`: ejemplos listos para exportar.

## Exportacion JSONL

```powershell
python -m src.mcp_client.commands.cli export-dataset `
  --db-path .mcp_traces/agent_traces.sqlite `
  --example-type sft_conversation `
  --output datasets/sft_conversation.jsonl
```

Para exportar el resultado consolidado del flujo planner-worker-reviewer:

```powershell
python -m src.mcp_client.commands.cli export-dataset `
  --example-type team_final `
  --output datasets/team_final.jsonl
```

El exportador escribe una linea JSON por ejemplo con `input`, `output`, `tags`,
`run_id` y `phase_id`.
