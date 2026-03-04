BEGIN;

ALTER TABLE chat_conversations
    ADD COLUMN IF NOT EXISTS memory_summary TEXT NOT NULL DEFAULT '';

COMMIT;
