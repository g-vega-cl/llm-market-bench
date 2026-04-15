import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { PerformanceChart } from './-PerformanceChart'

vi.mock('d3', async (importOriginal) => {
  const actual = await importOriginal<typeof import('d3')>()
  const mockSelection = {
    selectAll: vi.fn().mockReturnThis(),
    remove: vi.fn().mockReturnThis(),
    append: vi.fn().mockReturnThis(),
    attr: vi.fn().mockReturnThis(),
    style: vi.fn().mockReturnThis(),
    datum: vi.fn().mockReturnThis(),
    call: vi.fn().mockReturnThis(),
    on: vi.fn().mockReturnThis(),
    empty: vi.fn().mockReturnValue(false),
    select: vi.fn().mockReturnThis(),
    text: vi.fn().mockReturnThis(),
  }
  return {
    ...actual,
    select: vi.fn().mockReturnValue(mockSelection),
  }
})

test('renders PerformanceChart component with equity curve', () => {
  const mockData = [
    { date: '2023-01-01', total_equity: 10000 },
    { date: '2023-01-02', total_equity: 10500 },
  ]

  render(<PerformanceChart data={mockData} />)
  expect(screen.getByText(/Equity Curve/i)).toBeInTheDocument()
})

test('renders PerformanceChart with benchmark comparison', () => {
  const mockData = [
    { date: '2023-01-01', total_equity: 10000 },
    { date: '2023-01-02', total_equity: 10500 },
  ]
  const mockBenchmarkData = {
    SPY: [
      { date: '2023-01-01', price: 100 },
      { date: '2023-01-02', price: 102 },
    ],
  }

  render(
    <PerformanceChart
      data={mockData}
      benchmarkData={mockBenchmarkData}
      selectedBenchmark="SPY"
      showPercentage={true}
    />
  )
  expect(screen.getByText(/Performance vs Benchmark/i)).toBeInTheDocument()
})

test('shows percentage normalization label when benchmark is selected', () => {
  const mockData = [
    { date: '2023-01-01', total_equity: 10000 },
    { date: '2023-01-02', total_equity: 10500 },
  ]
  const mockBenchmarkData = {
    QQQ: [
      { date: '2023-01-01', price: 50 },
      { date: '2023-01-02', price: 51 },
    ],
  }

  render(
    <PerformanceChart
      data={mockData}
      benchmarkData={mockBenchmarkData}
      selectedBenchmark="QQQ"
      showPercentage={true}
    />
  )
  expect(screen.getByText(/Normalized to percentage returns/i)).toBeInTheDocument()
})

test('renders without benchmark when showPercentage is false', () => {
  const mockData = [
    { date: '2023-01-01', total_equity: 10000 },
    { date: '2023-01-02', total_equity: 10500 },
  ]
  const mockBenchmarkData = {
    SPY: [
      { date: '2023-01-01', price: 100 },
      { date: '2023-01-02', price: 102 },
    ],
  }

  render(
    <PerformanceChart
      data={mockData}
      benchmarkData={mockBenchmarkData}
      selectedBenchmark="SPY"
      showPercentage={false}
    />
  )
  expect(screen.getByText(/Equity Curve/i)).toBeInTheDocument()
})

test('displays latest equity value in inline card', () => {
  const mockData = [
    { date: '2023-01-01', total_equity: 10000 },
    { date: '2023-01-02', total_equity: 10500 },
  ]

  render(<PerformanceChart data={mockData} />)
  expect(screen.getByText('$10,500.00')).toBeInTheDocument()
  expect(screen.getByText('2023-01-02')).toBeInTheDocument()
})
