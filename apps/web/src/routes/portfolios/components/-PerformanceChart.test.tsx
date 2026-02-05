import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { PerformanceChart } from './-PerformanceChart'

// Mock d3 since it's hard to test SVG output in jsdom
vi.mock('d3', async (importOriginal) => {
  const actual = await importOriginal<typeof import('d3')>()
  return {
    ...actual,
    select: vi.fn().mockReturnValue({
      selectAll: vi.fn().mockReturnThis(),
      remove: vi.fn().mockReturnThis(),
      append: vi.fn().mockReturnThis(),
      attr: vi.fn().mockReturnThis(),
      style: vi.fn().mockReturnThis(),
      datum: vi.fn().mockReturnThis(),
      call: vi.fn().mockReturnThis(),
      on: vi.fn().mockReturnThis(),
    }),
  }
})

test('renders PerformanceChart component', () => {
  const mockData = [
    { date: '2023-01-01', total_equity: 10000 },
    { date: '2023-01-02', total_equity: 10500 },
  ]

  render(<PerformanceChart data={mockData} />)
  expect(screen.getByText(/Equity Curve/i)).toBeInTheDocument()
})
