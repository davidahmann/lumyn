'use client';

import { useState, useEffect } from 'react';
import SearchModal from './SearchModal';

interface SearchButtonProps {
  variant?: 'sidebar' | 'header';
}

export default function SearchButton({ variant = 'sidebar' }: SearchButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Handle Cmd/Ctrl + K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (variant === 'header') {
    return (
      <>
        <button
          onClick={() => setIsOpen(true)}
          className="p-2 text-gray-400 hover:text-white"
          aria-label="Search"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </button>
        <SearchModal isOpen={isOpen} onClose={() => setIsOpen(false)} />
      </>
    );
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-400 bg-gray-800/50 hover:bg-gray-800 rounded-lg border border-gray-700 transition-colors group"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <span className="flex-1 text-left">Search docs...</span>
        <kbd className="hidden sm:inline-flex px-1.5 py-0.5 text-xs text-gray-500 bg-gray-700 rounded">
          <span className="text-xs">Cmd</span>K
        </kbd>
      </button>
      <SearchModal isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  );
}
