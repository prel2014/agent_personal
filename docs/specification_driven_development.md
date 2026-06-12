# Specification-Driven Development Para Este Repo

## Objetivo

Este repo usa specs Markdown como contrato compartido entre humanos y agentes.
La spec no reemplaza tests ni codigo; reduce ambiguedad antes de cambiar un
subsistema y deja claro que comportamiento debe conservarse.

Specs activas:

- `src/mcp_client/mcp_client.sdd.md`
- `src/mcp_server/mcp_server.sdd.md`
- `src/mcp/mcp_runtime.sdd.md`

## Autoridad

Cuando hay conflicto, la autoridad practica es:

1. Instrucciones del usuario y `AGENTS.md`.
2. Codigo actual y tests existentes.
3. Spec del subsistema afectado.
4. README y guias en `docs/`.
5. Roadmaps o planes historicos.

Si una spec contradice el codigo actual, el cambio correcto es actualizar la
spec o agregar pruebas que formalicen la nueva regla antes de depender de ella.

## Subsistemas

- `src/mcp_client`: cliente agente, CLI/REPL, sesiones persistentes, autowrite,
  subagentes, prompt routing y trazabilidad.
- `src/mcp_server`: orquestador HTTP hacia nodos Ollama, auth, discovery,
  auto-promocion y prompt rendering.
- `src/mcp`: runtime local de tools, permisos, auditoria, KV, Git, datos,
  hardware/media y sandbox web.

## Flujo De Trabajo Con Agentes

1. Identificar el subsistema propietario.
2. Leer la spec `.sdd.md` de ese subsistema.
3. Si cambia una interfaz publica, regla de seguridad o modo de fallo,
   actualizar la spec junto al codigo.
4. Implementar el cambio minimo que respeta los limites `Owns` y
   `Does Not Own`.
5. Ejecutar el `Test Map` actualizado o documentar la limitacion.
6. Actualizar README/docs si cambia el uso publico.

## Como Documentar Cambios

Feature nueva:

1. Agregar interfaz, reglas y acceptance criteria en la spec propietaria.
2. Implementar codigo.
3. Agregar o actualizar pruebas.
4. Actualizar README/docs si el usuario debe cambiar comandos, flags o flujo.

Bug:

1. Agregar comportamiento esperado a `Behavior Rules` o `Failure Modes`.
2. Agregar test de regresion.
3. Implementar fix.

Seguridad:

1. Actualizar `Security And Permissions`.
2. Mantener permisos peligrosos como opt-in.
3. Probar denegacion por defecto y caso permitido.
4. Verificar que no se filtran secretos en trazas, sesiones o outputs.

## Reglas De Mantenimiento

- Mantener specs pequenas y cercanas al codigo.
- Evitar specs aspiracionales en archivos `.sdd.md`; los roadmaps van en
  `docs/`.
- El `Test Map` debe nombrar tests que existen o indicar explicitamente que
  falta cobertura.
- No agregar una tool sin categoria de permiso y prueba minima.
- No agregar flags publicos sin documentarlos en README o en una guia.

## Fuentes Internas

- `README.md`: entrada de usuario y comandos principales.
- `docs/arquitectura_y_operacion.md`: mapa transversal del proyecto.
- `docs/uso_orquestador_ollama_distribuido.md`: despliegue con Ollama local/LAN.
- `docs/trazabilidad_dataset_sqlite.md`: persistencia y export de trazas.
- `docs/plan_sandbox_web_tools.md`: estado y criterios del sandbox web.
- `docs/hermes_level_cli_roadmap.md`: direccion de producto.

## Criterio Operativo

Un cambio esta listo cuando:

- La spec afectada describe el comportamiento deseado.
- El codigo cumple esa spec.
- Las pruebas relevantes pasan o la limitacion queda documentada.
- La documentacion publica refleja cualquier cambio visible para usuarios.
