import { marked } from 'marked';

// Configure marked for GitHub Flavored Markdown
marked.setOptions({
  gfm: true, // Enable GitHub Flavored Markdown (tables, strikethrough, etc.)
  breaks: false, // Don't convert \n to <br>
});

// Get basePath for production (GitHub Pages deploys to /lumyn/)
const basePath = process.env.NODE_ENV === 'production' ? '/lumyn' : '';

// Helper function to generate slug from heading text (similar to rehype-slug)
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '') // Remove special characters except spaces and hyphens
    .replace(/\s+/g, '-') // Replace spaces with hyphens
    .replace(/-+/g, '-') // Replace multiple hyphens with single hyphen
    .trim();
}

// Custom renderer to handle internal .md links and add classes
const renderer = new marked.Renderer();

// Override link rendering to handle internal .md links
renderer.link = function ({ href, title, text }) {
  // Normalize internal absolute links to respect GitHub Pages basePath.
  // Next.js `basePath` is only automatically applied when using `next/link`;
  // our markdown renderer outputs raw `<a>` tags.
  if (href && href.startsWith('/') && !href.startsWith('//')) {
    if (basePath && !href.startsWith(basePath + '/')) {
      href = basePath + href;
    }
  }

  // Convert internal .md links to proper paths with basePath
  if (href && href.endsWith('.md')) {
    // Remove .md extension
    let path = href.replace('.md', '');

    // Handle relative paths like ../context-accountability.md (from blog posts)
    if (path.startsWith('../')) {
      path = path.replace('../', '');
    }

    // Determine if it's a blog or docs link
    if (path.startsWith('blog/')) {
      // Blog links go to /blog/slug
      href = basePath + '/' + path;
    } else if (path.startsWith('use-cases/')) {
      // Use-cases stay under /docs/use-cases/
      href = basePath + '/docs/' + path;
    } else {
      // Regular docs links
      href = basePath + '/docs/' + path;
    }
  }

  // External links open in new tab
  if (href && (href.startsWith('http://') || href.startsWith('https://'))) {
    return `<a href="${href}" target="_blank" rel="noopener noreferrer"${title ? ` title="${title}"` : ''}>${text}</a>`;
  }

  return `<a href="${href}"${title ? ` title="${title}"` : ''}>${text}</a>`;
};

// Override code block rendering to add language class
renderer.code = function ({ text, lang }) {
  const language = lang || '';
  // Don't escape mermaid code - it needs the raw text for parsing
  if (language === 'mermaid') {
    return `<pre><code class="language-mermaid">${text}</code></pre>`;
  }
  const escapedCode = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return `<pre><code class="language-${language}">${escapedCode}</code></pre>`;
};

// Override inline code rendering
renderer.codespan = function ({ text }) {
  return `<code class="inline-code">${text}</code>`;
};

// Override heading rendering to add IDs for anchor links
renderer.heading = function ({ text, depth }) {
  const slug = slugify(text);
  return `<h${depth} id="${slug}">${text}</h${depth}>`;
};

// Use the custom renderer
marked.use({ renderer });

/**
 * Convert markdown to HTML using marked library
 * Supports full GitHub Flavored Markdown including tables
 */
export function markdownToHtml(markdown: string): string {
  // Note: Frontmatter is already removed by gray-matter in docs.ts
  // Only remove Jekyll liquid tags here
  const cleanContent = markdown
    .replace(/\{%.*?%\}/g, '')
    .replace(/\{\{.*?\}\}/g, '');

  // Parse markdown to HTML
  return marked.parse(cleanContent) as string;
}
