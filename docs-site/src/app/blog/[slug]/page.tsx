import { getDocContent, getAllDocSlugs } from '@/lib/docs';
import { markdownToHtml } from '@/lib/markdown';
import { notFound } from 'next/navigation';
import { Metadata } from 'next';
import MarkdownRenderer from '@/components/MarkdownRenderer';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  const slugs = getAllDocSlugs();
  // Get only blog posts
  return slugs
    .filter((slug) => slug.startsWith('blog/'))
    .map((slug) => ({
      slug: slug.replace('blog/', ''),
    }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const doc = getDocContent(`blog/${slug}`);

  const title = doc?.frontmatter?.title || slug.replace(/-/g, ' ');

  return {
    title: `${title} - Lumyn Blog`,
    description: doc?.frontmatter?.description || 'Lumyn blog post',
  };
}

export default async function BlogPostPage({ params }: PageProps) {
  const { slug } = await params;
  const doc = getDocContent(`blog/${slug}`);

  if (!doc) {
    notFound();
  }

  const html = markdownToHtml(doc.content);

  return <MarkdownRenderer html={html} />;
}
