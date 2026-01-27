import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ConceptMap, type Concept } from './-ConceptMap'

describe('ConceptMap', () => {
  const mockData: Concept[] = [
    {
      id: '1',
      concept_name: 'Inflation',
      pca_x: 0.5,
      pca_y: 0.5,
      mention_count: 50,
      velocity_score: 2.5,
      first_mention_at: '2024-01-01',
    },
    {
      id: '2',
      concept_name: 'AI',
      pca_x: -0.5,
      pca_y: -0.5,
      mention_count: 100,
      velocity_score: 5.0,
      first_mention_at: '2024-01-01',
    },
  ]

  it('renders without crashing', () => {
    const { container } = render(<ConceptMap data={mockData} />)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
  })
})
