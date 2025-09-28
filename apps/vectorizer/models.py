from django.db import models
from django.conf import settings

EMBED_DIM = getattr(settings, "EMBEDDING_DIM", 1536)

class Document(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.CharField(max_length=64, db_index=True)
    source_url = models.TextField()
    doc_hash = models.CharField(max_length=64, db_index=True)  # sha256 of normalized content
    title = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vectorizer_document'
        unique_together = ['tenant_id', 'doc_hash']

class Chunk(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.CharField(max_length=64, db_index=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    ordinal = models.IntegerField()
    text = models.TextField()
    # vector + FTS (managed by migrations with custom SQL for types/indexes)
    embedding = models.BinaryField(null=True, blank=True)   # placeholder for Django; real type set in SQL
    ts = models.TextField(null=True, blank=True)            # placeholder; real tsvector set in SQL
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vectorizer_chunk'
        indexes = [
            models.Index(fields=["tenant_id", "document", "ordinal"]),
        ]
