BEGIN;

DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS vector;
    EXCEPTION
        WHEN undefined_file THEN
            RAISE NOTICE 'pgvector extension not available; continuing without vector indexes';
    END;
END
$$;

COMMIT;
