import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoriesList, Memory } from './components/-MemoriesList'

const mockMemories: Memory[] = [
  {
    id: '1',
    content: 'Consensus on rate hike',
    created_at: new Date().toISOString(),
    metadata: { 
      type: 'consensus_event', 
      impact: 'BEARISH',
      scenario_analysis: 'Scenario A: Rates go up -> Trading Plan (How to Profit): Buy bank stocks. Scenario B: Rates go down -> Trading Plan (How to Profit): Buy tech stocks.'
    }
  },
  {
    id: '2',
    content: 'Decision to buy TSLA',
    created_at: new Date().toISOString(),
    metadata: { type: 'decision_reasoning', ticker: 'TSLA', signal: 'BUY' }
  },
  {
    id: '3',
    content: 'Post-mortem on AAPL',
    created_at: new Date().toISOString(),
    metadata: { type: 'post_mortem', ticker: 'AAPL', is_regret: true }
  }
]

describe('MemoriesList', () => {
  it('renders all memories by default', () => {
    render(<MemoriesList memories={mockMemories} />)
    expect(screen.getByText('Consensus on rate hike')).toBeInTheDocument()
    expect(screen.getByText('Decision to buy TSLA')).toBeInTheDocument()
    expect(screen.getByText('Post-mortem on AAPL')).toBeInTheDocument()
  })

  it('filters memories by type when button is clicked', () => {
    render(<MemoriesList memories={mockMemories} />)
    
    const consensusButton = screen.getByText('CONSENSUS EVENT')
    fireEvent.click(consensusButton)
    
    expect(screen.getByText('Consensus on rate hike')).toBeInTheDocument()
    expect(screen.queryByText('Decision to buy TSLA')).not.toBeInTheDocument()
    expect(screen.queryByText('Post-mortem on AAPL')).not.toBeInTheDocument()
    
    const decisionButton = screen.getByText('DECISION REASONING')
    fireEvent.click(decisionButton)
    
    expect(screen.queryByText('Consensus on rate hike')).not.toBeInTheDocument()
    expect(screen.getByText('Decision to buy TSLA')).toBeInTheDocument()
  })

  it('displays metadata correctly', () => {
    render(<MemoriesList memories={mockMemories} />)
    expect(screen.getByText('Impact: BEARISH')).toBeInTheDocument()
    expect(screen.getByText('Ticker: TSLA')).toBeInTheDocument()
    expect(screen.getByText('Regret')).toBeInTheDocument()
  })

  it('shows empty state when no memories match filter', () => {
    render(<MemoriesList memories={[]} />)
    expect(screen.getByText('No memories found for this category.')).toBeInTheDocument()
  })

  it('expands how to profit section when button is clicked', () => {
    render(<MemoriesList memories={mockMemories} />)
    
    const profitButton = screen.getByText('How to Profit from this')
    expect(screen.queryByText('Profit Analysis & Chains of Events')).not.toBeInTheDocument()
    
    fireEvent.click(profitButton)
    
    expect(screen.getByText('Profit Analysis & Chains of Events')).toBeInTheDocument()
    expect(screen.getByText('Buy bank stocks.')).toBeInTheDocument()
  })
})
