-- Add trade_id to decisions table for Attribution Locking (Step 13)
ALTER TABLE decisions
ADD COLUMN IF NOT EXISTS trade_id UUID REFERENCES trades(id);

-- Optional: Index on trade_id for faster lookup of decisions by trade
CREATE INDEX IF NOT EXISTS decisions_trade_id_idx ON decisions(trade_id);
