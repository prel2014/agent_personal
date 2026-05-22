from __future__ import annotations

import re
from urllib.parse import urlparse

from .models import NodeAutoPromotionSettings, NodeProbeResult, OllamaNodeConfig
from .probe import OllamaNodeProbe

AUTO_MODEL_VALUES = {"", "auto", "discover", "discovery", "detectar"}

FALLBACK_AUTO_MODEL = "qwen3"

EMBEDDING_MODEL_KEYWORDS = (
    "embed",
    "embedding",
    "nomic-embed",
    "bge",
    "minilm",
    "e5-",
)

CODE_MODEL_KEYWORDS = (
    "coder",
    "codestral",
    "codegemma",
    "deepseek-coder",
    "starcoder",
    "devstral",
)

VISION_MODEL_KEYWORDS = (
    "llava",
    "bakllava",
    "moondream",
    "minicpm-v",
    "qwen-vl",
    "qwen2-vl",
    "qwen2.5-vl",
    "vision",
    "-vl",
)

REASONING_MODEL_KEYWORDS = (
    "qwen3",
    "deepseek-r1",
    "qwq",
    "openthinker",
    "reason",
)

GENERAL_MODEL_KEYWORDS = (
    "qwen",
    "llama",
    "mistral",
    "mixtral",
    "gemma",
    "phi",
    "deepseek",
)

MODEL_SIZE_PATTERN = re.compile(r"(?P<size>\d+(?:\.\d+)?)\s*b", re.IGNORECASE)

def _infer_auto_promoted_nodes(
    *,
    base_url: str,
    available_models: tuple[str, ...],
    settings: NodeAutoPromotionSettings,
    limit: int,
) -> list[OllamaNodeConfig]:
    role_selections: dict[str, tuple[str, int]] = {}
    for role in settings.normalized_roles():
        selection = _best_model_for_role(available_models, role)
        if selection is not None:
            role_selections[role] = selection

    grouped: dict[str, dict[str, object]] = {}
    for role, (model, score) in role_selections.items():
        entry = grouped.setdefault(model, {"roles": [], "score": score})
        entry["roles"].append(role)
        entry["score"] = max(int(entry["score"]), score)

    nodes: list[OllamaNodeConfig] = []
    url_fragment = _node_id_fragment(base_url)
    for model, entry in sorted(grouped.items(), key=lambda item: (-int(item[1]["score"]), item[0])):
        if len(nodes) >= limit:
            break
        roles = tuple(sorted(str(role) for role in entry["roles"]))
        score = int(entry["score"])
        node_id = f"auto:{url_fragment}:{_node_id_fragment(model)}"
        nodes.append(
            OllamaNodeConfig(
                node_id=node_id,
                base_url=base_url,
                model=model,
                roles=roles,
                enabled=True,
                priority=max(1, settings.priority - min(score, 120)),
                is_local=False,
                source="auto_promoted",
                auto_promoted=True,
                promotion_reason=(
                    "auto_promoted_from_discovery:"
                    f"roles={','.join(roles)};score={score}"
                ),
            )
        )
    return nodes

def _resolve_local_model(
    *,
    requested_model: str,
    base_url: str,
    probe: OllamaNodeProbe,
) -> tuple[str, NodeProbeResult | None, str, str | None]:
    if not _is_auto_model(requested_model):
        return requested_model, None, "configured", None

    probe_result = probe.probe(base_url)
    selected_model = None
    if probe_result.reachable:
        selected_model = _best_default_model(probe_result.available_models)

    if selected_model:
        return (
            selected_model,
            probe_result,
            "auto_selected",
            "auto_selected_from_local_tags",
        )

    return (
        FALLBACK_AUTO_MODEL,
        probe_result,
        "auto_fallback",
        "auto_model_fallback_no_reachable_local_tags",
    )

def _is_auto_model(model: str | None) -> bool:
    return (model or "").strip().lower() in AUTO_MODEL_VALUES

def _best_default_model(available_models: tuple[str, ...]) -> str | None:
    for role in ("planner", "reviewer", "worker"):
        selection = _best_model_for_role(available_models, role)
        if selection is not None:
            return selection[0]
    return None

def _best_model_for_role(
    available_models: tuple[str, ...],
    role: str,
) -> tuple[str, int] | None:
    scored = [
        (model, _score_model_for_role(model, role))
        for model in available_models
    ]
    scored = [(model, score) for model, score in scored if score >= 0]
    if not scored:
        return None

    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored[0]

def _score_model_for_role(model: str, role: str) -> int:
    lowered = model.lower()
    if _contains_any(lowered, EMBEDDING_MODEL_KEYWORDS):
        return -1

    size_score = _model_size_score(lowered)
    role = role.lower()
    score = 5 + size_score

    if role == "worker":
        if _contains_any(lowered, CODE_MODEL_KEYWORDS):
            score += 90
        elif _contains_any(lowered, REASONING_MODEL_KEYWORDS + GENERAL_MODEL_KEYWORDS):
            score += 35
        else:
            return -1
        return score if score >= 25 else -1

    if role in {"planner", "reviewer"}:
        if _contains_any(lowered, REASONING_MODEL_KEYWORDS):
            score += 75
        elif _contains_any(lowered, GENERAL_MODEL_KEYWORDS):
            score += 45
        else:
            return -1

        if _contains_any(lowered, CODE_MODEL_KEYWORDS):
            score -= 60
        if _contains_any(lowered, VISION_MODEL_KEYWORDS):
            score -= 40
        return score if score >= 25 else -1

    if role == "vision":
        if not _contains_any(lowered, VISION_MODEL_KEYWORDS):
            return -1
        return score + 95

    if _contains_any(
        lowered,
        CODE_MODEL_KEYWORDS + REASONING_MODEL_KEYWORDS + GENERAL_MODEL_KEYWORDS,
    ):
        return score + 20
    return -1

def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)

def _model_size_score(model: str) -> int:
    match = MODEL_SIZE_PATTERN.search(model)
    if match is None:
        return 0
    try:
        size = float(match.group("size"))
    except ValueError:
        return 0
    return min(int(size), 40)

def _node_id_fragment(value: str) -> str:
    parsed = urlparse(value)
    candidate = parsed.netloc or parsed.path or value
    fragment = re.sub(r"[^a-zA-Z0-9_.-]+", "-", candidate).strip("-").lower()
    return fragment or "node"
