import Link from 'next/link';
import CodeBlock from '@/components/CodeBlock';

const QUICKSTART_CODE = `pip install lumyn
lumyn demo --story

# Make a decision (CLI) and record it
lumyn decide --request examples/requests/decision_request.v1.json

# Fetch a Decision Record (API) and replay it
lumyn replay --pack workspace/packs/<decision_id>.json`;

export default function Home() {
  return (
    <div className="not-prose">
      {/* Hero Section */}
      <div className="text-center py-12 lg:py-20">
        <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6">
          Turn Gated AI Actions Into{' '}
          <span className="bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">
            Replayable Evidence
          </span>
        </h1>
        <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-8">
          Lumyn is a deterministic decision gateway for production AI.
          Every gated action emits a durable Decision Record with a verdict and stable reason codes, so you can audit and replay.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/docs/quickstart"
            className="px-6 py-3 bg-cyan-500 hover:bg-cyan-400 text-gray-900 font-semibold rounded-lg transition-colors"
          >
            Get Started
          </Link>
          <Link
            href="/docs/v1_semantics"
            className="px-6 py-3 bg-gray-800 hover:bg-gray-700 text-gray-100 font-semibold rounded-lg border border-gray-700 transition-colors"
          >
            Learn v1 Semantics
          </Link>
        </div>
      </div>

      {/* Quick Install */}
      <div className="max-w-xl mx-auto mb-16">
        <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
          <code className="text-cyan-400 text-sm">pip install lumyn &amp;&amp; lumyn demo --story</code>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
        <FeatureCard
          icon="🧾"
          title="Decision Records"
          description="Every gated action emits a durable record with verdict, stable reason codes, and replayable digests."
          href="/docs/v1_semantics"
        />
        <FeatureCard
          icon="🔁"
          title="Replay Incidents"
          description="Reproduce decisions deterministically from stored records to debug and audit without guesswork."
          href="/docs/replay-guarantees"
        />
        <FeatureCard
          icon="🧠"
          title="Policy + Memory"
          description="Gates can learn from labeled history while keeping reason codes stable and machine-readable."
          href="/docs/memory"
        />
        <FeatureCard
          icon="🔒"
          title="Strict Contracts"
          description="Versioned v1 schemas and strict policy validation to prevent silent drift in production."
          href="/docs/compatibility"
        />
        <FeatureCard
          icon="⚡"
          title="Fast Integration"
          description="Drop in a gateway that returns deterministic decisions and durable evidence."
          href="/docs/integration_checklist"
        />
        <FeatureCard
          icon="🧪"
          title="Upgrade Safely"
          description="Migrate packs and policies with explicit versioning; no breaking changes to v1 contracts."
          href="/docs/migration_v0_to_v1"
        />
      </div>

      {/* Code Example */}
      <div className="mb-16">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">2 Minutes to Your First Decision Record</h2>
        <CodeBlock code={QUICKSTART_CODE} language="bash" filename="quickstart.sh" />
      </div>

      {/* Comparison Table */}
      <div className="mb-16">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">Why Lumyn?</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 px-4 text-gray-400"></th>
                <th className="text-left py-3 px-4 text-gray-400">Without Lumyn</th>
                <th className="text-left py-3 px-4 text-cyan-400">With Lumyn</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              <tr>
                <td className="py-3 px-4 text-gray-300 font-medium">Can you prove why it happened?</td>
                <td className="py-3 px-4 text-gray-500">Screenshots + logs</td>
                <td className="py-3 px-4 text-gray-300">Durable Decision Record</td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-gray-300 font-medium">Can you replay a gate?</td>
                <td className="py-3 px-4 text-gray-500">Not reliably</td>
                <td className="py-3 px-4 text-gray-300">Yes (deterministic)</td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-gray-300 font-medium">Do decisions drift silently?</td>
                <td className="py-3 px-4 text-gray-500">Often</td>
                <td className="py-3 px-4 text-gray-300">Reason codes + digests</td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-gray-300 font-medium">Incident resolution</td>
                <td className="py-3 px-4 text-gray-500">Hours of guesswork</td>
                <td className="py-3 px-4 text-gray-300">Minutes with replay</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center py-12 border-t border-gray-800">
        <h2 className="text-2xl font-bold text-white mb-4">Ready to stop guessing?</h2>
        <p className="text-gray-400 mb-6">From pip install to replayable decisions in minutes.</p>
        <Link
          href="/docs/quickstart"
          className="inline-block px-6 py-3 bg-cyan-500 hover:bg-cyan-400 text-gray-900 font-semibold rounded-lg transition-colors"
        >
          Read the Quickstart Guide
        </Link>
      </div>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
  href,
}: {
  icon: string;
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="block p-6 bg-gray-800/30 hover:bg-gray-800/50 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
    >
      <span className="text-2xl mb-3 block">{icon}</span>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-gray-400">{description}</p>
    </Link>
  );
}
