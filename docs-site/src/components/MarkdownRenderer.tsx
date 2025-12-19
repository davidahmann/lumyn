'use client';

import { useEffect, useRef } from 'react';
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import bash from 'highlight.js/lib/languages/bash';
import json from 'highlight.js/lib/languages/json';
import yaml from 'highlight.js/lib/languages/yaml';
import sql from 'highlight.js/lib/languages/sql';
import xml from 'highlight.js/lib/languages/xml';
import css from 'highlight.js/lib/languages/css';
import mermaid from 'mermaid';

// Register languages
hljs.registerLanguage('python', python);
hljs.registerLanguage('py', python);
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('js', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('ts', typescript);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('shell', bash);
hljs.registerLanguage('sh', bash);
hljs.registerLanguage('json', json);
hljs.registerLanguage('yaml', yaml);
hljs.registerLanguage('yml', yaml);
hljs.registerLanguage('sql', sql);
hljs.registerLanguage('html', xml);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('css', css);

// Initialize mermaid with dark theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#22d3ee',
    primaryTextColor: '#e6edf3',
    primaryBorderColor: '#30363d',
    lineColor: '#8b949e',
    secondaryColor: '#1f2937',
    tertiaryColor: '#374151',
    background: '#0d1117',
    mainBkg: '#0d1117',
    nodeBorder: '#30363d',
    clusterBkg: '#1f2937',
    clusterBorder: '#30363d',
    titleColor: '#e6edf3',
    edgeLabelBackground: '#0d1117',
  },
});

interface MarkdownRendererProps {
  html: string;
}

export default function MarkdownRenderer({ html }: MarkdownRendererProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (contentRef.current) {
      // Find all code blocks and highlight them
      const codeBlocks = contentRef.current.querySelectorAll('pre code');
      codeBlocks.forEach((block) => {
        const element = block as HTMLElement;
        // Check if this is a mermaid diagram
        if (element.classList.contains('language-mermaid')) {
          const mermaidCode = element.textContent || '';
          const parent = element.parentElement;
          if (parent) {
            // Create a container for the mermaid diagram
            const container = document.createElement('div');
            container.className = 'mermaid';
            container.textContent = mermaidCode;
            parent.replaceWith(container);
          }
        } else {
          hljs.highlightElement(element);
        }
      });

      // Render mermaid diagrams
      mermaid.run({
        nodes: contentRef.current.querySelectorAll('.mermaid'),
      });
    }
  }, [html]);

  return (
    <div
      ref={contentRef}
      className="prose prose-invert max-w-none"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
