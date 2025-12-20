import stringify from 'fast-json-stable-stringify';

export type Verdict = 'ALLOW' | 'ABSTAIN' | 'ESCALATE' | 'DENY';

export type DecisionRequestV1 = Record<string, unknown>;
export type PolicyV1 = Record<string, unknown>;

export type MemorySnapshotV1 = {
  schema_version?: string;
  similar_allow?: string[];
  similar_block?: string[];
};

export type DecisionRecordV1 = {
  schema_version: 'decision_record.v1';
  decision_id: string;
  created_at: string;
  request: DecisionRequestV1;
  policy: {
    policy_id: string;
    policy_version: string;
    policy_hash: string;
    mode: 'enforce' | 'advisory';
  };
  verdict: Verdict;
  reason_codes: string[];
  matched_rules: Array<Record<string, unknown>>;
  risk_signals: Record<string, unknown>;
  queries: Array<Record<string, unknown>>;
  obligations: Array<Record<string, unknown>>;
  determinism: Record<string, unknown>;
  extensions: Record<string, unknown>;
};

const STAGES = ['REQUIREMENTS', 'HARD_BLOCKS', 'ESCALATIONS', 'ALLOW_PATHS'] as const;
type Stage = (typeof STAGES)[number];

function asObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return value as Record<string, unknown>;
}

