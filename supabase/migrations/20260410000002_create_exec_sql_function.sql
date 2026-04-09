-- Create exec_sql function for running arbitrary read queries (audit checks)
-- This is only used by the audit system for internal diagnostics
CREATE OR REPLACE FUNCTION public.exec_sql(query TEXT)
RETURNS TABLE(result JSONB)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY EXECUTE query;
END;
$$;