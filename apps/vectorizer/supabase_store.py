from typing import List, Dict, Any, Tuple
from django.db import connection
from django.conf import settings

EMBED_DIM = getattr(settings, "EMBEDDING_DIM", 1536)
TOP_K = getattr(settings, "RETRIEVAL_TOP_K", 6)

def upsert_chunks(tenant_id: str, chunks: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Insert Document/Chunk rows; dedupe by doc_hash+url on Document."""
    with connection.cursor() as cur:
        # Insert documents first
        doc_map = {}  # url -> id
        for c in chunks:
            url = c["url"]; title = c.get("title")
            # doc hash is hash of full page title+all chunks for that url; here we accept per-chunk insert and compute later
            cur.execute("""
                INSERT INTO vectorizer_document (tenant_id, source_url, doc_hash, title, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (tenant_id, doc_hash) DO NOTHING
                RETURNING id
            """, [tenant_id, url, c.get("doc_hash",""), title])
            row = cur.fetchone()
            if row:
                doc_map[url] = row[0]
            else:
                # fetch existing
                cur.execute("SELECT id FROM vectorizer_document WHERE tenant_id=%s AND source_url=%s ORDER BY id DESC LIMIT 1",
                            [tenant_id, url])
                ex = cur.fetchone()
                if ex: doc_map[url] = ex[0]

        # Insert chunks
        for c in chunks:
            import json
            cur.execute("""
            INSERT INTO vectorizer_chunk (tenant_id, document_id, ordinal, text, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
            """, [tenant_id, doc_map[c["url"]], c["ordinal"], c["text"], json.dumps(c.get("metadata", {}))])
        # Don't commit in test environment to avoid transaction conflicts
        if not getattr(settings, 'TESTING', False):
            connection.commit()

    # Return rough counts
    return (len(set([c["url"] for c in chunks])), len(chunks))

def write_embeddings(tenant_id: str, chunk_ids: List[int], vectors: List[List[float]]):
    # Batched update
    with connection.cursor() as cur:
        for cid, vec in zip(chunk_ids, vectors):
            cur.execute("UPDATE vectorizer_chunk SET embedding=%s WHERE id=%s AND tenant_id=%s", [vec, cid, tenant_id])
        # Don't commit in test environment to avoid transaction conflicts
        if not getattr(settings, 'TESTING', False):
            connection.commit()

def hybrid_search(tenant_id: str, query: str, query_vec: List[float], top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """
    Score = 0.65 * (1 - cosine_distance) + 0.35 * ts_rank_cd
    Filter by tenant_id and a minimal similarity threshold if desired.
    """
    print(f"DEBUG: hybrid_search called with tenant_id='{tenant_id}', query='{query}', top_k={top_k}")
    
    with connection.cursor() as cur:
        # First, let's check if there are any chunks for this tenant
        cur.execute("SELECT COUNT(*) FROM vectorizer_chunk WHERE tenant_id = %s", [tenant_id])
        chunk_count = cur.fetchone()[0]
        print(f"DEBUG: Found {chunk_count} chunks for tenant_id='{tenant_id}'")
        
        if chunk_count == 0:
            print(f"DEBUG: No chunks found for tenant_id='{tenant_id}', returning empty list")
            return []
        
        # Also check documents
        cur.execute("SELECT COUNT(*) FROM vectorizer_document WHERE tenant_id = %s", [tenant_id])
        doc_count = cur.fetchone()[0]
        print(f"DEBUG: Found {doc_count} documents for tenant_id='{tenant_id}'")
        
        cur.execute("""
        WITH scored AS (
          SELECT
            c.id, c.text, c.metadata, d.source_url, d.title,
            1 - (c.embedding <=> %s::vector) AS sim,
            ts_rank_cd(c.ts, websearch_to_tsquery('english', %s)) AS fts_rank
          FROM vectorizer_chunk c
          JOIN vectorizer_document d ON d.id = c.document_id
          WHERE c.tenant_id = %s
        )
        SELECT id, text, metadata, source_url, title, sim, fts_rank,
               (0.65*sim + 0.35*fts_rank) AS score
        FROM scored
        ORDER BY score DESC
        LIMIT %s
        """, [query_vec, query, tenant_id, top_k])
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        print(f"DEBUG: hybrid_search returning {len(rows)} results")
        return rows
