AUDIT_CHECKS = [
    {
        "id": "orphan_trade_refs",
        "title": "Orphaned Trade References",
        "description": "Decisions with trade_id pointing to non-existent trades",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT id, trade_id, status, created_at
                FROM decisions
                WHERE trade_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM trades WHERE trades.id = decisions.trade_id)
            ) t
        """,
        "severity": "HIGH",
        "source_table": "decisions",
        "analysis_method": "SQL_CHECK",
    },
    {
        "id": "orphan_portfolio_trades",
        "title": "Trades with Invalid Portfolio",
        "description": "Trades referencing portfolio_id that doesn't exist",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT id, portfolio_id
                FROM trades
                WHERE NOT EXISTS (SELECT 1 FROM portfolios WHERE portfolios.id = trades.portfolio_id)
            ) t
        """,
        "severity": "CRITICAL",
        "source_table": "trades",
        "analysis_method": "SQL_CHECK",
    },
    {
        "id": "orphan_portfolio_positions",
        "title": "Positions with Invalid Portfolio",
        "description": "Portfolio positions referencing portfolio_id that doesn't exist",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT id, portfolio_id, ticker
                FROM portfolio_positions
                WHERE NOT EXISTS (SELECT 1 FROM portfolios WHERE portfolios.id = portfolio_positions.portfolio_id)
            ) t
        """,
        "severity": "HIGH",
        "source_table": "portfolio_positions",
        "analysis_method": "SQL_CHECK",
    },
    {
        "id": "executed_without_trade",
        "title": "Executed Decisions Without Trade Record",
        "description": "Decisions marked EXECUTED but no corresponding trade exists",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT d.id, d.status, d.ticker, d.created_at
                FROM decisions d
                WHERE d.status = 'EXECUTED'
                AND NOT EXISTS (SELECT 1 FROM trades t WHERE t.decision_id = d.id)
            ) t
        """,
        "severity": "CRITICAL",
        "source_table": "decisions",
        "analysis_method": "SQL_CHECK",
    },
    {
        "id": "invalid_decision_status",
        "title": "Invalid Decision Status Values",
        "description": "Decisions with status values not in the valid set",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT id, status, created_at
                FROM decisions
                WHERE status NOT IN ('CREATED', 'EXECUTED', 'VALIDATED', 'REJECTED_MARGIN', 'REJECTED_OWNERSHIP', 'REJECTED_REDUNDANCY', 'REJECTED_TOOL_USAGE', 'REJECTED_VERIFICATION', 'REJECTED_HALLUCINATION', 'REJECTED_PRICE_DEVIATION', 'REJECTED_LIQUIDITY', 'REJECTED_MARKET_CLOSED', 'REJECTED_LIMIT_PRICE', 'REJECTED_STALE_QUOTE', 'ERROR_PROVIDER')
            ) t
        """,
        "severity": "MEDIUM",
        "source_table": "decisions",
        "analysis_method": "SQL_CHECK",
    },
    {
        "id": "stale_created_decisions",
        "title": "Stale CREATED Decisions",
        "description": "Decisions stuck in CREATED status for more than 7 days",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT id, status, created_at
                FROM decisions
                WHERE status = 'CREATED'
                AND created_at < NOW() - INTERVAL '7 days'
            ) t
        """,
        "severity": "MEDIUM",
        "source_table": "decisions",
        "analysis_method": "SQL_CHECK",
    },
    {
        "id": "duplicate_positions",
        "title": "Duplicate Portfolio Positions",
        "description": "Multiple active positions for same portfolio and ticker",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT portfolio_id, ticker, COUNT(*) as count
                FROM portfolio_positions
                GROUP BY portfolio_id, ticker
                HAVING COUNT(*) > 1
            ) t
        """,
        "severity": "HIGH",
        "source_table": "portfolio_positions",
        "analysis_method": "SQL_CHECK",
    },
    {
        "id": "future_catalyst_past_date",
        "title": "Past Dates Marked as Future Catalyst",
        "description": "Memories marked as future catalysts but target_date has passed",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT id, target_date, memory_type
                FROM memories
                WHERE (metadata->>'is_future_catalyst')::boolean = true
                AND target_date IS NOT NULL
                AND target_date < CURRENT_DATE::text
            ) t
        """,
        "severity": "MEDIUM",
        "source_table": "memories",
        "analysis_method": "SQL_CHECK",
    },
    {
        "id": "empty_reasoning",
        "title": "Empty Reasoning in Decisions",
        "description": "Decisions with null or empty reasoning field",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT id, status, ticker, created_at
                FROM decisions
                WHERE reasoning IS NULL OR reasoning = ''
            ) t
        """,
        "severity": "LOW",
        "source_table": "decisions",
        "analysis_method": "SQL_CHECK",
    },
    {
        "id": "null_embeddings",
        "title": "Missing Embeddings",
        "description": "Memories or decisions with null embedding vectors",
        "query": """
            SELECT row_to_json(t)::jsonb FROM (
                SELECT id, 'memories' as source_table FROM memories WHERE embedding IS NULL
                UNION ALL
                SELECT id, 'decisions' as source_table FROM decisions WHERE embedding IS NULL
            ) t
        """,
        "severity": "LOW",
        "source_table": "memories",
        "analysis_method": "SQL_CHECK",
    },
]
