"""
Sample data fixtures for testing.
"""
from apps.core.types import PageRaw, Doc, Chunk, Embedding


def get_sample_page_raw() -> PageRaw:
    """Get a sample PageRaw object."""
    return PageRaw(
        url="https://example.com",
        title="Example Page",
        content="This is example content for testing purposes.",
        html="<html><body><h1>Example Page</h1><p>This is example content for testing purposes.</p></body></html>",
        metadata={
            "status": 200,
            "content_type": "text/html",
            "content_length": 1000,
            "crawled_at": "2024-01-01T00:00:00Z"
        }
    )


def get_sample_doc() -> Doc:
    """Get a sample Doc object."""
    return Doc(
        content_id="doc-123",
        url="https://example.com",
        title="Example Page",
        content="This is example content for testing purposes.",
        markdown="# Example Page\n\nThis is example content for testing purposes.",
        metadata={
            "status": 200,
            "content_type": "text/html",
            "word_count": 10,
            "processed_at": "2024-01-01T00:00:00Z"
        }
    )


def get_sample_chunk() -> Chunk:
    """Get a sample Chunk object."""
    return Chunk(
        chunk_id="chunk-123",
        content_id="doc-123",
        content="This is a test chunk for vectorization.",
        chunk_index=0,
        total_chunks=3,
        metadata={
            "source": "test",
            "chunk_type": "paragraph"
        }
    )


def get_sample_embedding() -> Embedding:
    """Get a sample Embedding object."""
    return Embedding(
        chunk_id="chunk-123",
        content_id="doc-123",
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5] * 20,  # 100-dimensional vector
        model="text-embedding-ada-002"
    )


def get_sample_pages() -> list[PageRaw]:
    """Get multiple sample PageRaw objects."""
    return [
        PageRaw(
            url="https://example.com",
            title="Home Page",
            content="Welcome to our website.",
            metadata={"status": 200}
        ),
        PageRaw(
            url="https://example.com/about",
            title="About Us",
            content="Learn more about our company.",
            metadata={"status": 200}
        ),
        PageRaw(
            url="https://example.com/contact",
            title="Contact",
            content="Get in touch with us.",
            metadata={"status": 200}
        )
    ]


def get_sample_docs() -> list[Doc]:
    """Get multiple sample Doc objects."""
    return [
        Doc(
            content_id="doc-1",
            url="https://example.com",
            title="Home Page",
            content="Welcome to our website.",
            markdown="# Home Page\n\nWelcome to our website."
        ),
        Doc(
            content_id="doc-2",
            url="https://example.com/about",
            title="About Us",
            content="Learn more about our company.",
            markdown="# About Us\n\nLearn more about our company."
        )
    ]


