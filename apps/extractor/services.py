"""
HTML to Markdown extraction and normalization services.
"""
from typing import List
from apps.core.types import PageRaw, Doc
from apps.core.logging import get_logger

logger = get_logger(__name__)


def extract_markdown(pages: List[PageRaw]) -> List[Doc]:
    """
    Extract and normalize markdown from raw pages.
    
    Args:
        pages: List of raw page data
        
    Returns:
        List of processed documents
    """
    logger.info(f"Extracting markdown from {len(pages)} pages")
    
    docs = []
    for page in pages:
        try:
            # For now, use the content as markdown
            # In a real implementation, you'd convert HTML to markdown
            doc = Doc(
                content_id=page.content_id,
                url=page.url,
                title=page.title,
                content=page.content,
                markdown=page.content,  # Simplified for now
                metadata=page.metadata
            )
            docs.append(doc)
            
        except Exception as e:
            logger.error(f"Failed to extract markdown from {page.url}: {e}")
            continue
    
    logger.info(f"Successfully extracted {len(docs)} documents")
    return docs


