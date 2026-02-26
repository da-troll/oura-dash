-- Migration 005: Fix chat trigger function for environments where 004 failed
-- This is a compatibility repair migration. Safe to run even if 004 was already fixed.

BEGIN;

-- Ensure the trigger function exists (idempotent)
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Re-create trigger only if chat_conversations table exists
-- (no-op safe if table doesn't exist yet)
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'chat_conversations') THEN
    -- Drop and recreate to ensure it points to the correct function
    DROP TRIGGER IF EXISTS set_updated_at_chat_conversations ON chat_conversations;
    CREATE TRIGGER set_updated_at_chat_conversations
        BEFORE UPDATE ON chat_conversations
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;

COMMIT;
