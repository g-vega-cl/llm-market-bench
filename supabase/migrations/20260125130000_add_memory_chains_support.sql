-- Migration to add support for Memory Chains
-- This allows linking related events and tracking their resolution state.

-- 1. Add status column with check constraint
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='memories' AND column_name='status') THEN
        ALTER TABLE public.memories ADD COLUMN status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'RESOLVED', 'SUPERSEDED'));
    END IF;
END $$;

-- 2. Add parent_id column for self-referencing links
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='memories' AND column_name='parent_id') THEN
        ALTER TABLE public.memories ADD COLUMN parent_id UUID REFERENCES public.memories(id);
    END IF;
END $$;

-- 3. Add relationship_type column
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='memories' AND column_name='relationship_type') THEN
        ALTER TABLE public.memories ADD COLUMN relationship_type TEXT CHECK (relationship_type IN ('REVERSAL', 'UPDATE', 'RESOLUTION', 'GENERAL'));
    END IF;
END $$;

-- Enable RLS for everyone to read the new columns (already enabled, but making sure)
-- Policies usually apply to all columns unless specified otherwise.
