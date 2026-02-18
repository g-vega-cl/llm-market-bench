import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { HumanFriendlyResponse, HumanFriendlyPrompt } from './index'
import * as React from 'react'

// Mock navigator.clipboard
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
            reasoning: 'Apple is doing great. '.repeat(10), // long text
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
    { role: 'assistant', content: '{"decisions": [{"ticker": "AAPL", "signal": "BUY"}]}' } // JSON string content
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

        // Default tab is 'decisions'
        expect(screen.getByText('AAPL')).toBeInTheDocument()
        expect(screen.getByText('BUY')).toBeInTheDocument()

        // Switch to 'macro events'
        fireEvent.click(screen.getByText('macro events'))
        expect(screen.getByText('Fed Pivot')).toBeInTheDocument()
        expect(screen.getByText('BULLISH')).toBeInTheDocument()
    })

    it('renders RAW tab with JSON and copy button', () => {
        render(<HumanFriendlyResponse response={mockResponse} />)

        fireEvent.click(screen.getByText('RAW'))
        expect(screen.getByText('Copy JSON')).toBeInTheDocument()
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
        // The assistant message contains JSON, FormattedContent should try to parse it
        // We look for a part of the formatted JSON string
        expect(screen.getByText(/\"ticker\": \"AAPL\"/)).toBeInTheDocument()
    })
})
