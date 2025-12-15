## Summary

## Checklist
- [ ] Tests added/updated (if behavior changed)
- [ ] `uv run ruff format . && uv run ruff check .` clean
- [ ] `uv run mypy src` clean
- [ ] `uv run pytest -q` clean
- [ ] v0 schemas unchanged or evolved additively (breaking changes require v1)
- [ ] Determinism preserved (no ordering/time-based drift beyond `decision_id`/`created_at`)
