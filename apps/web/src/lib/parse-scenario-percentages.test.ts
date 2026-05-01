import { describe, it, expect } from 'vitest'
import { parseScenarioPercentages, extractPercentage } from './parse-scenario-percentages'

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

describe('extractPercentage', () => {
  it('extracts percentage from text', () => {
    expect(extractPercentage('Scenario A (65%):')).toBe('65%')
  })

  it('extracts percentage with space', () => {
    expect(extractPercentage('65 % probability of market rally')).toBe('65%')
  })

  it('returns null when no percentage present', () => {
    expect(extractPercentage('Bullish market outlook')).toBeNull()
  })

  it('extracts percentage from inline text', () => {
    expect(extractPercentage('There is a 70% chance of rate hike')).toBe('70%')
  })

  it('handles single-digit percentages', () => {
    expect(extractPercentage('Only 5% chance of recession')).toBe('5%')
  })

  it('returns first percentage if multiple exist', () => {
    expect(extractPercentage('60% bull case, 40% bear case')).toBe('60%')
  })
})
