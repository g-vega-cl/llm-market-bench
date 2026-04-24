import { describe, it, expect } from 'vitest'

/**
 * Tests for FutureCatalysts component functionality.
 * 
 * Win #2: Scenario Percentage Parsing
 * The FutureCatalysts component now scans scenario_analysis text for percentage
 * values and renders them as styled badges next to each line.
 */

// Inline copy of the component's parsing logic for unit testing
function parseScenarioPercentages(analysis: string): { text: string; percentage: string | null }[] {
  const lines = analysis.split('\n')
  return lines.map(line => {
    const match = line.match(/(\d{1,3})\s*%/)
    const percentage = match ? match[1] + '%' : null
    return { text: line, percentage }
  })
}

describe('parseScenarioPercentages', () => {
  it('extracts basic percentage (40%)', () => {
    const result = parseScenarioPercentages('Market drops 40% in the bear case')
    expect(result).toHaveLength(1)
    expect(result[0].percentage).toBe('40%')
    expect(result[0].text).toBe('Market drops 40% in the bear case')
  })

  it('extracts percentage with space (40 %)', () => {
    const result = parseScenarioPercentages('Probability is 40 % for this outcome')
    expect(result[0].percentage).toBe('40%')
  })

  it('extracts percentage in parentheses (80%)', () => {
    const result = parseScenarioPercentages('high chance (80%) for bullish case')
    expect(result[0].percentage).toBe('80%')
  })

  it('returns null for lines without percentages', () => {
    const result = parseScenarioPercentages('Bullish scenario with strong momentum')
    expect(result[0].percentage).toBeNull()
  })

  it('handles multiple lines with mixed percentages', () => {
    const input = 'Bull case: 70% probability\nBear case: 30% probability\nNeutral: steady growth'
    const result = parseScenarioPercentages(input)
    
    expect(result).toHaveLength(3)
    expect(result[0].percentage).toBe('70%')
    expect(result[1].percentage).toBe('30%')
    expect(result[2].percentage).toBeNull()
  })

  it('handles triple-digit percentages (100%)', () => {
    const result = parseScenarioPercentages('Full allocation at 100%')
    expect(result[0].percentage).toBe('100%')
  })

  it('handles empty string', () => {
    const result = parseScenarioPercentages('')
    expect(result).toHaveLength(1)
    expect(result[0].text).toBe('')
    expect(result[0].percentage).toBeNull()
  })

  it('extracts only first percentage if multiple on same line', () => {
    const result = parseScenarioPercentages('Range is 50% to 80% likely')
    expect(result[0].percentage).toBe('50%')
  })
})
