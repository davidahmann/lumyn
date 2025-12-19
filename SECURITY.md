# Security Policy

## Reporting a vulnerability

Please do not open public issues for security vulnerabilities.

Preferred: open a GitHub Security Advisory for this repository and include:
- a description of the issue and impact
- steps to reproduce (or a PoC)
- affected versions/commits if known

If you cannot use GitHub advisories, open a GitHub issue titled `SECURITY: request contact` and we’ll coordinate a private channel.

## Supported versions

This project is early-stage OSS. Security fixes are applied to `main` and shipped in the next tagged release.

## Secrets management

Do not commit credentials or API keys to this public repository.

- Local development secrets belong in `.env` files (ignored by git) or your shell environment.
- GitHub Actions should use repository secrets (Settings → Secrets and variables → Actions).
- Supabase Edge Functions should use Supabase secrets (Project → Settings → Secrets).
- Treat `SUPABASE_SERVICE_ROLE_KEY` and `OPENAI_API_KEY` as highly sensitive server-side secrets.

If a secret is accidentally shared or committed, rotate it immediately and assume compromise.
