'use client';

export type OutputPanelResult = {
  decisionRecordJson: string;
  normalizedRequestJson: string;
  notes: string[];
};

interface OutputPanelProps {
  result: OutputPanelResult | null;
  error: string | null;
  isRunning: boolean;
  durationMs: number | null;
  onCopyDecisionRecord: () => void;
}

export default function OutputPanel({
  result,
  error,
  isRunning,
  durationMs,
  onCopyDecisionRecord,
}: OutputPanelProps) {
  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-300">Decision Record (v1)</span>
          {durationMs !== null && (
            <span className="text-xs text-gray-500">{durationMs.toFixed(0)}ms</span>
          )}
        </div>
        <button
          onClick={onCopyDecisionRecord}
          disabled={!result || isRunning}
          className={`text-xs px-3 py-1.5 rounded-md border transition ${
            !result || isRunning
              ? 'border-gray-700 text-gray-500 cursor-not-allowed'
              : 'border-gray-600 text-gray-200 hover:border-cyan-500 hover:text-white'
          }`}
        >
          Copy JSON
        </button>
      </div>

      <div className="p-4 min-h-[260px] max-h-[520px] overflow-auto">
        {isRunning ? (
          <div className="flex items-center gap-2 text-gray-400">
            <div className="w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            <span>Evaluating…</span>
          </div>
        ) : error ? (
          <div className="text-red-400 font-mono text-sm whitespace-pre-wrap">{error}</div>
        ) : result ? (
          <div className="space-y-4">
            {result.notes.length > 0 && (
              <div className="rounded-md border border-gray-700 bg-gray-800/40 p-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                  Notes
                </div>
                <ul className="text-sm text-gray-300 list-disc pl-5 space-y-1">
                  {result.notes.map((n, i) => (
                    <li key={i}>{n}</li>
                  ))}
                </ul>
              </div>
            )}

            <pre className="text-gray-200 font-mono text-xs whitespace-pre-wrap">
              {result.decisionRecordJson}
            </pre>

            <details className="rounded-md border border-gray-700 bg-gray-800/20 p-3">
              <summary className="cursor-pointer text-sm text-gray-300">
                Show normalized request
              </summary>
              <pre className="mt-3 text-gray-200 font-mono text-xs whitespace-pre-wrap">
                {result.normalizedRequestJson}
              </pre>
            </details>
          </div>
        ) : (
          <div className="text-gray-500 text-sm">Click “Run gate” to generate a Decision Record.</div>
        )}
      </div>
    </div>
  );
}

