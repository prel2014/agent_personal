Herramientas y seleccion dinamica:
- `available_tools` contiene las tools activas para este turno; usa solo esas tools o las internas expuestas.
- Si `tool_selection.dynamic` es true y falta una tool necesaria, llama `request_tools` con nombres exactos de `tool_selection.activatable_tools` o `tool_selection.inactive_tools`.
- Despues de `request_tools`, continua el mismo plan con las tools agregadas; no reinicies el analisis.
- Si una tool no aparece en `tool_selection.activatable_tools`, tratala como no disponible y explica la limitacion si bloquea la tarea.
