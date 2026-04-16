import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { HumanFriendlyResponse, HumanFriendlyPrompt } from './index'
import * as React from 'react'

Object.assign(navigator, {
    clipboard: {
        writeText: vi.fn(),
    },
})

const mockResponse = {
    decisions: [
        {
            ticker: 'AAPL',
            signal: 'BUY',
            reasoning: 'Apple is doing great. '.repeat(10),
            confidence: 90
        }
    ],
    macro_events: [
        {
            event_name: 'Fed Pivot',
            impact: 'BULLISH',
            reasoning: 'Inflation is cooling down.'
        }
    ]
}

const mockPrompt = [
    { role: 'system', content: 'You are a financial analyst.' },
    { role: 'user', content: 'What about AAPL?' },
    { role: 'assistant', content: '{"decisions": [{"ticker": "AAPL", "signal": "BUY"}]}' }
]

const manyRolesPrompt = [
    { role: 'system', content: 'System prompt 1' },
    { role: 'system', content: 'System prompt 2' },
    { role: 'user', content: 'User question' },
    { role: 'user', content: 'User follow-up' },
    { role: 'assistant', content: 'Assistant response' },
    { role: 'tool', content: 'Tool result' }
]

describe('HumanFriendlyResponse', () => {
    it('renders tabs for top-level keys', () => {
        render(<HumanFriendlyResponse response={mockResponse} />)
        expect(screen.getByText('decisions')).toBeInTheDocument()
        expect(screen.getByText('macro events')).toBeInTheDocument()
        expect(screen.getByText('RAW')).toBeInTheDocument()
    })

    it('shows data for the selected tab', () => {
        render(<HumanFriendlyResponse response={mockResponse} />)

        expect(screen.getByText('AAPL')).toBeInTheDocument()
        expect(screen.getByText('BUY')).toBeInTheDocument()

        fireEvent.click(screen.getByText('macro events'))
        expect(screen.getByText('Fed Pivot')).toBeInTheDocument()
        expect(screen.getByText('BULLISH')).toBeInTheDocument()
    })

    it('renders RAW tab with JSON and copy button', () => {
        render(<HumanFriendlyResponse response={mockResponse} />)

        fireEvent.click(screen.getByText('RAW'))
        expect(screen.getByText('Copy JSON')).toBeInTheDocument()
    })

    it('renders string response in RAW format', () => {
        render(<HumanFriendlyResponse response="simple string" />)
        expect(screen.getByText(/"simple string"/)).toBeInTheDocument()
    })

    it('renders null response correctly', () => {
        render(<HumanFriendlyResponse response={null} />)
        expect(screen.getByText(/null/)).toBeInTheDocument()
    })

    it('renders empty array in RAW format', () => {
        render(<HumanFriendlyResponse response={[]} />)
        expect(screen.getByText('[]')).toBeInTheDocument()
    })
})

describe('HumanFriendlyPrompt', () => {
    it('renders messages correctly', () => {
        render(<HumanFriendlyPrompt prompt={mockPrompt} />)
        expect(screen.getByText('system')).toBeInTheDocument()
        expect(screen.getByText('user')).toBeInTheDocument()
        expect(screen.getByText('assistant')).toBeInTheDocument()
        expect(screen.getByText('You are a financial analyst.')).toBeInTheDocument()
    })

    it('parses JSON content in assistant messages', () => {
        render(<HumanFriendlyPrompt prompt={mockPrompt} />)
        expect(screen.getByText(/"ticker": "AAPL"/)).toBeInTheDocument()
    })

    it('shows role tabs when prompt has more than 3 messages', () => {
        render(<HumanFriendlyPrompt prompt={manyRolesPrompt} />)
        expect(screen.getByText('ALL')).toBeInTheDocument()
        const systemButtons = screen.getAllByText('system')
        expect(systemButtons.length).toBeGreaterThanOrEqual(1)
    })

    it('filters messages by role when role tab is clicked', () => {
        render(<HumanFriendlyPrompt prompt={manyRolesPrompt} />)

        const userButtons = screen.getAllByText('user')
        fireEvent.click(userButtons[0])
    })

    it('renders tool role messages correctly', () => {
        render(<HumanFriendlyPrompt prompt={[{ role: 'tool', content: 'Tool output' }]} />)
        expect(screen.getByText('tool')).toBeInTheDocument()
        expect(screen.getByText('Tool output')).toBeInTheDocument()
    })

    it('renders thought content in messages', () => {
        const promptWithThought = [
            { role: 'assistant', parts: [{ thought: 'Let me think about this' }, { text: 'Final answer' }] }
        ]
        render(<HumanFriendlyPrompt prompt={promptWithThought} />)
        expect(screen.getByText('Internal Thought')).toBeInTheDocument()
        expect(screen.getByText('Let me think about this')).toBeInTheDocument()
    })

    it('renders function call content in messages', () => {
        const promptWithFunction = [
            { role: 'assistant', parts: [{ function_call: { name: 'get_stock_quote', args: { ticker: 'AAPL' } } }] }
        ]
        render(<HumanFriendlyPrompt prompt={promptWithFunction} />)
        expect(screen.getByText('Tool Call: get_stock_quote')).toBeInTheDocument()
        expect(screen.getByText(/"ticker": "AAPL"/)).toBeInTheDocument()
    })
})
