import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.38.4';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const OPENAI_DISABLE_SECONDS_ON_AUTH_ERROR = 10 * 60; // 10 minutes
let openAiDisabledUntilMs: number | null = null;
let openAiDisabledReason: string | null = null;
let lastOpenAiKeyFingerprint: string | null = null;

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { query } = await req.json();

    if (!query || typeof query !== 'string') {
      return new Response(JSON.stringify({ error: 'Query is required' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const openaiKey = Deno.env.get('OPENAI_API_KEY');
    if (!openaiKey) {
      return new Response(JSON.stringify({ error: 'Missing OPENAI_API_KEY' }), {
        status: 503,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const fingerprint = `len:${openaiKey.length}`;
    if (lastOpenAiKeyFingerprint !== fingerprint) {
      lastOpenAiKeyFingerprint = fingerprint;
      openAiDisabledUntilMs = null;
      openAiDisabledReason = null;
    }

    const nowMs = Date.now();
    if (openAiDisabledUntilMs && nowMs < openAiDisabledUntilMs) {
      return new Response(
        JSON.stringify({
          error: 'Search temporarily disabled',
          detail: openAiDisabledReason || 'OpenAI authentication failed',
          retry_after_s: Math.max(1, Math.ceil((openAiDisabledUntilMs - nowMs) / 1000)),
        }),
        {
          status: 503,
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/json',
            'Retry-After': String(
              Math.max(1, Math.ceil((openAiDisabledUntilMs - nowMs) / 1000)),
            ),
          },
        },
      );
    }

    const openaiResponse = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${openaiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'text-embedding-ada-002',
        input: query,
      }),
    });

    if (!openaiResponse.ok) {
      const error = await openaiResponse.text();
      console.error('OpenAI error:', error);
      if (openaiResponse.status === 401 || openaiResponse.status === 403) {
        openAiDisabledUntilMs = Date.now() + OPENAI_DISABLE_SECONDS_ON_AUTH_ERROR * 1000;
        openAiDisabledReason = 'Invalid OpenAI API key (401/403). Update Supabase secret and redeploy.';
      }
      return new Response(JSON.stringify({ error: 'Embedding generation failed' }), {
        status: openaiResponse.status === 401 || openaiResponse.status === 403 ? 503 : 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const { data } = await openaiResponse.json();
    const queryEmbedding = data[0].embedding;

    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data: results, error } = await supabase.rpc('match_documents', {
      query_embedding: queryEmbedding,
      match_count: 5,
      match_threshold: 0.5,
    });

    if (error) {
      console.error('Supabase error:', error);
      return new Response(JSON.stringify({ error: 'Search failed' }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const seen = new Set<string>();
    const deduped = (results || []).filter((item: { slug: string }) => {
      if (seen.has(item.slug)) return false;
      seen.add(item.slug);
      return true;
    });

    return new Response(JSON.stringify({ results: deduped }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});

