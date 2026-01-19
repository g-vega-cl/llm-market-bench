-- Create trades table for immutable execution ledger
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    ticker TEXT NOT NULL,
    signal TEXT NOT NULL, -- 'BUY' or 'SELL'
    quantity INTEGER NOT NULL,
    price NUMERIC NOT NULL,
    total_cost NUMERIC NOT NULL,
    executed_at TIMESTAMPTZ DEFAULT now(),
    
    -- Optional: Link back to the decision that caused this trade
    -- Note: We might update this AFTER trade creation in Step 13, 
    -- or we can pass decision_id if available. 
    -- For now, we'll keep it nullable and separate as per Step 13 "Attribution Locking".
    decision_id UUID
);

-- Index for fast lookup by portfolio
CREATE INDEX trades_portfolio_id_idx ON trades(portfolio_id);
