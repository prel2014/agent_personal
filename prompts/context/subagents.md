Catalogo de subagentes:
- Si `available_tools` incluye `delegate_agent`, puedes delegar subtareas acotadas a un subagente del arreglo `subagents`.
- El argumento `agent` de `delegate_agent` debe ser exactamente el campo `name` del catalogo.
- Delega solo tareas autocontenidas con contexto minimo: inspeccion, revision, validacion o ejecucion aislada.
- Usa el resumen devuelto por el subagente como evidencia auxiliar; no lo trates como sustituto de resultados de tools locales cuando necesitas verificar archivos.
