from typing import List, Dict, Any, Tuple
from django.db import connection
from django.conf import settings

EMBED_DIM = getattr(settings, "EMBEDDING_DIM", 1536)
TOP_K = getattr(settings, "RETRIEVAL_TOP_K", 6)

def cleanup_old_data_for_urls(tenant_id: str, urls: List[str]) -> Tuple[int, int]:
    """
    Clean up old documents and chunks for the given URLs before inserting new data.
    This implements replacive ingestion by removing old data first.
    
    Args:
        tenant_id: Tenant identifier
        urls: List of URLs to clean up
        
    Returns:
        Tuple of (deleted_documents_count, deleted_chunks_count)
    """
    if not urls:
        return 0, 0
        
    with connection.cursor() as cur:
        # First, get document IDs for the URLs
        placeholders = ','.join(['%s'] * len(urls))
        cur.execute(f"""
            SELECT id FROM vectorizer_document 
            WHERE tenant_id = %s AND source_url IN ({placeholders})
        """, [tenant_id] + urls)
        doc_ids = [row[0] for row in cur.fetchall()]
        
        if not doc_ids:
            return 0, 0
            
        # Delete chunks first (due to foreign key constraint)
        chunk_placeholders = ','.join(['%s'] * len(doc_ids))
        cur.execute(f"""
            DELETE FROM vectorizer_chunk 
            WHERE tenant_id = %s AND document_id IN ({chunk_placeholders})
        """, [tenant_id] + doc_ids)
        deleted_chunks = cur.rowcount
        
        # Delete documents
        cur.execute(f"""
            DELETE FROM vectorizer_document 
            WHERE tenant_id = %s AND id IN ({chunk_placeholders})
        """, [tenant_id] + doc_ids)
        deleted_docs = cur.rowcount
        
        # Don't commit in test environment to avoid transaction conflicts
        if not getattr(settings, 'TESTING', False):
            connection.commit()
            
        return deleted_docs, deleted_chunks

def upsert_chunks(tenant_id: str, chunks: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Insert Document/Chunk rows with replacive ingestion.
    First cleans up old data for the same URLs, then inserts new data.
    All operations happen in a single transaction.
    """
    if not chunks:
        return 0, 0
        
    # Extract unique URLs from chunks
    urls = list(set([c["url"] for c in chunks]))
    
    # Use transaction.atomic to ensure proper transaction handling
    from django.db import transaction
    
    with transaction.atomic():
        with connection.cursor() as cur:
            # Clean up old data for these URLs first (replacive ingestion)
            if urls:
                placeholders = ','.join(['%s'] * len(urls))
                cur.execute(f"""
                    SELECT id FROM vectorizer_document 
                    WHERE tenant_id = %s AND source_url IN ({placeholders})
                """, [tenant_id] + urls)
                doc_ids = [row[0] for row in cur.fetchall()]
                
                if doc_ids:
                    # Delete chunks first (due to foreign key constraint)
                    chunk_placeholders = ','.join(['%s'] * len(doc_ids))
                    cur.execute(f"""
                        DELETE FROM vectorizer_chunk 
                        WHERE tenant_id = %s AND document_id IN ({chunk_placeholders})
                    """, [tenant_id] + doc_ids)
                    deleted_chunks = cur.rowcount
                    
                    # Delete documents
                    cur.execute(f"""
                        DELETE FROM vectorizer_document 
                        WHERE tenant_id = %s AND id IN ({chunk_placeholders})
                    """, [tenant_id] + doc_ids)
                    deleted_docs = cur.rowcount
                    
                    print(f"DEBUG: Cleaned up {deleted_docs} old documents and {deleted_chunks} old chunks for replacive ingestion")
            
            # Insert documents first using upsert (INSERT ... ON CONFLICT)
            doc_map = {}  # url -> id
            for c in chunks:
                url = c["url"]; title = c.get("title")
                # doc hash is hash of full page title+all chunks for that url
                cur.execute("""
                    INSERT INTO vectorizer_document (tenant_id, source_url, doc_hash, title, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (tenant_id, doc_hash) 
                    DO UPDATE SET 
                        source_url = EXCLUDED.source_url,
                        title = EXCLUDED.title,
                        created_at = NOW()
                    RETURNING id
                """, [tenant_id, url, c.get("doc_hash",""), title])
                row = cur.fetchone()
                if row:
                    doc_map[url] = row[0]

            # Insert chunks
            for c in chunks:
                import json
                cur.execute("""
                INSERT INTO vectorizer_chunk (tenant_id, document_id, ordinal, text, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING id
                """, [tenant_id, doc_map[c["url"]], c["ordinal"], c["text"], json.dumps(c.get("metadata", {}))])

    # Return counts of new data inserted
    return (len(set([c["url"] for c in chunks])), len(chunks))

def write_embeddings(tenant_id: str, chunk_ids: List[int], vectors: List[List[float]]):
    # Batched update
    with connection.cursor() as cur:
        for cid, vec in zip(chunk_ids, vectors):
            cur.execute("UPDATE vectorizer_chunk SET embedding=%s WHERE id=%s AND tenant_id=%s", [vec, cid, tenant_id])
        # Don't commit in test environment to avoid transaction conflicts
        if not getattr(settings, 'TESTING', False):
            connection.commit()

def get_tenant_stats(tenant_id: str) -> Dict[str, int]:
    """
    Get statistics for a tenant's data.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Dictionary with document count, chunk count, and total size
    """
    with connection.cursor() as cur:
        # Count documents
        cur.execute("SELECT COUNT(*) FROM vectorizer_document WHERE tenant_id = %s", [tenant_id])
        doc_count = cur.fetchone()[0]
        
        # Count chunks
        cur.execute("SELECT COUNT(*) FROM vectorizer_chunk WHERE tenant_id = %s", [tenant_id])
        chunk_count = cur.fetchone()[0]
        
        # Get total size (approximate)
        cur.execute("""
            SELECT 
                pg_size_pretty(pg_total_relation_size('vectorizer_document') + pg_total_relation_size('vectorizer_chunk')) as total_size,
                pg_total_relation_size('vectorizer_document') + pg_total_relation_size('vectorizer_chunk') as total_bytes
            FROM vectorizer_document 
            WHERE tenant_id = %s 
            LIMIT 1
        """, [tenant_id])
        size_result = cur.fetchone()
        total_size = size_result[0] if size_result else "0 bytes"
        total_bytes = size_result[1] if size_result else 0
        
        return {
            "documents": doc_count,
            "chunks": chunk_count,
            "total_size": total_size,
            "total_bytes": total_bytes
        }

def cleanup_tenant_data(tenant_id: str) -> Tuple[int, int]:
    """
    Clean up all data for a specific tenant.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Tuple of (deleted_documents_count, deleted_chunks_count)
    """
    with connection.cursor() as cur:
        # Delete chunks first
        cur.execute("""
            DELETE FROM vectorizer_chunk 
            WHERE tenant_id = %s
        """, [tenant_id])
        deleted_chunks = cur.rowcount
        
        # Delete documents
        cur.execute("""
            DELETE FROM vectorizer_document 
            WHERE tenant_id = %s
        """, [tenant_id])
        deleted_docs = cur.rowcount
        
        if not getattr(settings, 'TESTING', False):
            connection.commit()
            
        return deleted_docs, deleted_chunks

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
