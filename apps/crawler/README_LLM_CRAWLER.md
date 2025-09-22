# LLM-Based Web Crawler

This document describes the new LLM-based web crawler implementation that uses OpenAI's GPT-4o-mini for intelligent content extraction and deep crawling capabilities.

## Features

### 🤖 LLM-Powered Extraction
- Uses OpenAI GPT-4o-mini for intelligent content extraction
- Extracts comprehensive information including pricing, products, contact info, and more
- Handles unstructured content that traditional CSS/XPath selectors might miss
- Uses `extraction_type="block"` for flexible content extraction

### 🔍 Deep Crawling
- Automatically discovers internal links from crawled pages
- Iteratively crawls pages up to a specified depth
- Respects `max_pages` and `max_depth` limits
- Only crawls same-domain pages (`include_external=false`)

### 📄 Markdown Generation
- Creates markdown files for each crawled page
- Includes front matter with metadata (title, URL, crawl timestamp)
- Saves files in organized directory structure by domain
- Combines regular markdown content with LLM-extracted information

## Usage

### Basic Usage

```python
from apps.crawler.services import crawl_website, CrawlerType

# Use LLM crawler
pages = await crawl_website(
    root_url="https://example.com",
    max_pages=10,
    crawler_type=CrawlerType.LLM,
    max_depth=3
)
```

### API Integration

The crawler can be integrated into the `/injest` endpoint by specifying the crawler type:

```python
# In your API endpoint
pages = await crawl_website(
    root_url=request.url,
    max_pages=request.max_pages,
    crawler_type=CrawlerType.LLM,  # Use LLM crawler
    max_depth=request.max_depth
)
```

## Configuration

### Environment Variables

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Crawler Parameters

- `root_url`: Starting URL for crawling
- `max_pages`: Maximum number of pages to crawl (default: 100)
- `max_depth`: Maximum crawling depth (default: 5)
- `tenant_id`: Optional tenant identifier
- `crawler_type`: Either `CrawlerType.LLM` (default) or `CrawlerType.COMPREHENSIVE`

### LLM Configuration

The LLM crawler uses the following configuration:

```python
LLMConfig(
    provider="openai/gpt-4o-mini",
    api_token=os.getenv('OPENAI_API_KEY')
)

LLMExtractionStrategy(
    extraction_type="block",
    chunk_token_threshold=4000,
    overlap_rate=0.1,
    apply_chunking=True,
    input_format="html",
    temperature=0.1,
    max_tokens=2000
)
```

## Content Extraction

The LLM crawler is specifically designed to extract:

1. **Main Content**: Headlines, paragraphs, articles, sections
2. **Products & Services**: Product names, descriptions, features, benefits
3. **Pricing**: All pricing information, costs, fees, rates, discounts, offers
4. **Contact Info**: Addresses, phone numbers, emails, social media links
5. **Business Info**: Company details, about us, team, mission
6. **FAQ & Help**: Questions, answers, help content, documentation
7. **Reviews & Testimonials**: Customer reviews, ratings, testimonials
8. **Structured Data**: Tables, lists, specifications, technical details
9. **Navigation**: Menu items, breadcrumbs, internal links
10. **Media**: Image descriptions, video content, audio content

## File Structure

```
apps/crawler/
├── llm_crawler.py          # New LLM-based crawler implementation
├── simple_crawl4ai.py      # Original comprehensive crawler
├── services.py             # Updated service layer with crawler selection
├── markdown/               # Generated markdown files
│   └── {domain}/
│       ├── page1.md
│       ├── page2.md
│       └── ...
└── README_LLM_CRAWLER.md   # This documentation
```

## Testing

Run the test script to verify the LLM crawler functionality:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Run the test
python test_llm_crawler.py
```

Or test directly with the crawler module:

```bash
python -m apps.crawler.llm_crawler https://example.com 5 2
```

## Comparison with Comprehensive Crawler

| Feature | LLM Crawler | Comprehensive Crawler |
|---------|-------------|----------------------|
| Extraction Method | AI-powered (GPT-4o-mini) | CSS/XPath selectors |
| Deep Crawling | ✅ Yes | ❌ No |
| Pricing Detection | ✅ Advanced | ⚠️ Limited |
| Unstructured Content | ✅ Excellent | ❌ Poor |
| Speed | ⚠️ Slower (API calls) | ✅ Fast |
| Cost | ⚠️ API costs | ✅ Free |
| Accuracy | ✅ High | ⚠️ Variable |

## Error Handling

The LLM crawler includes comprehensive error handling:

- Falls back to basic crawling if LLM extraction fails
- Handles API rate limits and timeouts
- Logs detailed error information
- Continues crawling even if individual pages fail

## Performance Considerations

- **Token Usage**: Monitor OpenAI API usage with `llm_strategy.show_usage()`
- **Chunking**: Large pages are automatically chunked to stay within token limits
- **Parallel Processing**: Multiple pages can be processed concurrently
- **Caching**: Uses `CacheMode.BYPASS` for fresh content

## Future Enhancements

- Support for other LLM providers (Claude, Gemini, etc.)
- Custom extraction schemas
- Advanced content filtering
- Real-time crawling progress updates
- Integration with vector databases for semantic search
