import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';

export const metadata: Metadata = {
  title: 'Lumyn - Decide → Record → Replay',
  description:
    "Lumyn is a deterministic decision gateway for production AI. Every gated action emits a durable Decision Record you can audit and replay. Decide → record → replay.",
  keywords:
    'decision gateway, decision record, deterministic ai, ai governance, ai audit trail, incident replay, reason codes, human-in-the-loop, policy engine, guardrails, pgvector, semantic search',
  openGraph: {
    title: 'Lumyn - Decide → Record → Replay',
    description:
      "Lumyn is a deterministic decision gateway. Every action emits a Decision Record, so incidents stop being vibes and screenshots.",
    url: 'https://davidahmann.github.io/lumyn',
    siteName: 'Lumyn',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Lumyn - Decide → Record → Replay',
    description:
      'Lumyn is a deterministic decision gateway. Every action emits a Decision Record you can replay.',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        <Header />
        <div className="flex max-w-7xl mx-auto px-4 lg:px-8">
          <Sidebar />
          <main className="flex-1 min-w-0 py-8 lg:pl-8">
            <article className="prose prose-invert max-w-none">
              {children}
            </article>
          </main>
        </div>
      </body>
    </html>
  );
}
