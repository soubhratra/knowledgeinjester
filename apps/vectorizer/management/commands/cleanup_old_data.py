"""
Management command to clean up old vectorizer data.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = "Clean up old vectorizer documents and chunks"

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='Clean up data for specific tenant (default: all tenants)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Clean up data older than N days (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--urls',
            type=str,
            nargs='+',
            help='Clean up specific URLs'
        )

    def handle(self, *args, **options):
        tenant_id = options.get('tenant_id')
        days = options.get('days', 30)
        dry_run = options.get('dry_run', False)
        urls = options.get('urls')

        if urls:
            self.cleanup_specific_urls(tenant_id, urls, dry_run)
        else:
            self.cleanup_old_data(tenant_id, days, dry_run)

    def cleanup_specific_urls(self, tenant_id, urls, dry_run):
        """Clean up data for specific URLs."""
        self.stdout.write(f"Cleaning up data for URLs: {urls}")
        
        with connection.cursor() as cur:
            # Build WHERE clause
            where_clauses = []
            params = []
            
            if tenant_id:
                where_clauses.append("tenant_id = %s")
                params.append(tenant_id)
            
            placeholders = ','.join(['%s'] * len(urls))
            where_clauses.append(f"source_url IN ({placeholders})")
            params.extend(urls)
            
            where_sql = " AND ".join(where_clauses)
            
            # Count documents to be deleted
            cur.execute(f"""
                SELECT COUNT(*) FROM vectorizer_document 
                WHERE {where_sql}
            """, params)
            doc_count = cur.fetchone()[0]
            
            # Count chunks to be deleted
            cur.execute(f"""
                SELECT COUNT(*) FROM vectorizer_chunk c
                JOIN vectorizer_document d ON d.id = c.document_id
                WHERE {where_sql}
            """, params)
            chunk_count = cur.fetchone()[0]
            
            self.stdout.write(f"Would delete {doc_count} documents and {chunk_count} chunks")
            
            if not dry_run and (doc_count > 0 or chunk_count > 0):
                # Delete chunks first
                cur.execute(f"""
                    DELETE FROM vectorizer_chunk 
                    WHERE document_id IN (
                        SELECT id FROM vectorizer_document WHERE {where_sql}
                    )
                """, params)
                deleted_chunks = cur.rowcount
                
                # Delete documents
                cur.execute(f"""
                    DELETE FROM vectorizer_document 
                    WHERE {where_sql}
                """, params)
                deleted_docs = cur.rowcount
                
                if not getattr(settings, 'TESTING', False):
                    connection.commit()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Deleted {deleted_docs} documents and {deleted_chunks} chunks"
                    )
                )
            elif dry_run:
                self.stdout.write("Dry run - no data deleted")

    def cleanup_old_data(self, tenant_id, days, dry_run):
        """Clean up data older than specified days."""
        self.stdout.write(f"Cleaning up data older than {days} days")
        
        with connection.cursor() as cur:
            # Build WHERE clause
            where_clauses = ["created_at < NOW() - INTERVAL '%s days'"]
            params = [days]
            
            if tenant_id:
                where_clauses.append("tenant_id = %s")
                params.append(tenant_id)
            
            where_sql = " AND ".join(where_clauses)
            
            # Count documents to be deleted
            cur.execute(f"""
                SELECT COUNT(*) FROM vectorizer_document 
                WHERE {where_sql}
            """, params)
            doc_count = cur.fetchone()[0]
            
            # Count chunks to be deleted
            cur.execute(f"""
                SELECT COUNT(*) FROM vectorizer_chunk c
                JOIN vectorizer_document d ON d.id = c.document_id
                WHERE {where_sql}
            """, params)
            chunk_count = cur.fetchone()[0]
            
            self.stdout.write(f"Would delete {doc_count} documents and {chunk_count} chunks")
            
            if not dry_run and (doc_count > 0 or chunk_count > 0):
                # Delete chunks first
                cur.execute(f"""
                    DELETE FROM vectorizer_chunk 
                    WHERE document_id IN (
                        SELECT id FROM vectorizer_document WHERE {where_sql}
                    )
                """, params)
                deleted_chunks = cur.rowcount
                
                # Delete documents
                cur.execute(f"""
                    DELETE FROM vectorizer_document 
                    WHERE {where_sql}
                """, params)
                deleted_docs = cur.rowcount
                
                if not getattr(settings, 'TESTING', False):
                    connection.commit()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Deleted {deleted_docs} documents and {deleted_chunks} chunks"
                    )
                )
            elif dry_run:
                self.stdout.write("Dry run - no data deleted")
