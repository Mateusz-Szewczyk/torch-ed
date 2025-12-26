-- Migration: Add meta_json column to messages table
-- Date: 2024-12-26
-- Description: Adds a nullable meta_json column to store JSON with steps and actions
-- Note: 'metadata' is a reserved attribute in SQLAlchemy Declarative API

-- PostgreSQL / SQLite compatible
ALTER TABLE messages ADD COLUMN IF NOT EXISTS meta_json TEXT;

-- For PostgreSQL (if IF NOT EXISTS doesn't work)
-- DO $$
-- BEGIN
--     IF NOT EXISTS (
--         SELECT 1 FROM information_schema.columns
--         WHERE table_name = 'messages' AND column_name = 'meta_json'
--     ) THEN
--         ALTER TABLE messages ADD COLUMN meta_json TEXT;
--     END IF;
-- END $$;

-- Note: The meta_json column stores JSON string with the following structure:
-- {
--   "steps": [
--     {"content": "Step description", "status": "complete"}
--   ],
--   "actions": [
--     {"type": "flashcards", "id": 123, "name": "New Deck", "count": 20}
--   ]
-- }
