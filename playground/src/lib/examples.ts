export type PlaygroundExample = {
  id: string;
  title: string;
  description: string;
  requestJson: string;
  policyYaml: string;
  memoryJson: string;
};

const PLACEHOLDER_DIGEST = 'sha256:' + '0'.repeat(64);

const STARTER_POLICY_YAML = `schema_version: policy.v1
policy_id: starter-policy
policy_version: "1.0.0"

defaults:
  mode: enforce
  default_verdict: ESCALATE
  default_reason_code: NO_MATCH_DEFAULT_ESCALATE

rules:
  - id: R001
    stage: REQUIREMENTS
    when: { action_type: support.refund }
    if_any:
      - { evidence.ticket_id_is: null }
      - { evidence.order_id_is: null }
      - { evidence.customer_id_is: null }
    then:
      verdict: DENY
      reason_codes: [MISSING_EVIDENCE_REFUND]

  - id: R022
    stage: HARD_BLOCKS
    when: { action_type: support.refund }
    if: { evidence.chargeback_risk_gte: 0.70 }
    then:
      verdict: ABSTAIN
      reason_codes: [CHARGEBACK_RISK_BLOCK]

  - id: R030
    stage: ESCALATIONS
    when: { action_type: support.refund }
    if: { amount_usd_gt: 200 }
    then:
      verdict: ESCALATE
      reason_codes: [REFUND_OVER_ESCALATION_LIMIT]

  - id: R050
    stage: ALLOW_PATHS
    when: { action_type: support.refund }
    if_all:
      - { amount_usd_lte: 25 }
      - { evidence.payment_instrument_risk_in: [low, medium] }
      - { evidence.chargeback_risk_lt: 0.35 }
      - { evidence.previous_refund_count_90d_lt: 2 }
      - { evidence.customer_age_days_gte: 14 }
    then:
      verdict: ALLOW
      reason_codes: [REFUND_SMALL_LOW_RISK]
      obligations:
        - type: check
          title: Verify ticket exists
          details: Confirm the support ticket_id exists.`;

export const examples: PlaygroundExample[] = [
  {
    id: 'refund-small-allow',
    title: 'Refund: small + low risk (ALLOW)',
    description: 'Shows an allow-path rule for small USD refunds with low chargeback risk.',
    requestJson: JSON.stringify(
      {
        schema_version: 'decision_request.v1',
        subject: { type: 'agent', id: 'support_agent_17' },
        action: {
          type: 'support.refund',
          intent: 'Refund customer for delayed shipment',
          amount: { value: 24, currency: 'USD' },
          tags: ['refund', 'support'],
        },
        evidence: {
          ticket_id: 'TCK-10017',
          order_id: 'ORD-908',
          customer_id: 'CUS-42',
          payment_instrument_risk: 'low',
          chargeback_risk: 0.12,
          previous_refund_count_90d: 0,
          customer_age_days: 240,
        },
        context: {
          mode: 'inline',
          digest: PLACEHOLDER_DIGEST,
          inline: { ticket_summary: 'Customer reports delayed shipment; approve small refund.' },
        },
      },
      null,
      2,
    ),
    policyYaml: STARTER_POLICY_YAML,
    memoryJson: JSON.stringify(
      {
        schema_version: 'memory_snapshot.v1',
        similar_allow: [],
        similar_block: [],
      },
      null,
      2,
    ),
  },
  {
    id: 'refund-high-risk-abstain',
    title: 'Refund: high chargeback risk (ABSTAIN)',
    description: 'Shows a hard-block style gate for high chargeback risk.',
    requestJson: JSON.stringify(
      {
        schema_version: 'decision_request.v1',
        subject: { type: 'agent', id: 'support_agent_4' },
        action: {
          type: 'support.refund',
          intent: 'Refund customer complaint',
          amount: { value: 85, currency: 'USD' },
          tags: ['refund', 'support'],
        },
        evidence: {
          ticket_id: 'TCK-20001',
          order_id: 'ORD-1221',
          customer_id: 'CUS-991',
          payment_instrument_risk: 'medium',
          chargeback_risk: 0.92,
          previous_refund_count_90d: 1,
          customer_age_days: 18,
        },
        context: {
          mode: 'inline',
          digest: PLACEHOLDER_DIGEST,
          inline: { ticket_summary: 'Customer wants refund; payment instrument flagged.' },
        },
      },
      null,
      2,
    ),
    policyYaml: STARTER_POLICY_YAML,
    memoryJson: JSON.stringify(
      {
        schema_version: 'memory_snapshot.v1',
        similar_allow: [],
        similar_block: [],
      },
      null,
      2,
    ),
  },
  {
    id: 'memory-similar-block',
    title: 'Memory: similar prior incident (DENY)',
    description:
      'Shows a memory-based block. The demo uses context.digest as the similarity fingerprint.',
    requestJson: JSON.stringify(
      {
        schema_version: 'decision_request.v1',
        subject: { type: 'agent', id: 'support_agent_9' },
        action: { type: 'support.issue_credit', intent: 'Issue goodwill credit', tags: ['credit'] },
        evidence: { ticket_id: 'TCK-30077', customer_id: 'CUS-10' },
        context: {
          mode: 'inline',
          digest: PLACEHOLDER_DIGEST,
          inline: { ticket_summary: 'Customer asks for credit; similar past fraud attempt.' },
        },
      },
      null,
      2,
    ),
    policyYaml: `schema_version: policy.v1
policy_id: memory-demo
policy_version: "1.0.0"

defaults:
  mode: enforce
  default_verdict: ABSTAIN
  default_reason_code: NO_MATCH_DEFAULT_ABSTAIN

rules:
  - id: R010
    stage: ALLOW_PATHS
    when: { action_type: support.issue_credit }
    if: { evidence.customer_id_is: null }
    then:
      verdict: DENY
      reason_codes: [MISSING_EVIDENCE_CUSTOMER_ID]`,
    memoryJson: JSON.stringify(
      {
        schema_version: 'memory_snapshot.v1',
        similar_allow: [],
        similar_block: ['__REQUEST_CONTEXT_DIGEST__'],
      },
      null,
      2,
    ),
  },
];
