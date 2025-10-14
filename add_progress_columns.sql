-- Add progress tracking columns to jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS current_step VARCHAR;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS progress_percentage VARCHAR;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_competitors VARCHAR;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS completed_competitors VARCHAR;
