# Specification-Driven Development Para Este Repo

## Objetivo

Este repo usa Specification-Driven Development (SDD) como contrato compartido
entre humanos y agentes. La spec no reemplaza los tests ni el codigo: reduce la
ambiguedad antes de cambiar codigo y deja trazable que comportamiento debe
mantenerse.

En este proyecto, SDD aplica a tres subsistemas:

- `src/mcp_client`: cliente agente, CLI/REPL, sesiones persistentes, autowrite y trazabilidad.
- `src/mcp_server`: orquestador HTTP hacia nodos Ollama.
- `src/mcp`: runtime local de tools, permisos y sandbox web.

## Como Se Lleva A Cabo Con Agentes

1. El humano define el objetivo del cambio.
2. El agente lee `.specdd/bootstrap.md` y la spec del subsistema.
3. Si la spec no cubre el cambio, primero propone o edita la spec.
4. El agente implementa el cambio minimo que cumple la spec.
5. El agente ejecuta el `Test Map` de la spec.
6. El agente reporta resultado, pruebas y cualquier desviacion.

La idea clave es que el agente no trabaja solo con prompts libres. Trabaja con
contratos locales que explican proposito, limites, interfaces publicas, reglas de
seguridad y criterios de aceptacion.

## Metodologia Adoptada

La practica se basa en estas reglas:

- Specs pequenas y cercanas al codigo que describen.
- Bootstrap global para que cualquier agente sepa como resolver autoridad.
- Contratos con `Owns` y `Does Not Own` para evitar refactors amplios.
- Interfaces publicas declaradas antes de modificar codigo.
- Reglas de seguridad explicitas para permisos, red, sandbox y trazas.
- `Acceptance Criteria` verificables.
- `Test Map` conectado a pruebas reales del repo.

Para este repo se eligio Markdown con sufijo `.sdd.md`. SpecDD usa normalmente
archivos `.sdd`; aqui se mantiene `.md` para legibilidad, previews y consistencia
con la documentacion existente.

## Como Documentaria Cambios Nuevos

Para una feature nueva:

1. Identificar el subsistema propietario.
2. Actualizar su `.sdd.md` con la nueva interfaz, reglas y tests esperados.
3. Implementar codigo.
4. Agregar o actualizar pruebas.
5. Actualizar README/docs si cambia el uso publico.

Para un bug:

1. Agregar el comportamiento esperado a `Behavior Rules` o `Failure Modes`.
2. Agregar un criterio de aceptacion que reproduzca el bug.
3. Implementar el fix.
4. Agregar test de regresion.

Para seguridad:

1. Actualizar primero `Security And Permissions`.
2. Declarar permisos nuevos como opt-in.
3. Probar denegacion por defecto y caso permitido.
4. Verificar que no se filtran secretos en trazas o outputs.

## Specs Del Repo

- `.specdd/bootstrap.md`: reglas globales para agentes.
- `.specdd/glossary.md`: vocabulario comun.
- `.specdd/spec-template.sdd.md`: plantilla para specs nuevas.
- `src/mcp_client/mcp_client.sdd.md`: contrato del cliente agente.
- `src/mcp_server/mcp_server.sdd.md`: contrato del orquestador HTTP.
- `src/mcp/mcp_runtime.sdd.md`: contrato del runtime local.
- `docs/hermes_level_cli_roadmap.md`: hoja de ruta de producto CLI.

## Fuentes Revisadas

- [SpecDD](https://specdd.ai/): propone specs locales, bootstrap para agentes y archivos fuente-adjacent como contrato de desarrollo.
- [OpenAI Codex](https://openai.com/index/introducing-codex/): describe agentes de software que leen, editan y prueban codigo en entornos aislados, con necesidad de revision humana.
- [OpenAI Codex cloud docs](https://platform.openai.com/docs/codex/overview): documenta delegacion de tareas a Codex en un entorno cloud aislado.
- [Agentic Coding Handbook: Spec-First Approach](https://tweag.github.io/agentic-coding-handbook/WORKFLOW_SPEC_FIRST_APPROACH/): recomienda empezar con una especificacion clara antes de implementar con agentes.

## Criterio Operativo

Un cambio esta listo cuando:

- La spec afectada describe el comportamiento deseado.
- El codigo cumple esa spec.
- Las pruebas del `Test Map` pasan o la limitacion queda documentada.
- La respuesta final del agente lista cambios, pruebas y riesgos restantes.
