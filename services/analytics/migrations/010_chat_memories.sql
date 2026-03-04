BEGIN;

DO $$
DECLARE
    has_vector boolean;
BEGIN
    SELECT to_regtype('vector') IS NOT NULL INTO has_vector;

    IF has_vector THEN
        EXECUTE '
            CREATE TABLE IF NOT EXISTS chat_memories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                memory_type TEXT NOT NULL CHECK (memory_type IN (''profile'', ''preference'', ''goal'', ''episodic'')),
                content TEXT NOT NULL,
                content_norm TEXT NOT NULL,
                confidence DOUBLE PRECISION NOT NULL DEFAULT 0.7 CHECK (confidence >= 0 AND confidence <= 1),
                importance DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
                source_conversation_id UUID REFERENCES chat_conversations(id) ON DELETE SET NULL,
                source_message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
                expires_at TIMESTAMPTZ,
                last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                embedding vector(1024),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        ';
    ELSE
        EXECUTE '
            CREATE TABLE IF NOT EXISTS chat_memories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                memory_type TEXT NOT NULL CHECK (memory_type IN (''profile'', ''preference'', ''goal'', ''episodic'')),
                content TEXT NOT NULL,
                content_norm TEXT NOT NULL,
                confidence DOUBLE PRECISION NOT NULL DEFAULT 0.7 CHECK (confidence >= 0 AND confidence <= 1),
                importance DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
                source_conversation_id UUID REFERENCES chat_conversations(id) ON DELETE SET NULL,
                source_message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
                expires_at TIMESTAMPTZ,
                last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                embedding DOUBLE PRECISION[],
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        ';
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_chat_memories_user_type_seen
    ON chat_memories (user_id, memory_type, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_memories_user_content_norm
    ON chat_memories (user_id, content_norm);

DO $$
BEGIN
    IF to_regtype('vector') IS NOT NULL THEN
        BEGIN
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_chat_memories_embedding_hnsw ON chat_memories USING hnsw (embedding vector_cosine_ops)';
        EXCEPTION
            WHEN undefined_object OR feature_not_supported THEN
                RAISE NOTICE 'HNSW index not available; continuing without ANN index';
        END;
    END IF;
END
$$;

ALTER TABLE chat_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_memories FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'chat_memories' AND policyname = 'user_isolation_select'
    ) THEN
        EXECUTE 'CREATE POLICY user_isolation_select ON chat_memories FOR SELECT USING (user_id = NULLIF(current_setting(''app.current_user_id'', true), '''')::uuid)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'chat_memories' AND policyname = 'user_isolation_insert'
    ) THEN
        EXECUTE 'CREATE POLICY user_isolation_insert ON chat_memories FOR INSERT WITH CHECK (user_id = NULLIF(current_setting(''app.current_user_id'', true), '''')::uuid)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'chat_memories' AND policyname = 'user_isolation_update'
    ) THEN
        EXECUTE 'CREATE POLICY user_isolation_update ON chat_memories FOR UPDATE USING (user_id = NULLIF(current_setting(''app.current_user_id'', true), '''')::uuid) WITH CHECK (user_id = NULLIF(current_setting(''app.current_user_id'', true), '''')::uuid)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'chat_memories' AND policyname = 'user_isolation_delete'
    ) THEN
        EXECUTE 'CREATE POLICY user_isolation_delete ON chat_memories FOR DELETE USING (user_id = NULLIF(current_setting(''app.current_user_id'', true), '''')::uuid)';
    END IF;
END
$$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON chat_memories TO app_user;
    END IF;
END
$$;

COMMIT;
