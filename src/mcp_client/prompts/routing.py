from __future__ import annotations


def build_routing_classifier_prompt(prompt: str) -> str:
    return (
        "Clasifica si el prompt del usuario debe responderse directo o con "
        "flujo planner-worker-reviewer.\n"
        "Usa direct para preguntas simples, explicaciones cortas o conversacion.\n"
        "Usa team para editar archivos, investigar, depurar, usar tools, web, hardware, "
        "o tareas multi-paso.\n"
        'Devuelve solo JSON: {"route":"direct|team","confidence":0.0,"reason":"..."}.\n\n'
        f"Prompt:\n{prompt}"
    )
