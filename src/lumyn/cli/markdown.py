from __future__ import annotations

from typing import Any


def _truncate_lines(lines: list[str], *, max_lines: int = 40, max_chars: int = 4000) -> list[str]:
    if max_lines <= 0 or max_chars <= 0:
        return []

    out: list[str] = []
    char_count = 0
    for line in lines:
        added = len(line) + 1
        if len(out) >= max_lines or char_count + added > max_chars:
            omitted_lines = len(lines) - len(out)
            out.append(f"... (truncated; omitted {omitted_lines} lines)")
            return out[:max_lines]
        out.append(line)
        char_count += added
    return out


def _format_obligation(item: dict[str, Any]) -> str:
    obligation_type = item.get("type")
    title = item.get("title")
    details = item.get("details")
    source = item.get("source")

    parts: list[str] = []
    if isinstance(obligation_type, str) and obligation_type:
        parts.append(f"type=`{obligation_type}`")
    if isinstance(title, str) and title:
        parts.append(f"title={title!r}")
    if isinstance(source, dict):
        stage = source.get("stage")
        rule_id = source.get("rule_id")
        if isinstance(stage, str) and isinstance(rule_id, str):
            parts.append(f"source=`{stage}:{rule_id}`")
    if isinstance(details, str) and details:
        parts.append(f"details={details!r}")
    return "- " + (" ".join(parts) if parts else str(item))


def render_ticket_summary_markdown(
    *,
    decision_id: str | None,
    created_at: str | None,
    verdict: str | None,
    reason_codes: list[str],
    policy_hash: str | None,
    context_digest: str | None,
    inputs_digest: str | None,
    context_ref: dict[str, Any] | None = None,
    interaction_ref: dict[str, Any] | None = None,
    memory_snapshot_digest: str | None = None,
    matched_rules: list[dict[str, Any]],
    obligations: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append(f"# Lumyn decision `{decision_id}`")
    if created_at is not None:
        lines.append(f"- created_at: `{created_at}`")
    lines.append(f"- verdict: `{verdict}`")
    lines.append(f"- reason_codes: `{', '.join(reason_codes) or '(none)'}`")
    lines.append(f"- policy_hash: `{policy_hash}`")
    lines.append(f"- context_digest: `{context_digest}`")
    if isinstance(context_ref, dict) and context_ref:
        if isinstance(context_ref.get("context_id"), str):
            lines.append(f"- context_id: `{context_ref.get('context_id')}`")
        if isinstance(context_ref.get("record_hash"), str):
            lines.append(f"- context_record_hash: `{context_ref.get('record_hash')}`")
    if isinstance(interaction_ref, dict) and interaction_ref:
        if isinstance(interaction_ref.get("mode"), str):
            lines.append(f"- interaction_mode: `{interaction_ref.get('mode')}`")
        if isinstance(interaction_ref.get("call_id"), str):
            lines.append(f"- call_id: `{interaction_ref.get('call_id')}`")
        if isinstance(interaction_ref.get("turn_id"), str):
            lines.append(f"- turn_id: `{interaction_ref.get('turn_id')}`")
        if isinstance(interaction_ref.get("turn_index"), int):
            lines.append(f"- turn_index: `{interaction_ref.get('turn_index')}`")
    lines.append(f"- inputs_digest: `{inputs_digest}`")
    if memory_snapshot_digest is not None:
        lines.append(f"- memory_snapshot_digest: `{memory_snapshot_digest}`")

    if matched_rules:
        lines.append("")
        lines.append("## Matched rules")
        for rule in matched_rules:
            lines.append(
                f"- `{rule.get('stage')}:{rule.get('rule_id')}` "
                f"effect=`{rule.get('effect')}` "
                f"reasons=`{rule.get('reason_codes')}`"
            )

    if obligations:
        lines.append("")
        lines.append("## Obligations")
        for item in obligations:
            lines.append(_format_obligation(item))

    lines = _truncate_lines(lines)
    return "\n".join(lines) + "\n"
