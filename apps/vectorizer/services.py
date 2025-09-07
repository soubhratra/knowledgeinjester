from typing import List, Tuple
from apps.core.hashing import sha256_str
from apps.core.types import Doc
from .chunker import chunk_docs
from .embedder import embed_texts
from .supabase_store import upsert_chunks, write_embeddings

def vectorize_docs(tenant_id: str, docs: List[Doc]) -> Tuple[int,int]:
    # chunk
    chunks = []
    # group docs by URL to create a stable doc hash per doc
    for d in docs:
        chs = chunk_docs([d])
        full_str = (d.title or "") + "\n".join([c["text"] for c in chs])
        dhash = sha256_str(full_str)
        for c in chs:
            c["doc_hash"] = dhash
        chunks.extend(chs)

    docs_count, chunks_count = upsert_chunks(tenant_id, chunks)

    # fetch inserted chunk ids for embeddings
    # simplest approach: re-select by (tenant_id, doc_hash)
    from django.db import connection
    chunk_texts = []
    chunk_ids = []
    with connection.cursor() as cur:
        doc_hashes = tuple({c["doc_hash"] for c in chunks})
        if doc_hashes:
            placeholders = ','.join(['%s'] * len(doc_hashes))
            cur.execute(f"""
              SELECT c.id, c.text FROM vectorizer_chunk c
              JOIN vectorizer_document d ON d.id = c.document_id
              WHERE c.tenant_id=%s AND d.doc_hash IN ({placeholders})
              ORDER BY c.id ASC
            """, [tenant_id] + list(doc_hashes))
            for row in cur.fetchall():
                chunk_ids.append(row[0]); chunk_texts.append(row[1])
        # If no chunks, chunk_ids and chunk_texts remain empty lists

    vectors = embed_texts(chunk_texts)
    write_embeddings(tenant_id, chunk_ids, vectors)
    return docs_count, len(chunk_ids)