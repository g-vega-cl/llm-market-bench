-- Add evaluation_audit_data JSONB column to sector_predictions table for price auditability
ALTER TABLE public.sector_predictions
    ADD COLUMN IF NOT EXISTS evaluation_audit_data JSONB;
