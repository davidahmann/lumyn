import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Lumyn Playground - Try Decision Records in Browser',
  description:
    'Interactive playground to try Lumyn Decision Records in your browser. Run a deterministic policy+memory demo. No installation required.',
  keywords:
    'lumyn playground, decision record demo, ai governance, deterministic ai, policy engine, reason codes, incident replay',
  openGraph: {
    title: 'Lumyn Playground',
    description: 'Try Lumyn Decision Records in your browser',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
