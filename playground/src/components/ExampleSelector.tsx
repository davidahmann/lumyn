'use client';

import { PlaygroundExample, examples } from '@/lib/examples';

interface ExampleSelectorProps {
  selectedId: string;
  onSelect: (example: PlaygroundExample) => void;
}

export default function ExampleSelector({
  selectedId,
  onSelect,
}: ExampleSelectorProps) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-300 mb-2">
        Examples
      </label>
      <div className="grid grid-cols-1 gap-2">
        {examples.map((example) => (
          <button
            key={example.id}
            onClick={() => onSelect(example)}
            className={`text-left p-3 rounded-lg border transition-all ${
              selectedId === example.id
                ? 'border-green-500 bg-green-500/10'
                : 'border-gray-700 hover:border-gray-600 bg-gray-800/50'
            }`}
          >
            <div className="text-sm font-medium text-white mb-1">{example.title}</div>
            <p className="text-xs text-gray-400">{example.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
