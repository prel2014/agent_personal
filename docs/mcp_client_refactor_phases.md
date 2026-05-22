# Fases De Refactor Del Cliente

Objetivo: hacer `mcp_client` mas expandible sin fragmentarlo en exceso. La idea es separar composicion, workflows, interfaz interactiva e integraciones, manteniendo la compatibilidad actual mientras se migra por partes.

## Fase 1. Encapsular el motor de workflows
- [x] Crear un paquete `workflows/` para concentrar la composicion y ejecucion de flujos.
- [x] Mover la decision de routing y la orquestacion de ejecucion fuera de `sessions/agent.py`.
- [x] Mantener `AgentWorkflow` y `AgentTeamOrchestrator` como implementaciones existentes detras de una fachada nueva.
- [ ] Agregar pruebas de routing entre modo directo, modo team y modo nunca.

## Fase 2. Separar la superficie interactiva
- [x] Aislar el ciclo REPL para que no conozca detalles de composicion interna.
- [x] Mantener `slash/` como adaptador de comandos, no como orquestador.
- [x] Definir un punto unico para manejar preguntas del usuario, hotkeys y streaming.

## Fase 3. Agrupar integraciones
- [x] Mantener transporte, renderizado, autowrite y trazas como adaptadores independientes.
- [x] Agrupar los mixins de cache, sesiones y lifecycle del cliente en `integrations/`.
- [x] Reducir imports cruzados entre `sessions/`, `app/` y `agentic/`.
- [x] Preparar una capa mas limpia para reemplazar adaptadores sin tocar workflows.

## Fase 4. Limpieza de compatibilidad
- [x] Revisar reexports y aliases antiguos.
- [x] Retirar rutas viejas solo cuando no haya consumidores.
- [x] Consolidar nombres y contratos publicos finales.

## Ajustes Posteriores
- [x] Planner sin tools: si el modelo emite una tool call en una fase sin tools, el cliente la convierte en texto util y no ejecuta la tool.
- [x] Worker sandbox-first: las tools del worker quedan limitadas al sandbox por defecto y solo salen al host si el usuario lo pide explicitamente.
- [x] Contexto multiarchivo: las tools de escritura y reemplazo devuelven preview/hash del archivo final para preservar contexto entre cambios.
- [x] Streaming Markdown: en salida rich se acumula la respuesta y se renderiza como Markdown al final del turno.
- [x] `thinking` sigue apagado por defecto y se alterna con `Ctrl+T` o `/thinking`.
- [x] Prueba de regresion para tool calls del planner sin tools.

## Hecho En Esta Iteracion
- [x] `src/mcp_client/workflows/registry.py`
- [x] `src/mcp_client/workflows/__init__.py`
- [x] `src/mcp_client/sessions/agent.py` delega la ejecucion al registry de workflows
- [x] `src/mcp_client/sessions/controller.py`
- [x] `src/mcp_client/sessions/repl.py` delega el ciclo interactivo al controller
- [x] `src/mcp_client/integrations/state.py`
- [x] `src/mcp_client/integrations/__init__.py`
- [x] `src/mcp_client/app/client.py` consume la capa de integraciones
- [x] `src/mcp_client/render/terminal.py` ahora imprime la barra de contexto durante la ejecucion
- [x] Eliminados los shims antiguos de compatibilidad de `agentic/`, `integrations/` y `sessions/`
- [x] `src/mcp_client/sessions/tool_call_compat.py` filtra tool calls no disponibles
- [x] `src/mcp_client/integrations/execution.py` conserva Markdown en streaming rich
