'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';

interface SearchResult {
  slug: string;
  title: string;
  content: string;
  similarity: number;
}

// Supabase URL - hardcoded as fallback since env vars can be flaky with static export
const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://ycneyxgsifdvkcrveyal.supabase.co';

const POPULAR_QUERIES = [
  // Incident Response / SRE Persona
  { query: 'How do I debug a blocked decision?', href: '/blog/ai-incident-response-replay' },
  { query: 'Replay a past decision for incident response', href: '/docs/replay-guarantees' },

  // Compliance / Audit Persona
  { query: 'What is a Decision Record?', href: '/blog/what-is-a-decision-record' },
  { query: 'How to prove AI decisions are deterministic?', href: '/docs/replay-guarantees' },

  // Engineering / Integration Persona
  { query: 'Decision Records vs telemetry logs', href: '/blog/decision-logs-vs-telemetry' },
  { query: 'Quickstart guide', href: '/docs/quickstart' },

  // AI/ML / Memory Persona
  { query: 'How does memory labeling work?', href: '/docs/memory' },
  { query: 'What are stable reason codes?', href: '/blog/reason-codes-are-a-contract' },
];

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setQuery('');
      setResults([]);
      setHasSearched(false);
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen, onClose]);

  const search = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    setIsLoading(true);
    setHasSearched(true);

    try {
      // Call Supabase Edge Function for semantic search
      const response = await fetch(`${SUPABASE_URL}/functions/v1/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!response.ok) throw new Error('Search failed');

      const data = await response.json();
      setResults(data.results || []);
    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    search(query);
  };

  const handlePopularClick = (item: typeof POPULAR_QUERIES[0]) => {
    setQuery(item.query);
    search(item.query);
  };

  const getDocPath = (slug: string) => {
    if (!slug) return '/docs';
    if (slug.startsWith('blog/')) return `/${slug}`;
    return `/docs/${slug}`;
  };

  if (!isOpen) return null;

  return (
    <div className="search-modal-overlay fixed inset-0 z-[9999] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm">
      <div
        ref={modalRef}
        className="w-full max-w-2xl bg-gray-900 rounded-xl shadow-2xl border border-gray-700 overflow-hidden"
      >
        {/* Search Input */}
        <form onSubmit={handleSubmit} className="relative">
          <svg
            className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search documentation..."
            className="w-full pl-12 pr-4 py-4 bg-transparent text-white placeholder-gray-400 border-b border-gray-700 focus:outline-none focus:border-cyan-500"
          />
          {isLoading && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2">
              <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </form>

        {/* Content */}
        <div className="max-h-[60vh] overflow-y-auto">
          {/* Popular Queries (show when no search) */}
          {!hasSearched && (
            <div className="p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                Popular searches
              </p>
              <div className="flex flex-wrap gap-2">
                {POPULAR_QUERIES.map((item) => (
                  <button
                    key={item.query}
                    onClick={() => handlePopularClick(item)}
                    className="px-3 py-1.5 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-full transition-colors"
                  >
                    {item.query}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Search Results */}
          {hasSearched && !isLoading && (
            <div className="p-4">
              {results.length > 0 ? (
                <>
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                    {results.length} result{results.length !== 1 ? 's' : ''}
                  </p>
                  <div className="space-y-2">
                    {results.map((result, i) => (
                      <Link
                        key={`${result.slug}-${i}`}
                        href={getDocPath(result.slug)}
                        onClick={onClose}
                        className="block p-3 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors group"
                      >
                        <h3 className="font-medium text-white group-hover:text-cyan-400 transition-colors mb-1">
                          {result.title}
                        </h3>
                        <p className="text-sm text-gray-400 line-clamp-2">
                          {result.content.substring(0, 150)}...
                        </p>
                      </Link>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-400">No results found for &quot;{query}&quot;</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Try different keywords or browse the documentation
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between text-xs text-gray-500">
          <span>
            <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-400">Enter</kbd> to search
          </span>
          <span>
            <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-400">Esc</kbd> to close
          </span>
        </div>
      </div>
    </div>
  );
}
