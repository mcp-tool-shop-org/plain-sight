import type { SiteConfig } from '@mcptoolshop/site-theme';

export const config: SiteConfig = {
  title: 'plain-sight',
  description:
    'An AI says what it sees — local Florence-2 image describer: MCP server + CLI for prose descriptions, OCR, and LoRA-dataset caption sidecars.',
  logoBadge: 'PS',
  brandName: 'plain-sight',
  repoUrl: 'https://github.com/mcp-tool-shop-org/plain-sight',
  footerText:
    'MIT Licensed — built by <a href="https://mcp-tool-shop.github.io/" style="color:var(--color-muted);text-decoration:underline">MCP Tool Shop</a>',

  hero: {
    badge: 'Local · MIT · Florence-2',
    headline: 'An AI says',
    headlineAccent: 'what it sees.',
    description:
      'plain-sight wraps Florence-2 as an MCP server and a CLI: prose descriptions at three detail tiers, OCR, and exact-basename .txt caption sidecars for LoRA training sets. Deterministic by default. No cloud, no telemetry, never trust_remote_code.',
    primaryCta: { href: '#usage', label: 'Get started' },
    secondaryCta: { href: 'handbook/', label: 'Read the Handbook' },
    previews: [
      { label: 'Install', code: 'pip install -e .' },
      { label: 'Describe', code: 'plain-sight describe hero.png' },
      { label: 'Dataset lane', code: 'plain-sight batch ./dataset --prefix "mcpt_style, "' },
    ],
  },

  sections: [
    {
      kind: 'features',
      id: 'features',
      title: 'Features',
      subtitle: 'The describing sibling of ai-eyes — it narrates, ai-eyes measures.',
      features: [
        {
          title: 'Three detail tiers',
          desc: "Florence-2's native ladder: one sentence (low), a few sentences (medium), a full paragraph (high) — plus OCR for reading text off pixels.",
        },
        {
          title: 'The dataset lane',
          desc: 'Exact basename pairing (img_0042.png → img_0042.txt), bare prefix+caption+suffix for trigger tokens, and idempotent re-runs that skip existing sidecars.',
        },
        {
          title: 'Deterministic by default',
          desc: 'do_sample=false + beam search: the same image reproduces the same caption, so caption diffs mean something happened to the image.',
        },
        {
          title: 'MIT end to end',
          desc: 'The tool is MIT and the model is pinned to florence-community/Florence-2-large — MIT, loaded with native transformers classes. trust_remote_code is never used.',
        },
        {
          title: 'MCP + CLI, one engine',
          desc: 'Five MCP tools for Claude (describe_image, describe_batch, read_text, sight_status, sight_selftest) and a five-command CLI share the same Florence2Engine.',
        },
        {
          title: 'Honest about hallucination',
          desc: "Generative captions can invent detail. plain-sight says so, and pairs with ai-eyes-mcp (SigLIP2) — a different model family — when a claim needs verifying.",
        },
      ],
    },
    {
      kind: 'code-cards',
      id: 'usage',
      title: 'Usage',
      cards: [
        {
          title: 'Install',
          code: 'git clone https://github.com/mcp-tool-shop-org/plain-sight\ncd plain-sight\npip install -e .',
        },
        {
          title: 'Describe + OCR',
          code: 'plain-sight describe hero.png --detail high\nplain-sight ocr screenshot.png',
        },
        {
          title: 'Caption a training set',
          code: 'plain-sight batch ./dataset \\\n  --prefix "mcpt_style, " --detail high',
        },
        {
          title: 'Claude Code (MCP)',
          code: '{\n  "mcpServers": {\n    "plain-sight": { "command": "plain-sight-mcp" }\n  }\n}',
        },
      ],
    },
  ],
};
