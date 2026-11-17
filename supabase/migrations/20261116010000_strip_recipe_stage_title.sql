-- Recipe Studio: drop the obsolete per-stage title.
--
-- The Studio makes exactly one LLM call, so the user-editable stage title was a
-- leftover from the multi-stage experiment. It duplicated (and shadowed) the
-- recipe name, so the field is now gone from the web stage type
-- (apps/web/src/features/recipes/types.ts), the engine schema
-- (apps/engine/recipes/push_schema.py), and the starter template
-- (packages/config/starter-recipes.json).
--
-- Pydantic ignores the unknown key, so loaded graphs keep working either way.
-- This migration only cleans the stored configs so the database matches the
-- schema again. recipe_execution_queue.result_json rows are historical run
-- telemetry and are intentionally left untouched.
--
-- No RLS or GRANT changes: existing policies and grants stay as they are.
--
-- Scope is limited to single-stage graphs: the legacy unpublished
-- "2-Stage Research -> Trade Decision" row cannot be updated at all, because
-- strategy_recipes_single_stage_check (added NOT VALID in
-- 20261113190000_unpublish_legacy_multistage_recipe_template.sql) rejects any
-- update that leaves two stages in place. That row is neither public nor a
-- template nor live, so its inert title is left as audit history.

-- Boolean subexpressions are not evaluated left to right, so the array-length
-- and element checks are gated by CASE instead of a sibling AND guard: the
-- single-stage CHECK is NOT VALID, so a row whose `stages` is an object or
-- scalar was never scanned and must not abort the migration.
WITH candidates AS (
    SELECT id
    FROM public.strategy_recipes
    WHERE jsonb_typeof(graph_json -> 'stages') = 'array'
      AND CASE
          WHEN jsonb_typeof(graph_json -> 'stages') = 'array'
          THEN jsonb_array_length(graph_json -> 'stages') = 1
          ELSE FALSE
      END
      AND CASE
          WHEN jsonb_typeof(graph_json -> 'stages') = 'array'
          THEN EXISTS (
              SELECT 1
              FROM jsonb_array_elements(graph_json -> 'stages') AS stage
              WHERE stage ? 'title'
          )
          ELSE FALSE
      END
)
UPDATE public.strategy_recipes AS sr
SET graph_json = jsonb_set(
        sr.graph_json,
        '{stages}',
        (
            SELECT jsonb_agg(stage - 'title')
            FROM jsonb_array_elements(sr.graph_json -> 'stages') AS stage
        ),
        false
    ),
    updated_at = NOW()
FROM candidates
WHERE sr.id = candidates.id;
