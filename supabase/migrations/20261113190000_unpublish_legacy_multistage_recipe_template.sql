-- Recipe Studio: one LLM call per strategy.
--
-- The Studio is limited to a single Push v2 stage, enforced in the engine
-- schema (apps/engine/recipes/push_schema.py) and in the web save and enqueue
-- paths. This migration closes the two remaining gaps at the database boundary:
--
-- 1. The legacy "2-Stage Research -> Trade Decision" template is unpublished.
--    It was removed from packages/config/starter-recipes.json, so the seeder
--    never recreates it. The row is kept for auditability but is no longer
--    publicly readable, and the enqueue API rejects a multi-stage graph.
--
-- 2. A CHECK constraint makes a multi-stage graph_json unrepresentable for new
--    and updated rows. It is added NOT VALID so the legacy row above does not
--    block the change; validate it once the legacy row is cleaned up.
--
-- No RLS or GRANT changes: both tables keep their existing policies and grants.

UPDATE public.strategy_recipes
SET is_public = FALSE,
    is_template = FALSE,
    updated_at = NOW()
WHERE name = '2-Stage Research -> Trade Decision';

ALTER TABLE public.strategy_recipes
    ADD CONSTRAINT strategy_recipes_single_stage_check
    CHECK (
        jsonb_typeof(graph_json -> 'stages') IS NULL
        OR jsonb_array_length(graph_json -> 'stages') = 1
    ) NOT VALID;
