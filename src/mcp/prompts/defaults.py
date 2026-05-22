from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptDefinition:
    name: str
    description: str
    arguments: tuple[str, ...]
    template: str
    defaults: dict[str, str] = field(default_factory=dict)

    def render(self, **kwargs) -> str:
        values = dict(self.defaults)
        values.update(kwargs)

        missing = [arg for arg in self.arguments if arg not in values]
        if missing:
            raise ValueError(
                f"Faltan argumentos para el prompt '{self.name}': {', '.join(missing)}"
            )

        return self.template.format(**values)


PROMPTS: dict[str, PromptDefinition] = {
    "review_file": PromptDefinition(
        name="review_file",
        description="Revisa un archivo y detecta errores, riesgos y mejoras.",
        arguments=("path",),
        template=(
            "Revisa el archivo '{path}'. "
            "Explica que hace, detecta errores, riesgos, deuda tecnica y "
            "mejoras concretas."
        ),
    ),
    "summarize_directory": PromptDefinition(
        name="summarize_directory",
        description="Resume la estructura y el proposito de una carpeta.",
        arguments=("path",),
        defaults={"path": "."},
        template=(
            "Analiza la carpeta '{path}'. "
            "Resume su estructura, identifica archivos clave y explica "
            "como se relacionan."
        ),
    ),
    "plan_file_edit": PromptDefinition(
        name="plan_file_edit",
        description="Propone un plan antes de modificar un archivo.",
        arguments=("path", "objective"),
        template=(
            "Quiero modificar '{path}' con este objetivo: {objective}. "
            "Propone un plan de cambios paso a paso, riesgos y validaciones."
        ),
    ),
    "compare_files": PromptDefinition(
        name="compare_files",
        description="Compara dos archivos y explica diferencias importantes.",
        arguments=("path_a", "path_b"),
        template=(
            "Compara los archivos '{path_a}' y '{path_b}'. "
            "Explica diferencias funcionales, estructurales y posibles "
            "impactos."
        ),
    ),
    "safe_delete_check": PromptDefinition(
        name="safe_delete_check",
        description="Evalua si borrar un archivo parece seguro.",
        arguments=("path",),
        template=(
            "Antes de borrar '{path}', analiza si parece seguro hacerlo. "
            "Indica dependencias posibles, riesgos y que verificar antes "
            "de eliminarlo."
        ),
    ),
    "generate_readme": PromptDefinition(
        name="generate_readme",
        description="Genera un README basico a partir de una carpeta.",
        arguments=("path",),
        defaults={"path": "."},
        template=(
            "Genera un README para la carpeta '{path}'. "
            "Incluye proposito del proyecto, estructura principal, uso "
            "basico y notas importantes."
        ),
    ),
}


def get_prompt(name: str) -> PromptDefinition:
    prompt = PROMPTS.get(name)
    if prompt is None:
        raise KeyError(f"Prompt no encontrado: {name}")

    return prompt


def list_prompts() -> list[dict[str, object]]:
    return [
        {
            "name": prompt.name,
            "description": prompt.description,
            "arguments": list(prompt.arguments),
            "defaults": dict(prompt.defaults),
        }
        for prompt in PROMPTS.values()
    ]


def render_prompt(name: str, **kwargs) -> str:
    return get_prompt(name).render(**kwargs)
