-- Migration to unify memory_type across database and frontend
-- Elevates academic papers and post-mortems from overloaded LESSON_LEARNED into first-class memory_types

-- Update academic papers
UPDATE public.memories
SET memory_type = 'ACADEMIC_PAPER'
WHERE memory_type = 'LESSON_LEARNED'
  AND metadata->>'source_type' = 'academic_paper';

-- Update post-mortems
UPDATE public.memories
SET memory_type = 'POST_MORTEM'
WHERE memory_type = 'LESSON_LEARNED'
  AND metadata->>'analysis_window' IS NOT NULL;
