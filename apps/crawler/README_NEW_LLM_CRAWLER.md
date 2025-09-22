# New LLM Crawler Implementation

This is a fresh and clean implementation of the LLM crawler using Crawl4AI's deep crawling capabilities and LLM extraction strategies.

## Features

### 🚀 Deep Crawling
- **BFSDeepCrawlStrategy**: Breadth-first search for comprehensive coverage
- **BestFirstCrawlingStrategy**: Intelligent prioritization based on content relevance
- **Configurable depth and page limits**: Control crawl scope with `max_depth` and `max_pages`
- **Internal links only**: Set `include_external=False` to stay within the same domain

### 🤖 LLM-Powered Extraction
- **Comprehensive content extraction**: Extracts structured information from web pages
- **Multiple content categories**: Products, pricing, contact info, business details, etc.
- **Intelligent chunking**: Handles large pages with smart content chunking
- **Structured output**: Returns well-organized extracted information

### 📁 Markdown Generation
- **Automatic markdown files**: Saves each crawled page as a markdown file
- **Front matter metadata**: Includes title, URL, and crawl timestamp
- **Organized storage**: Creates domain-based folder structure
- **Unique filenames**: Prevents conflicts with smart naming

### ⚡ Performance Features
- **Error resilience**: Graceful handling of failed pages
- **Resource management**: Proper cleanup and timeout handling
- **Efficient crawling**: Optimized for reliable single-pass crawling

## Usage

### Basic Usage

```python
from apps.crawler.llm_crawler import crawl_with_llm_deep_crawling

# Simple crawl
pages = await crawl_with_llm_deep_crawling(
    root_url="https://example.com",
    max_pages=10,
    max_depth=2
)
```

### Advanced Usage

```python
# With custom strategy
pages = await crawl_with_llm_deep_crawling(
    root_url="https://example.com",
    max_pages=50,
    max_depth=3,
    tenant_id="tenant_123",
    strategy_type="best_first"  # or "bfs"
)
```

### Command Line Usage

```bash
# Basic crawl
python -m apps.crawler.llm_crawler https://example.com

# With custom parameters
python -m apps.crawler.llm_crawler https://example.com 20 3 best_first
```

## Configuration

### Environment Variables

```bash
# Required
export OPENAI_API_KEY="your-openai-api-key"

# Optional
export CRAWL4AI_VERBOSE="true"
```

### Strategy Types

1. **BFS (Breadth-First Search)**
   - Explores all links at one depth before moving deeper
   - Good for comprehensive coverage
   - Predictable crawl order

2. **BestFirst (Intelligent Prioritization)**
   - Uses keyword relevance scoring
   - Prioritizes most relevant pages first
   - Better for focused content extraction

### Deep Crawling Parameters

- `max_depth`: Maximum levels to crawl beyond the starting page
- `max_pages`: Maximum total pages to crawl
- `include_external`: Whether to follow external links (default: False)

## LLM Extraction Strategy

The crawler uses a comprehensive LLM extraction strategy that focuses on:

1. **Main Content**: Headlines, paragraphs, articles, sections
2. **Products & Services**: Product names, descriptions, features, benefits
3. **Pricing**: All pricing information, costs, fees, rates, discounts
4. **Contact Info**: Addresses, phone numbers, emails, social media
5. **Business Info**: Company details, about us, team, mission
6. **FAQ & Help**: Questions, answers, help content, documentation
7. **Reviews & Testimonials**: Customer reviews, ratings, testimonials
8. **Structured Data**: Tables, lists, specifications, technical details
9. **Navigation**: Menu items, breadcrumbs, internal links
10. **Media**: Image descriptions, video content, audio content

## Output Format

### PageRaw Objects

Each crawled page is returned as a `PageRaw` object with:

```python
{
    "content_id": "unique_identifier",
    "url": "https://example.com/page",
    "title": "Page Title",
    "content": "Markdown content + AI extracted information",
    "metadata": {
        "crawled_at": "2024-01-01T00:00:00Z",
        "word_count": 1500,
        "source": "llm_crawler",
        "extraction_method": "llm_block_extraction",
        "llm_extracted_content": "Structured extracted information",
        "tenant_id": "optional_tenant_id",
        "depth": 1,
        "score": 0.85
    }
}
```

### Markdown Files

Each page is also saved as a markdown file with front matter:

```markdown
---
title: "Page Title"
url: "https://example.com/page"
crawled_at: "2024-01-01T00:00:00Z"
---

# Page Content

[Markdown content here]

## AI-Extracted Information

[Structured extracted information here]
```

## Error Handling

The crawler includes comprehensive error handling:

- **Graceful failures**: Individual page failures don't stop the entire crawl
- **Fallback strategies**: Multiple configuration attempts for difficult pages
- **Detailed logging**: Comprehensive logging for debugging
- **Resource cleanup**: Proper cleanup of browser resources

## Performance Considerations

- **Page limits**: Set reasonable `max_pages` to control resource usage
- **Depth limits**: Keep `max_depth` reasonable (2-3 levels typically sufficient)
- **Timeout settings**: Configured for reliable crawling without excessive delays
- **Memory usage**: Single-pass crawling for efficient memory usage

## Testing

Run the test script to verify the implementation:

```bash
python test_new_llm_crawler.py
```

## Dependencies

- `crawl4ai`: Web crawling and extraction
- `openai`: LLM integration
- `asyncio`: Asynchronous processing
- `pathlib`: File system operations

## Best Practices

1. **Set realistic limits**: Don't set `max_depth` too high (exponential growth)
2. **Use appropriate strategy**: BFS for coverage, BestFirst for relevance
3. **Monitor resource usage**: Watch memory and CPU usage during large crawls
4. **Respect robots.txt**: The crawler respects website crawling policies
5. **Handle errors gracefully**: Check for failed pages in results

## Integration

The crawler integrates seamlessly with the existing knowledge injester pipeline:

- **PageRaw objects**: Compatible with existing vectorization pipeline
- **Markdown files**: Ready for further processing and indexing
- **Metadata**: Includes all necessary information for downstream processing
- **Tenant support**: Multi-tenant architecture support
