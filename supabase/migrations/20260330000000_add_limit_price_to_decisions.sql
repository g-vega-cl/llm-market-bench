-- Migration: Add limit_price column to decisions table
-- Created: 2026-03-30

ALTER TABLE decisions ADD COLUMN limit_price NUMERIC;
