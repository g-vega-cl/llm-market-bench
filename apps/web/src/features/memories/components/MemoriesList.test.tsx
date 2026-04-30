import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoriesList, Memory } from './MemoriesList'

// Mock the Link component from TanStack Router
vi.mock('@tanstack/react-router', async () => {
  const actual = await vi.importActual('@tanstack/react-router')
  return {
    ...actual,
    Link: ({ children, ...props }: any) => (
      <a {...props}>{children}</a>
    ),
  }
})

const mockMemories: Memory[] = [
  {
    id: '1',
    content: 'Consensus on rate hike',
    created_at: new Date().toISOString(),
    metadata: {
      type: 'consensus_event',
      impact: 'BEARISH',
      scenario_analysis: 'Scenario A: Rates go up -> Trading Plan (How to Profit): Buy bank stocks. Scenario B: Rates go down -> Trading Plan (How to Profit): Buy tech stocks.'
    },
    status: 'ACTIVE',
    parent_id: null,
    relationship_type: null,
    relevance_score: null,
    memory_type: 'MARKET_EVENT',
    importance_score: null,
    target_date: null
  },
  {
    id: '2',
    content: 'Decision to buy TSLA',
    created_at: new Date().toISOString(),
    metadata: { type: 'decision_reasoning', ticker: 'TSLA', signal: 'BUY' },
    parent_id: '1',
    relationship_type: 'UPDATE',
    status: 'ACTIVE',
    relevance_score: null,
    memory_type: null,
    importance_score: null,
    target_date: null
  },
  {
    id: '3',
    content: 'Post-mortem on AAPL',
    created_at: new Date().toISOString(),
    metadata: { type: 'post_mortem', ticker: 'AAPL', is_regret: true },
    status: 'RESOLVED',
    parent_id: null,
    relationship_type: null,
    relevance_score: null,
    memory_type: null,
    importance_score: null,
    target_date: null
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

    const eventsButton = screen.getByText('Events')
    fireEvent.click(eventsButton)

    expect(screen.getByText('Consensus on rate hike')).toBeInTheDocument()
    expect(screen.queryByText('Decision to buy TSLA')).not.toBeInTheDocument()
    expect(screen.queryByText('Post-mortem on AAPL')).not.toBeInTheDocument()

    const decisionsButton = screen.getByText('Decisions')
    fireEvent.click(decisionsButton)

    expect(screen.queryByText('Consensus on rate hike')).not.toBeInTheDocument()
    expect(screen.getByText('Decision to buy TSLA')).toBeInTheDocument()
  })

  it('displays metadata badges correctly', () => {
    render(<MemoriesList memories={mockMemories} />)
    expect(screen.getByText('BEARISH')).toBeInTheDocument()
    expect(screen.getByText('$TSLA')).toBeInTheDocument()
    expect(screen.getByText('Regret')).toBeInTheDocument()
  })

  it('shows empty state when no memories match filter', () => {
    render(<MemoriesList memories={[]} />)
    expect(screen.getByText('No memories found in this category')).toBeInTheDocument()
  })

  it('expands scenario analysis when button is clicked', () => {
    render(<MemoriesList memories={mockMemories} />)

    const analysisButton = screen.getByText('Show Analysis')
    expect(screen.queryByText('Scenario Analysis')).not.toBeInTheDocument()

    fireEvent.click(analysisButton)

    expect(screen.getByText('Scenario Analysis')).toBeInTheDocument()
    expect(screen.getByText('Buy bank stocks.')).toBeInTheDocument()
  })

  it('shows event chain link for memories with parent', () => {
    render(<MemoriesList memories={mockMemories} />)
    
    // Memory 2 has a parent
    expect(screen.getByText('View event chain →')).toBeInTheDocument()
  })
})
