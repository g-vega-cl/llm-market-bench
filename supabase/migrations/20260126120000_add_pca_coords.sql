-- Add PCA coordinate columns for 2D visualization
ALTER TABLE "concept_metrics"
ADD COLUMN IF NOT EXISTS "pca_x" double precision,
ADD COLUMN IF NOT EXISTS "pca_y" double precision;

-- Add index for performance on fetching
CREATE INDEX IF NOT EXISTS "concept_metrics_pca_coords_idx" ON "concept_metrics" ("pca_x", "pca_y");
