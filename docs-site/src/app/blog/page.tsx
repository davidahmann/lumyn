import Link from 'next/link';
import { navigation } from '@/lib/navigation';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Blog - Lumyn',
  description: 'Articles about deterministic decision gateways, AI governance, and incident replay',
};

export default function BlogIndexPage() {
  const blogSection = navigation.find((section) => section.title === 'Blog');
  const blogPosts = blogSection?.children || [];

  return (
    <div className="prose prose-invert max-w-none">
      <h1>Blog</h1>
      <p className="text-lg text-gray-300">
        Articles about deterministic decision gateways, AI governance, and incident replay.
      </p>
      <div className="mt-8 grid gap-4">
        {blogPosts.map((post) => (
          <Link
            key={post.href}
            href={post.href}
            className="block p-4 rounded-lg border border-gray-700 hover:border-cyan-500 hover:bg-gray-800/50 transition-colors no-underline"
          >
            <h3 className="text-lg font-semibold text-white m-0">{post.title}</h3>
          </Link>
        ))}
      </div>
    </div>
  );
}
