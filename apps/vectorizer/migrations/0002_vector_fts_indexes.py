from django.db import migrations
from django.conf import settings

EMBED_DIM = getattr(settings, "EMBEDDING_DIM", 1536)

CREATE_EXTENSIONS = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
"""

POST_CREATE = f"""
-- Convert placeholder columns to proper types
ALTER TABLE vectorizer_chunk
  ALTER COLUMN embedding TYPE vector({EMBED_DIM}) USING NULL,
  ALTER COLUMN ts TYPE tsvector USING NULL;

-- HNSW index for cosine similarity
CREATE INDEX IF NOT EXISTS idx_chunk_embedding_hnsw
  ON vectorizer_chunk USING hnsw (embedding vector_cosine_ops);

-- FTS index
CREATE INDEX IF NOT EXISTS idx_chunk_fts
  ON vectorizer_chunk USING GIN (ts);

-- Keep FTS column updated
CREATE OR REPLACE FUNCTION vectorizer_chunk_tsv_update() RETURNS trigger AS $$
BEGIN
  NEW.ts := to_tsvector('english', unaccent(coalesce(NEW.text,'')));
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_chunk_tsv_update ON vectorizer_chunk;
CREATE TRIGGER trg_chunk_tsv_update
  BEFORE INSERT OR UPDATE OF text
  ON vectorizer_chunk FOR EACH ROW
  EXECUTE PROCEDURE vectorizer_chunk_tsv_update();
"""

class Migration(migrations.Migration):

    dependencies = [
        ("vectorizer", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(CREATE_EXTENSIONS),
        migrations.RunSQL(POST_CREATE),
    ]
