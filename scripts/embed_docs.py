#!/usr/bin/env python3
"""
Embed documentation and upload to Supabase (pgvector).

Usage:
    uv run python scripts/embed_docs.py

Required env vars (recommended):
    - OPENAI_API_KEY
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY

Optional (local convenience):
    - NEXT_PUBLIC_SUPABASE_URL (used as a fallback for SUPABASE_URL)
    - docs-site/.env.local (loaded if present and vars are missing)
"""

from __future__ import annotations

import importlib
import os
import re
import subprocess
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "docs"
CHUNK_SIZE = 200  # tokens (approximate) - reduced for better granularity
CHUNK_OVERLAP = 30


def _load_local_env_if_present() -> None:
    env_file = Path(__file__).parent.parent / "docs-site" / ".env.local"
    if not env_file.exists():
        return

    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key not in os.environ:
            os.environ[key] = value


def _import_clients():
    try:
        openai_module = importlib.import_module("openai")
        supabase_module = importlib.import_module("supabase")
    except ModuleNotFoundError:
        subprocess.run(["uv", "pip", "install", "openai", "supabase"], check=True)
        openai_module = importlib.import_module("openai")
        supabase_module = importlib.import_module("supabase")

    create_client = getattr(supabase_module, "create_client")
    return openai_module, create_client


def get_openai_client(openai_module) -> object:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")
    return openai_module.OpenAI(api_key=api_key)


def get_supabase_client(create_client_fn) -> object:
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return create_client_fn(url, key)


def extract_title(content: str, filename: str) -> str:
    frontmatter_match = re.search(
        r"^---\s*\n.*?title:\s*['\"]?(.+?)['\"]?\s*\n.*?---", content, re.DOTALL
    )
    if frontmatter_match:
        return frontmatter_match.group(1).strip()

    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    return filename.replace("-", " ").replace("_", " ").title()


def clean_content(content: str) -> str:
    content = re.sub(r"^---\s*\n.*?---\s*\n", "", content, flags=re.DOTALL)
    content = re.sub(r"\{%.*?%\}", "", content)
    content = re.sub(r"\{\{.*?\}\}", "", content)
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    tokens_per_chunk = int(chunk_size / 1.3)
    overlap_words = int(overlap / 1.3)

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + tokens_per_chunk, len(words))
        chunks.append(" ".join(words[start:end]))
        start = end - overlap_words
        if start >= len(words) - overlap_words:
            break
    return chunks


def get_embedding(openai_client, text: str) -> list[float]:
    response = openai_client.embeddings.create(model="text-embedding-ada-002", input=text)
    return response.data[0].embedding


def get_slug_from_path(filepath: Path, docs_dir: Path) -> str:
    relative = filepath.relative_to(docs_dir)
    slug = str(relative).replace(".md", "").replace("\\", "/")

    if slug == "index":
        return ""
    if slug.endswith("/index"):
        return slug[:-6]
    return slug


def main() -> None:
    _load_local_env_if_present()
    openai_module, create_client_fn = _import_clients()

    print("Embedding Lumyn documentation...")
    openai_client = get_openai_client(openai_module)
    supabase = get_supabase_client(create_client_fn)

    try:
        _ = get_embedding(openai_client, "lumyn embeddings smoke test")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        print("ERROR: OpenAI embedding call failed; refusing to clear existing embeddings.")
        print(f"Cause: {msg}")
        sys.exit(1)

    md_files = list(DOCS_DIR.glob("**/*.md"))
    print(f"Found {len(md_files)} markdown files")

    print("Clearing existing embeddings...")
    supabase.table("doc_embeddings").delete().neq("id", 0).execute()

    total_chunks = 0
    for filepath in md_files:
        if any(part.startswith("_") or part.startswith(".") for part in filepath.parts):
            continue

        content = filepath.read_text(encoding="utf-8")
        title = extract_title(content, filepath.stem)
        clean = clean_content(content)
        if not clean:
            continue

        slug = get_slug_from_path(filepath, DOCS_DIR)
        chunks = chunk_text(clean)

        for i, chunk in enumerate(chunks):
            embedding = get_embedding(openai_client, chunk)
            supabase.table("doc_embeddings").upsert(
                {
                    "slug": slug,
                    "title": title,
                    "chunk_index": i,
                    "content": chunk[:2000],
                    "embedding": embedding,
                },
                on_conflict="slug,chunk_index",
            ).execute()
            total_chunks += 1

    print(f"Done! Uploaded {total_chunks} total chunks.")


if __name__ == "__main__":
    main()
