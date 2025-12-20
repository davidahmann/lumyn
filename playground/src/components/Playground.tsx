'use client';

import { useCallback, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import yaml from 'js-yaml';
import { examples, PlaygroundExample } from '@/lib/examples';
import { decideDemo } from '@/lib/evaluator';
import OutputPanel, { OutputPanelResult } from './OutputPanel';
import ExampleSelector from './ExampleSelector';

const CodeEditor = dynamic(() => import('./CodeEditor'), {
  ssr: false,
  loading: () => (
    <div className="h-[260px] bg-gray-900 rounded-lg flex items-center justify-center border border-gray-700">
      <span className="text-gray-500">Loading editor…</span>
    </div>
  ),
});

export default function Playground() {
  const [selectedExample, setSelectedExample] = useState<PlaygroundExample>(examples[0]);
  const [requestJson, setRequestJson] = useState(examples[0].requestJson);
  const [policyYaml, setPolicyYaml] = useState(examples[0].policyYaml);
  const [memoryJson, setMemoryJson] = useState(examples[0].memoryJson);

  const [result, setResult] = useState<OutputPanelResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [durationMs, setDurationMs] = useState<number | null>(null);

  const shareUrl = useMemo(() => {
    if (typeof window === 'undefined') return null;
    return `${window.location.origin}${window.location.pathname}`;
  }, []);

  const handleExampleSelect = (example: PlaygroundExample) => {
    setSelectedExample(example);
    setRequestJson(example.requestJson);
    setPolicyYaml(example.policyYaml);
    setMemoryJson(example.memoryJson);
    setResult(null);
    setError(null);
    setDurationMs(null);
  };

  const handleReset = () => handleExampleSelect(selectedExample);

  const handleCopyDecisionRecord = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.decisionRecordJson);
  };

  const handleRun = useCallback(async () => {
    setIsRunning(true);
    setError(null);
    setResult(null);
    setDurationMs(null);

    try {
      const start = performance.now();

      const request = JSON.parse(requestJson);
      const policy = yaml.load(policyYaml);
      const memory = JSON.parse(memoryJson);

      const { record, normalizedRequest } = await decideDemo({
        request,
        policy: (policy || {}) as any,
        memory,
      });

      const end = performance.now();
      setDurationMs(end - start);

      setResult({
        decisionRecordJson: JSON.stringify(record, null, 2),
        normalizedRequestJson: JSON.stringify(normalizedRequest, null, 2),
        notes: [
          'No data leaves your browser.',
          'This is a deterministic demo evaluator (not the full Lumyn engine).',
        ],
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setIsRunning(false);
    }
  }, [memoryJson, policyYaml, requestJson]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-950">
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-2xl">🧭</div>
              <div>
                <h1 className="text-xl font-bold text-white">Lumyn Playground</h1>
                <p className="text-sm text-gray-400">Generate Decision Records in your browser</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <a
                href="https://davidahmann.github.io/lumyn/docs/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gray-400 hover:text-white transition"
              >
                Docs →
              </a>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <aside className="lg:col-span-1">
            <ExampleSelector selectedId={selectedExample.id} onSelect={handleExampleSelect} />
          </aside>

          <div className="lg:col-span-3 space-y-4">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRun}
                  disabled={isRunning}
                  className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition ${
                    isRunning
                      ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                      : 'bg-green-600 hover:bg-green-500 text-white'
                  }`}
                >
                  {isRunning ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/70 border-t-transparent rounded-full animate-spin" />
                      Running gate…
                    </>
                  ) : (
                    'Run gate'
                  )}
                </button>
                <button
                  onClick={handleReset}
                  disabled={isRunning}
                  className="px-3 py-2 text-sm text-gray-300 hover:text-white transition border border-gray-700 rounded-lg hover:border-gray-600 disabled:opacity-50"
                >
                  Reset example
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => shareUrl && navigator.clipboard.writeText(shareUrl)}
                  disabled={!shareUrl || isRunning}
                  className="px-3 py-2 text-sm text-gray-300 hover:text-white transition border border-gray-700 rounded-lg hover:border-gray-600 disabled:opacity-50"
                >
                  Copy link
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-4">
                <section>
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-sm font-semibold text-gray-200">Decision Request (JSON)</h2>
                  </div>
                  <CodeEditor
                    value={requestJson}
                    onChange={setRequestJson}
                    language="json"
                    height="260px"
                    ariaLabel="Decision Request JSON"
                  />
                </section>

                <section>
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-sm font-semibold text-gray-200">Policy (YAML)</h2>
                  </div>
                  <CodeEditor
                    value={policyYaml}
                    onChange={setPolicyYaml}
                    language="yaml"
                    height="320px"
                    ariaLabel="Policy YAML"
                  />
                </section>

                <section>
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-sm font-semibold text-gray-200">Memory Snapshot (JSON)</h2>
                  </div>
                  <CodeEditor
                    value={memoryJson}
                    onChange={setMemoryJson}
                    language="json"
                    height="220px"
                    ariaLabel="Memory Snapshot JSON"
                  />
                </section>
              </div>

              <div className="lg:col-span-1">
                <OutputPanel
                  result={result}
                  error={error}
                  isRunning={isRunning}
                  durationMs={durationMs}
                  onCopyDecisionRecord={handleCopyDecisionRecord}
                />
              </div>
            </div>

            <p className="text-xs text-gray-500">
              Runs fully client-side. No analytics. No network calls. Paste your own inputs if you want, but nothing is sent anywhere.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