function getNested(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split('.');
  let current: unknown = obj;
  for (const part of parts) {
    if (!current || typeof current !== 'object' || Array.isArray(current)) return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return current;
}

export async function sha256Hex(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest('SHA-256', data);
  const bytes = new Uint8Array(digest);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

async function sha256Prefixed(input: string): Promise<string> {
  return `sha256:${await sha256Hex(input)}`;
}

function normalizeContextDigest(request: Record<string, unknown>): Promise<string> {
  const context = asObject(request.context);
  const inline = asObject(context.inline);
  return sha256Prefixed(stringify(inline));
}

function extractMode(request: Record<string, unknown>, policy: Record<string, unknown>): 'enforce' | 'advisory' {
  const hints = asObject(request.hints);
  const requestPolicy = asObject(request.policy);
  const policyDefaults = asObject(policy.defaults);
  const mode =
    hints.mode ??
    requestPolicy.mode ??
    policyDefaults.mode ??
    'enforce';
  return mode === 'advisory' ? 'advisory' : 'enforce';
}

function amountUsd(request: Record<string, unknown>): number | null {
  const action = asObject(request.action);
  const amount = asObject(action.amount);
  const value = amount.value;
  const currency = amount.currency;
  if (typeof value !== 'number') return null;
  if (typeof currency === 'string' && currency.toUpperCase() === 'USD') return value;

  const evidence = asObject(request.evidence);
  const fx = evidence.fx_rate_to_usd;
  if (typeof fx === 'number') return value * fx;
  return null;
}

type Operator = 'is' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in';

function parsePredicateKey(key: string): { field: string; op: Operator } {
  const suffixes: Array<[string, Operator]> = [
    ['_is', 'is'],
    ['_ne', 'ne'],
    ['_gt', 'gt'],
    ['_gte', 'gte'],
    ['_lt', 'lt'],
    ['_lte', 'lte'],
    ['_in', 'in'],
  ];

  for (const [suffix, op] of suffixes) {
    if (key.endsWith(suffix)) {
      return { field: key.slice(0, -suffix.length), op };
    }
  }
  return { field: key, op: 'is' };
}

function resolveField(request: Record<string, unknown>, field: string): unknown {
  if (field === 'action_type') return getNested(request, 'action.type');
  if (field === 'amount_usd') return amountUsd(request);
  if (field === 'amount_currency') return getNested(request, 'action.amount.currency');

  if (field.startsWith('evidence.')) return getNested(request, field);
  if (field.startsWith('subject.')) return getNested(request, field);
  if (field.startsWith('action.')) return getNested(request, field);
  if (field.startsWith('context.')) return getNested(request, field);

  return getNested(request, field);
}

function evalOnePredicate(request: Record<string, unknown>, key: string, expected: unknown): boolean {
  const { field, op } = parsePredicateKey(key);
  const actual = resolveField(request, field);

  if (op === 'is') {
    if (expected === null) return actual === null || actual === undefined;
    return actual === expected;
  }
  if (op === 'ne') return actual !== expected;

  if (op === 'in') {
    if (!Array.isArray(expected)) return false;
    return expected.includes(actual as never);
  }

  if (typeof actual !== 'number' || typeof expected !== 'number') return false;
  if (op === 'gt') return actual > expected;
  if (op === 'gte') return actual >= expected;
  if (op === 'lt') return actual < expected;
  if (op === 'lte') return actual <= expected;
  return false;
}

function evalPredicateObject(request: Record<string, unknown>, predicate: Record<string, unknown>): boolean {
  for (const [key, expected] of Object.entries(predicate)) {
    if (!evalOnePredicate(request, key, expected)) return false;
  }
  return true;
}

function stageOrder(stage: Stage): number {
  return STAGES.indexOf(stage);
}

export async function decideDemo(params: {
  request: DecisionRequestV1;
  policy: PolicyV1;
  memory: MemorySnapshotV1;
}): Promise<{ record: DecisionRecordV1; normalizedRequest: DecisionRequestV1 }> {
  const requestObj = asObject(params.request);
  const policyObj = asObject(params.policy);

  if (requestObj.schema_version !== 'decision_request.v1') {
    throw new Error('Request must be schema_version: decision_request.v1');
  }
  if (policyObj.schema_version !== 'policy.v1') {
    throw new Error('Policy must be schema_version: policy.v1');
  }

  const normalizedRequest: Record<string, unknown> = JSON.parse(stringify(requestObj));
  normalizedRequest.context = { ...asObject(normalizedRequest.context) };
  const context = asObject(normalizedRequest.context);

  if (!context.mode) context.mode = 'inline';
  if (context.mode === 'inline' && !context.inline) {
    context.inline = { note: 'Added by playground (inline context required for digest)' };
  }
  const digestRaw = typeof context.digest === 'string' ? context.digest : '';
  const digestLooksValid = /^sha256:[0-9a-f]{64}$/.test(digestRaw);
  const digestIsPlaceholder = digestRaw === `sha256:${'0'.repeat(64)}`;
  if (!digestLooksValid || digestIsPlaceholder) {
    context.digest = await normalizeContextDigest(normalizedRequest);
  }

  const policyHash = await sha256Prefixed(stringify(policyObj));
  const mode = extractMode(normalizedRequest, policyObj);

  const memory = params.memory || {};
  const fingerprint = String(asObject(normalizedRequest.context).digest || '');
  const normalizeMemoryTokens = (values: unknown[] | undefined) =>
    (values || [])
      .map(String)
      .map((v) => (v === '__REQUEST_CONTEXT_DIGEST__' ? fingerprint : v))
      .filter(Boolean);

  const similarBlock = new Set(normalizeMemoryTokens(memory.similar_block));
  const similarAllow = new Set(normalizeMemoryTokens(memory.similar_allow));

  if (similarBlock.has(fingerprint)) {
    return {
      normalizedRequest,
      record: {
        schema_version: 'decision_record.v1',
        decision_id: `demo:${fingerprint.slice(7, 23) || 'memory'}`,
        created_at: '1970-01-01T00:00:00Z',
        request: normalizedRequest,
        policy: {
          policy_id: String(policyObj.policy_id || 'unknown'),
          policy_version: String(policyObj.policy_version || 'unknown'),
          policy_hash: policyHash,
          mode,
        },
        verdict: 'DENY',
        reason_codes: ['FAILURE_MEMORY_SIMILAR_BLOCK'],
        matched_rules: [{ id: 'MEMORY', stage: 'HARD_BLOCKS', source: 'memory_snapshot' }],
        risk_signals: { memory_similarity: { fingerprint, verdict: 'block' } },
        queries: [],
        obligations: [],
        determinism: {
          request_digest: fingerprint,
          policy_hash: policyHash,
          note: 'Demo evaluator (client-side); production engine may differ.',
        },
        extensions: {},
      },
    };
  }

  if (similarAllow.has(fingerprint)) {
    return {
      normalizedRequest,
      record: {
        schema_version: 'decision_record.v1',
        decision_id: `demo:${fingerprint.slice(7, 23) || 'memory'}`,
        created_at: '1970-01-01T00:00:00Z',
        request: normalizedRequest,
        policy: {
          policy_id: String(policyObj.policy_id || 'unknown'),
          policy_version: String(policyObj.policy_version || 'unknown'),
          policy_hash: policyHash,
          mode,
        },
        verdict: 'ALLOW',
        reason_codes: ['SUCCESS_MEMORY_SIMILAR_ALLOW'],
        matched_rules: [{ id: 'MEMORY', stage: 'ALLOW_PATHS', source: 'memory_snapshot' }],
        risk_signals: { memory_similarity: { fingerprint, verdict: 'allow' } },
        queries: [],
        obligations: [],
        determinism: {
          request_digest: fingerprint,
          policy_hash: policyHash,
          note: 'Demo evaluator (client-side); production engine may differ.',
        },
        extensions: {},
      },
    };
  }

  const defaults = asObject(policyObj.defaults);
  const defaultVerdict = (defaults.default_verdict as Verdict) || 'ABSTAIN';
  const defaultReason = (defaults.default_reason_code as string) || 'NO_MATCH_DEFAULT';
  const rules = Array.isArray(policyObj.rules) ? (policyObj.rules as unknown[]) : [];

  const parsedRules = rules
    .map(asObject)
    .filter((r) => typeof r.id === 'string' && typeof r.stage === 'string' && STAGES.includes(r.stage as Stage))
    .sort((a, b) => stageOrder(a.stage as Stage) - stageOrder(b.stage as Stage));

  const matchedRules: Array<Record<string, unknown>> = [];
  const allQueries: Array<Record<string, unknown>> = [];
  const allObligations: Array<Record<string, unknown>> = [];

  for (const rule of parsedRules) {
    const when = asObject(rule.when);
    if (Object.keys(when).length > 0 && !evalPredicateObject(normalizedRequest, when)) continue;

    let matched = false;
    const ifObj = asObject(rule.if);
    const ifAll = Array.isArray(rule.if_all) ? (rule.if_all as unknown[]).map(asObject) : [];
    const ifAny = Array.isArray(rule.if_any) ? (rule.if_any as unknown[]).map(asObject) : [];

    if (Object.keys(ifObj).length > 0) matched = evalPredicateObject(normalizedRequest, ifObj);
    else if (ifAll.length > 0) matched = ifAll.every((p) => evalPredicateObject(normalizedRequest, p));
    else if (ifAny.length > 0) matched = ifAny.some((p) => evalPredicateObject(normalizedRequest, p));
    else matched = true;

    if (!matched) continue;

    const thenObj = asObject(rule.then);
    const verdict = (thenObj.verdict as Verdict) || defaultVerdict;
    const reasonCodes = Array.isArray(thenObj.reason_codes)
      ? (thenObj.reason_codes as unknown[]).map(String)
      : [defaultReason];

    matchedRules.push({ id: rule.id, stage: rule.stage, when: rule.when, then: rule.then });

    const queries = Array.isArray(thenObj.queries) ? (thenObj.queries as unknown[]).map(asObject) : [];
    const obligations = Array.isArray(thenObj.obligations) ? (thenObj.obligations as unknown[]).map(asObject) : [];
    allQueries.push(...queries);
    allObligations.push(...obligations);

    const stage = rule.stage as Stage;
    if (stage === 'REQUIREMENTS' || stage === 'HARD_BLOCKS' || stage === 'ESCALATIONS') {
      return {
        normalizedRequest,
        record: {
          schema_version: 'decision_record.v1',
          decision_id: `demo:${fingerprint.slice(7, 23) || 'policy'}`,
          created_at: '1970-01-01T00:00:00Z',
          request: normalizedRequest,
          policy: {
            policy_id: String(policyObj.policy_id || 'unknown'),
            policy_version: String(policyObj.policy_version || 'unknown'),
            policy_hash: policyHash,
            mode,
          },
          verdict,
          reason_codes: reasonCodes,
          matched_rules: matchedRules,
          risk_signals: {},
          queries: allQueries,
          obligations: allObligations,
          determinism: {
            request_digest: fingerprint,
            policy_hash: policyHash,
            note: 'Demo evaluator (client-side); production engine may differ.',
          },
          extensions: {},
        },
      };
    }

    if (stage === 'ALLOW_PATHS') {
      return {
        normalizedRequest,
        record: {
          schema_version: 'decision_record.v1',
          decision_id: `demo:${fingerprint.slice(7, 23) || 'allow'}`,
          created_at: '1970-01-01T00:00:00Z',
          request: normalizedRequest,
          policy: {
            policy_id: String(policyObj.policy_id || 'unknown'),
            policy_version: String(policyObj.policy_version || 'unknown'),
            policy_hash: policyHash,
            mode,
          },
          verdict,
          reason_codes: reasonCodes,
          matched_rules: matchedRules,
          risk_signals: {},
          queries: allQueries,
          obligations: allObligations,
          determinism: {
            request_digest: fingerprint,
            policy_hash: policyHash,
            note: 'Demo evaluator (client-side); production engine may differ.',
          },
          extensions: {},
        },
      };
    }
  }

  return {
    normalizedRequest,
    record: {
      schema_version: 'decision_record.v1',
      decision_id: `demo:${fingerprint.slice(7, 23) || 'default'}`,
      created_at: '1970-01-01T00:00:00Z',
      request: normalizedRequest,
      policy: {
        policy_id: String(policyObj.policy_id || 'unknown'),
        policy_version: String(policyObj.policy_version || 'unknown'),
        policy_hash: policyHash,
        mode,
      },
      verdict: defaultVerdict,
      reason_codes: [defaultReason],
      matched_rules: matchedRules,
      risk_signals: {},
      queries: allQueries,
      obligations: allObligations,
      determinism: {
        request_digest: fingerprint,
        policy_hash: policyHash,
        note: 'Demo evaluator (client-side); production engine may differ.',
      },
      extensions: {},
    },
  };
}
