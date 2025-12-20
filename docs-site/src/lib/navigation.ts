export interface NavItem {
  title: string;
  href: string;
  children?: NavItem[];
}

export const navigation: NavItem[] = [
  {
    title: 'Getting Started',
    href: '/docs',
    children: [
      { title: 'Introduction', href: '/docs' },
      { title: 'Quickstart', href: '/docs/quickstart' },
      { title: 'v1 Semantics', href: '/docs/v1_semantics' },
      { title: 'Replay Guarantees', href: '/docs/replay-guarantees' },
      { title: 'Integration Checklist', href: '/docs/integration_checklist' },
    ],
  },
  {
    title: 'Core Concepts',
    href: '/docs/v1_semantics',
    children: [
      { title: 'Decision Records', href: '/docs/v1_semantics' },
      { title: 'Memory', href: '/docs/memory' },
      { title: 'Architecture', href: '/docs/architecture' },
    ],
  },
  {
    title: 'Compatibility',
    href: '/docs/compatibility',
    children: [
      { title: 'Compatibility', href: '/docs/compatibility' },
      { title: 'Migrate v0 → v1', href: '/docs/migration_v0_to_v1' },
    ],
  },
  {
    title: 'Deployment',
    href: '/docs/deployment/semantic-search-and-pages',
    children: [
      { title: 'Semantic Search + Pages', href: '/docs/deployment/semantic-search-and-pages' },
    ],
  },
  {
    title: 'Blog',
    href: '/blog',
    children: [
      { title: 'AI incident response: replay decisions', href: '/blog/ai-incident-response-replay' },
      { title: 'Decision logs vs telemetry', href: '/blog/decision-logs-vs-telemetry' },
      { title: 'What is a Decision Record?', href: '/blog/what-is-a-decision-record' },
      { title: 'Reason codes are a contract', href: '/blog/reason-codes-are-a-contract' },
      { title: 'Lumyn vs RAG', href: '/blog/lumyn-vs-rag' },
      { title: 'Lumyn vs Fine-Tuning', href: '/blog/lumyn-vs-finetuning' },
      { title: 'Lumyn vs LangChain', href: '/blog/lumyn-vs-langchain' },
      { title: 'Lumyn vs OPA', href: '/blog/lumyn-vs-opa' },
    ],
  },
];
