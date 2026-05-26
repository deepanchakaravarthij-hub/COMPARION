from __future__ import annotations

import ast
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

SEMANTIC_PROMPT_TEMPLATES = {
    "change_summary": (
        "Summarize major document differences by type, semantic label, and likely business impact."
    ),
    "risk_explanation": (
        "Explain why this change might introduce legal, financial, or compliance risk."
    ),
}

HIGH_RISK_RULE_TEMPLATES = {
    "finance": {
        "keywords": ["payment", "fee", "amount", "revenue", "tax", "invoice", "price", "cost"],
        "reason": "Finance-sensitive wording changed",
    },
    "legal": {
        "keywords": ["agreement", "clause", "liability", "termination", "indemnity", "warranty"],
        "reason": "Legal-contract language changed",
    },
    "compliance": {
        "keywords": ["compliance", "regulation", "policy", "gdpr", "pci", "sox", "audit"],
        "reason": "Compliance-related clause changed",
    },
}


@dataclass(frozen=True)
class SemanticOptions:
    enabled: bool
    similarity_threshold: float
    embedding_service: str
    local_summary_enabled: bool


def apply_semantic_layer(
    changes: list[dict[str, Any]],
    file_type: str,
    options: SemanticOptions,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not options.enabled:
        return changes, _empty_semantic(file_type, options)

    enriched = [dict(change) for change in changes]
    texts = [_extract_relevant_text(change.get("message", "")) for change in enriched]

    _annotate_semantic_labels(enriched, texts)
    _annotate_moved_pairs(enriched, texts, threshold=max(0.8, options.similarity_threshold))

    matches = _semantic_matches(
        changes=enriched,
        texts=texts,
        threshold=options.similarity_threshold,
    )
    summary = _local_summary(enriched, options.local_summary_enabled)
    risk_summary = _risk_summary(enriched)

    semantic_payload = {
        "embedding_service": options.embedding_service,
        "similarity_threshold": options.similarity_threshold,
        "prompt_templates": SEMANTIC_PROMPT_TEMPLATES,
        "risk_rule_templates": HIGH_RISK_RULE_TEMPLATES,
        "semantic_matches": matches,
        "summary": summary,
        "risk_summary": risk_summary,
        "provenance": {
            "method": "local-semantic-v1",
            "confidence": _semantic_confidence(enriched, matches),
            "local_summary_enabled": options.local_summary_enabled,
        },
    }
    return enriched, semantic_payload


def _empty_semantic(file_type: str, options: SemanticOptions) -> dict[str, Any]:
    return {
        "embedding_service": options.embedding_service,
        "similarity_threshold": options.similarity_threshold,
        "prompt_templates": SEMANTIC_PROMPT_TEMPLATES,
        "risk_rule_templates": HIGH_RISK_RULE_TEMPLATES,
        "semantic_matches": [],
        "summary": f"Semantic layer disabled for {file_type}",
        "risk_summary": {"high_risk_count": 0, "items": []},
        "provenance": {
            "method": "disabled",
            "confidence": 0.0,
            "local_summary_enabled": options.local_summary_enabled,
        },
    }


def _annotate_semantic_labels(changes: list[dict[str, Any]], texts: list[str]) -> None:
    for index, change in enumerate(changes):
        message = str(change.get("message", "")).lower()
        old_text, new_text = _extract_old_new(change.get("message", ""))
        label = "meaning-changed"
        score = 0.5

        if "moved" in message or "reordered" in message:
            label = "moved"
            score = 0.9
        elif old_text is not None and new_text is not None:
            similarity = _text_similarity(old_text, new_text)
            label = "wording-only" if similarity >= 0.6 else "meaning-changed"
            score = similarity
        elif change.get("type") in {"added", "removed"}:
            label = "meaning-changed"
            score = 0.45
        elif change.get("type") == "modified":
            similarity = _text_similarity(texts[index], str(change.get("message", "")))
            label = "wording-only" if similarity >= 0.7 else "meaning-changed"
            score = similarity

        change["semantic_label"] = label
        change["semantic_score"] = round(score, 3)


def _annotate_moved_pairs(
    changes: list[dict[str, Any]],
    texts: list[str],
    threshold: float,
) -> None:
    added = [i for i, change in enumerate(changes) if change.get("type") == "added"]
    removed = [i for i, change in enumerate(changes) if change.get("type") == "removed"]
    for add_index in added:
        best_removed = None
        best_score = 0.0
        for removed_index in removed:
            score = _text_similarity(texts[add_index], texts[removed_index])
            if score > best_score:
                best_score = score
                best_removed = removed_index
        if best_removed is None or best_score < threshold:
            continue
        changes[add_index]["semantic_label"] = "moved"
        changes[best_removed]["semantic_label"] = "moved"
        changes[add_index]["semantic_score"] = round(best_score, 3)
        changes[best_removed]["semantic_score"] = round(best_score, 3)


def _semantic_matches(
    changes: list[dict[str, Any]],
    texts: list[str],
    threshold: float,
) -> list[dict[str, Any]]:
    if len(changes) < 2:
        return []

    matches = []
    for left in range(len(changes)):
        for right in range(left + 1, len(changes)):
            score = _cosine_similarity_text(texts[left], texts[right])
            if score < threshold:
                continue
            if _same_anchor(
                changes[left].get("source_ref", {}),
                changes[right].get("source_ref", {}),
            ):
                continue
            matches.append(
                {
                    "left_id": changes[left]["id"],
                    "right_id": changes[right]["id"],
                    "score": round(score, 3),
                }
            )
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:100]


