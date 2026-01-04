-- =============================================================================
-- MIGRACJA: Tworzenie tabel dla Workspace, Documents, Images
-- WAŻNE: Wykonaj te polecenia w podanej kolejności!
-- =============================================================================

-- 1. TABELA KATEGORII (rodzic dla workspace_documents)
-- Sprawdź czy już istnieje
CREATE TABLE IF NOT EXISTS file_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id_) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_category_name_user UNIQUE NULLS NOT DISTINCT (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_file_categories_user ON file_categories(user_id);

-- 2. TABELA WORKSPACES
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id_) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workspaces_user ON workspaces(user_id);

-- 3. TABELA WORKSPACE_CATEGORIES (many-to-many)
CREATE TABLE IF NOT EXISTS workspace_categories (
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES file_categories(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (workspace_id, category_id)
);

-- 4. TABELA WORKSPACE_DOCUMENTS (RODZIC dla sections i images)
CREATE TABLE IF NOT EXISTS workspace_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id_) ON DELETE CASCADE,
    category_id UUID REFERENCES file_categories(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    original_filename VARCHAR(512),
    file_type VARCHAR(50),
    total_length INTEGER DEFAULT 0,
    total_sections INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workspace_docs_user ON workspace_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_workspace_docs_category ON workspace_documents(category_id);

-- 5. TABELA DOCUMENT_SECTIONS (dziecko workspace_documents)
CREATE TABLE IF NOT EXISTS document_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES workspace_documents(id) ON DELETE CASCADE,
    section_index INTEGER NOT NULL,
    content_text TEXT NOT NULL,
    base_styles JSONB DEFAULT '[]'::jsonb,
    section_metadata JSONB DEFAULT '{}'::jsonb,
    char_start INTEGER DEFAULT 0,
    char_end INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sections_order ON document_sections(document_id, section_index);

-- 6. TABELA DOCUMENT_IMAGES (dziecko workspace_documents)
DROP TABLE IF EXISTS document_images CASCADE;

CREATE TABLE document_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES workspace_documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    image_index INTEGER DEFAULT 0,
    image_path VARCHAR(512) NOT NULL,
    image_type VARCHAR(20) NOT NULL,
    file_size INTEGER DEFAULT 0,
    width INTEGER,
    height INTEGER,
    x_position FLOAT,
    y_position FLOAT,
    alt_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_images_doc_page ON document_images(document_id, page_number);

-- 7. TABELA USER_HIGHLIGHTS (dziecko workspace_documents i document_sections)
CREATE TABLE IF NOT EXISTS user_highlights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES workspace_documents(id) ON DELETE CASCADE,
    section_id UUID NOT NULL REFERENCES document_sections(id) ON DELETE CASCADE,
    start_offset INTEGER NOT NULL,
    end_offset INTEGER NOT NULL,
    color_code VARCHAR(20) NOT NULL,
    annotation_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_highlights_lookup ON user_highlights(section_id);
CREATE INDEX IF NOT EXISTS idx_highlights_color ON user_highlights(document_id, color_code);

-- 8. DODAJ workspace_id DO CONVERSATIONS (jeśli nie istnieje)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'workspace_id'
    ) THEN
        ALTER TABLE conversations
        ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;

        CREATE INDEX idx_conversations_workspace ON conversations(workspace_id);
    END IF;
END $$;

-- =============================================================================
-- GOTOWE! Wszystkie tabele zostały utworzone.
-- =============================================================================

