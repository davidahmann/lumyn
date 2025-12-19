---
title: Semantic search + GitHub Pages deployment
description: How to deploy the docs-site and run semantic search indexing without committing secrets.
---

This repository is public. Do not commit secrets.

## Secrets you will need

### GitHub Actions (repo secrets)

Configure these in GitHub: Settings → Secrets and variables → Actions → New repository secret.

- `SUPABASE_URL`: your Supabase project URL (not sensitive, but keep as a secret for consistency)
- `SUPABASE_SERVICE_ROLE_KEY`: **secret** (server-side only)
- `OPENAI_API_KEY`: **secret** (server-side only)
- `NEXT_PUBLIC_SUPABASE_URL`: Supabase URL used by the static docs site to call the Edge Function (safe to expose)

### Supabase (project secrets)

Configure these in Supabase: Project → Settings → Secrets.

- `OPENAI_API_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

`SUPABASE_URL` is automatically available inside Supabase Edge Functions as `SUPABASE_URL`.

## GitHub Actions workflows

These workflows are configured to keep secrets out of the repo:

- `.github/workflows/docs.yml`: builds `docs-site/` and deploys static output to GitHub Pages
- `.github/workflows/embed-docs.yml`: re-embeds `docs/**` into Supabase pgvector on docs changes

## Supabase Edge Function deployment

Semantic search depends on a Supabase Edge Function:

- `supabase/functions/search/index.ts`

Deploy it with the Supabase CLI (recommended), and set secrets in Supabase:

- `OPENAI_API_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

## Rotation policy

If a credential is ever pasted into a public issue, PR, or chat, rotate it immediately and assume compromise.
