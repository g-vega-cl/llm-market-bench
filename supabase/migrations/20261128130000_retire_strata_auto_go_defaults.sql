-- The queue still defaulted to the Strata-first lane that no longer exists:
-- provider 'auto-strata', model 'strata'. Any insert that omitted those columns
-- asked the proxy for a model it does not publish, and the call failed there
-- rather than at the insert.
--
-- Existing rows keep the values they ran with. Only the defaults move, to what
-- the application has been sending since the token work landed.

ALTER TABLE public.recipe_execution_queue
    ALTER COLUMN provider SET DEFAULT 'free-llm-proxy';

ALTER TABLE public.recipe_execution_queue
    ALTER COLUMN model SET DEFAULT 'auto-go';
