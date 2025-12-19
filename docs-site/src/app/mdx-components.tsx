import type { MDXComponents } from 'mdx/types';
import Link from 'next/link';

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    // Custom link handling for internal links
    a: ({ href, children, ...props }) => {
      const isInternal = href && (href.startsWith('/') || href.startsWith('#'));
      if (isInternal) {
        return (
          <Link href={href} {...props}>
            {children}
          </Link>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
          {children}
        </a>
      );
    },
    // Custom code block styling
    pre: ({ children, ...props }) => (
      <pre className="rounded-lg border border-gray-700 overflow-x-auto" {...props}>
        {children}
      </pre>
    ),
    // Custom inline code
    code: ({ children, ...props }) => {
      // Check if this is inside a pre (code block) vs inline
      const isInline = typeof children === 'string' && !children.includes('\n');
      if (isInline) {
        return (
          <code className="px-1.5 py-0.5 rounded bg-gray-800 text-purple-300 text-sm" {...props}>
            {children}
          </code>
        );
      }
      return <code {...props}>{children}</code>;
    },
    // Custom blockquote for callouts
    blockquote: ({ children, ...props }) => (
      <blockquote className="border-l-4 border-cyan-500 bg-cyan-500/10 pl-4 py-2 my-4 rounded-r-lg" {...props}>
        {children}
      </blockquote>
    ),
    // Custom table styling
    table: ({ children, ...props }) => (
      <div className="overflow-x-auto my-6">
        <table className="min-w-full divide-y divide-gray-700" {...props}>
          {children}
        </table>
      </div>
    ),
    th: ({ children, ...props }) => (
      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-200 bg-gray-800" {...props}>
        {children}
      </th>
    ),
    td: ({ children, ...props }) => (
      <td className="px-4 py-3 text-sm text-gray-300 border-b border-gray-700" {...props}>
        {children}
      </td>
    ),
    ...components,
  };
}