def _same_anchor(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = ["page", "slide", "sheet", "cell", "paragraph", "table", "row", "column", "part"]
    return all(left.get(key) == right.get(key) for key in keys)


def _local_summary(changes: list[dict[str, Any]], enabled: bool) -> str:
    if not enabled:
        return "Local summary disabled."
    if not changes:
        return "No semantic differences detected."
    label_counts = Counter(str(change.get("semantic_label", "unknown")) for change in changes)
    severity_counts = Counter(str(change.get("severity", "unknown")) for change in changes)
    top_labels = ", ".join(
        f"{label}={count}" for label, count in label_counts.most_common(3)
    )
    high_count = severity_counts.get("high", 0)
    return (
        f"Detected {len(changes)} changes. Semantic breakdown: {top_labels}. "
        f"High-severity changes: {high_count}."
    )


def _risk_summary(changes: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    for change in changes:
        text = str(change.get("message", "")).lower()
        if change.get("semantic_label") not in {"meaning-changed", "moved"}:
            continue
        for domain, template in HIGH_RISK_RULE_TEMPLATES.items():
            if any(keyword in text for keyword in template["keywords"]):
                findings.append(
                    {
                        "change_id": change.get("id"),
                        "domain": domain,
                        "reason": template["reason"],
                        "severity": change.get("severity", "medium"),
                    }
                )
    return {"high_risk_count": len(findings), "items": findings}


def _semantic_confidence(changes: list[dict[str, Any]], matches: list[dict[str, Any]]) -> float:
    if not changes:
        return 1.0
    average_score = (
        sum(float(change.get("semantic_score", 0.5)) for change in changes) / len(changes)
    )
    match_bonus = min(0.2, len(matches) * 0.005)
    return round(min(0.99, average_score + match_bonus), 3)


def _extract_relevant_text(message: str) -> str:
    old_text, new_text = _extract_old_new(message)
    if old_text is not None and new_text is not None:
        return f"{old_text} {new_text}".strip()
    return _normalize_for_similarity(message)


def _extract_old_new(message: str) -> tuple[str | None, str | None]:
    if "->" not in message:
        return None, None
    _, right = message.split(":", 1) if ":" in message else ("", message)
    left_text, right_text = right.split("->", 1)
    left = _safe_literal(left_text.strip())
    right_value = _safe_literal(right_text.strip())
    if left is None or right_value is None:
        return None, None
    return left, right_value


def _safe_literal(value: str) -> str | None:
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        parsed = value.strip("'\" ")
    if not isinstance(parsed, str):
        parsed = str(parsed)
    return parsed


def _text_similarity(left: str, right: str) -> float:
    left_tokens = set(_normalize_for_similarity(left).split())
    right_tokens = set(_normalize_for_similarity(right).split())
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _normalize_for_similarity(text: str) -> str:
    return " ".join(re.sub(r"[^a-zA-Z0-9\s]", " ", text).lower().split())


def _cosine_similarity_text(left: str, right: str) -> float:
    left_counts = Counter(_normalize_for_similarity(left).split())
    right_counts = Counter(_normalize_for_similarity(right).split())
    if not left_counts and not right_counts:
        return 1.0
    if not left_counts or not right_counts:
        return 0.0
    keys = set(left_counts) | set(right_counts)
    dot = sum(left_counts[key] * right_counts[key] for key in keys)
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
