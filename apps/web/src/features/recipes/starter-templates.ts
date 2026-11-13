import type { PushStrategy } from './types';

export const STARTER_RECIPES: PushStrategy[] = [
    {
        version: '2.0-push',
        name: 'Trump & Chips News Momentum',
        description:
            'Single-stage push prompt combining chip-tariff news, relevant market memories, and technical screening criteria.',
        cadence: '1d',
        stages: [
            {
                id: 'stage-1',
                title: 'Stage 1: Catalyst & Technical Analysis',
                selected_tools: [
                    'get_technical_indicators',
                    'get_key_metrics',
                    'get_price_history',
                    'get_todays_news_menu',
                ],
                blocks: [
                    {
                        id: 'blk-prompt-1',
                        type: 'prompt',
                        text: 'Analyze the injected news catalysts and historical memories. Use the tools to verify valuations and technicals.',
                    },
                    {
                        id: 'blk-news-1',
                        type: 'news',
                        contains: ['Trump', 'chips'],
                        recency_hours: 48,
                    },
                    {
                        id: 'blk-mem-1',
                        type: 'memories',
                        contains: ['tariff', 'semiconductor'],
                        recency_hours: 168,
                        category: 'MARKET_EVENT',
                        min_importance: 5,
                    },
                    {
                        id: 'blk-tech-1',
                        type: 'technicals',
                        rules: [
                            { id: 'rule-pe', metric: 'P/E', operator: '<', target: '45' },
                            { id: 'rule-rsi', metric: 'RSI', operator: '<', target: '70' },
                        ],
                    },
                    {
                        id: 'blk-format-1',
                        type: 'output_format',
                    },
                ],
            },
        ],
    },
    {
        version: '2.0-push',
        name: '2-Stage Research -> Trade Decision',
        description:
            'Two sequential LLM calls: Stage 1 narrows candidates from news + memories; Stage 2 checks technicals & fundamentals before issuing trades.',
        cadence: '1d',
        stages: [
            {
                id: 'stage-1',
                title: 'Stage 1: News & Memory Screener',
                selected_tools: ['get_todays_news_menu', 'fetch_newsletter_content'],
                blocks: [
                    {
                        id: 'blk-s1-prompt',
                        type: 'prompt',
                        text: 'Identify up to 3 tickers most impacted by recent Fed/macro news and our past lessons.',
                    },
                    {
                        id: 'blk-s1-news',
                        type: 'news',
                        contains: ['Fed', 'rates', 'inflation'],
                        recency_hours: 72,
                    },
                    {
                        id: 'blk-s1-mem',
                        type: 'memories',
                        contains: ['FOMC'],
                        recency_hours: 336,
                        category: 'ALL',
                        min_importance: 6,
                    },
                ],
            },
            {
                id: 'stage-2',
                title: 'Stage 2: Technical Audit & Execution',
                selected_tools: [
                    'get_technical_indicators',
                    'get_key_metrics',
                    'get_price_history',
                ],
                blocks: [
                    {
                        id: 'blk-s2-prompt',
                        type: 'prompt',
                        text: 'Review Stage 1 candidates:\n{{prev_output}}\nVerify technicals and fundamentals.',
                    },
                    {
                        id: 'blk-s2-tech',
                        type: 'technicals',
                        rules: [
                            {
                                id: 'rule-vwap',
                                metric: 'Price vs VWAP',
                                operator: '>',
                                target: '0%',
                            },
                            { id: 'rule-fcf', metric: 'FCF', operator: '>', target: '0' },
                        ],
                    },
                    {
                        id: 'blk-format-2',
                        type: 'output_format',
                    },
                ],
            },
        ],
    },
];
