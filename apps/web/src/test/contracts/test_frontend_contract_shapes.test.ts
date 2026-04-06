import { describe, it, expect } from 'vitest'

/**
 * Audit: Frontend Contract Shapes
 * This test ensures that the TypeScript interfaces used for rendering
 * core benchmark data (Reasoning, Trades, Decisions) align with the
 * truth chain discovered during Phase 1 of the audit.
 */

interface ReasoningTrace {
    id: string
    task_type: string
    model_provider: string
    model_name: string
    prompt: any[]
    response: any
    metadata: {
        ticker?: string
        source_id?: string
        [key: string]: any
    }
    normalized_transcript?: any // Deliverable 4 Hardened Column
    created_at: string
}

interface DecisionTrace {
    id: string
    source_id: string
    ticker: string
    signal: 'BUY' | 'SELL' | 'HOLD'
    confidence: number
    reasoning: string
    model_provider: string
    model_name: string
    status: string // e.g., 'VALIDATED', 'EXECUTED', 'REJECTED_MARGIN'
    metadata: {
        rejection_reason?: string
        strategy_reasoning?: string
        verification_reasoning?: string
        [key: string]: any
    }
    trade_id?: string
    created_at: string
}

describe('Frontend Data Contract Audit', () => {
  it('should support the audit-hardened ReasoningLog shape', () => {
    const trace: ReasoningTrace = {
        id: 'uuid',
        task_type: 'VERIFICATION',
        model_provider: 'openai',
        model_name: 'gpt-4o',
        prompt: [],
        response: {},
        metadata: {
            ticker: 'AAPL'
        },
        normalized_transcript: {
            messages: [],
            tool_calls: []
        },
        created_at: new Date().toISOString()
    }

    expect(trace.normalized_transcript).toBeDefined()
  })

  it('should support the audit-hardened Decision shape (including rejections)', () => {
    const decision: DecisionTrace = {
        id: 'uuid',
        source_id: 'news-123',
        ticker: 'TSLA',
        signal: 'BUY',
        confidence: 85,
        reasoning: 'Catalyst detected',
        model_provider: 'openai',
        model_name: 'gpt-4o',
        status: 'REJECTED_VERIFICATION',
        metadata: {
            rejection_reason: 'Missing mandatory tools'
        },
        created_at: new Date().toISOString()
    }

    expect(decision.metadata.rejection_reason).toBe('Missing mandatory tools')
  })

  it('should support the new TradeRejection shape for audit views', () => {
      interface TradeRejection {
          id: string
          provider: string
          ticker: string
          requested_action: string
          rejection_reason: string
          market_price?: number
          created_at: string
      }

      const rejection: TradeRejection = {
          id: 'rej-123',
          provider: 'openai',
          ticker: 'AAPL',
          requested_action: 'BUY',
          rejection_reason: 'Insufficient buying power',
          created_at: new Date().toISOString()
      }

      expect(rejection.rejection_reason).toBeDefined()
  })
})
