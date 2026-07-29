-- PROJ-20: PDF, EPUB und MOBI als Markdown importieren
-- Erweitert den source_type CHECK um drei neue Dokumenttypen.

ALTER TABLE sources
    DROP CONSTRAINT IF EXISTS sources_source_type_check;

ALTER TABLE sources
    ADD CONSTRAINT sources_source_type_check
    CHECK (source_type IN (
        'text',
        'markdown_file',
        'pdf_file',
        'epub_file',
        'mobi_file'
    ));
