-- Run this in Supabase SQL Editor (Dashboard -> SQL Editor -> New Query)

-- Enable pgvector extension
create extension if not exists vector;

-- Create embeddings table
create table if not exists doc_embeddings (
  id bigserial primary key,
  slug text not null,
  title text,
  chunk_index int not null,
  content text not null,
  embedding vector(1536),
  created_at timestamp with time zone default now(),

  -- Unique constraint to prevent duplicates
  unique(slug, chunk_index)
);

-- Create index for faster similarity search
create index if not exists doc_embeddings_embedding_idx
  on doc_embeddings
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Create similarity search function
create or replace function match_documents(
  query_embedding vector(1536),
  match_count int default 5,
  match_threshold float default 0.5
)
returns table (
  slug text,
  title text,
  content text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    doc_embeddings.slug,
    doc_embeddings.title,
    doc_embeddings.content,
    1 - (doc_embeddings.embedding <=> query_embedding) as similarity
  from doc_embeddings
  where 1 - (doc_embeddings.embedding <=> query_embedding) > match_threshold
  order by doc_embeddings.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Grant access to the anon role (for public API access)
grant usage on schema public to anon;
grant select on doc_embeddings to anon;
grant execute on function match_documents to anon;
