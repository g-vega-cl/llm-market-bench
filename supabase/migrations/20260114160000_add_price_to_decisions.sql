-- Migration: Add price column to decisions table
-- Created: 2026-01-14

ALTER TABLE decisions ADD COLUMN price NUMERIC;
