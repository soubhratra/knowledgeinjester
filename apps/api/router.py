from ninja_extra import NinjaExtraAPI, api_controller, http_get, http_post
from django.conf import settings
from .schemas import AskIn, AskOut, CrawlIn, CrawlOut
from .services.langgraph_pipeline import graph
from apps.crawler.services import crawl_website_sync
import asyncio

api = NinjaExtraAPI(title="KnowledgeInjester API", version="0.1.0")

@api_controller("", tags=["meta"])
class MetaController:
    @http_get("/healthz")
    def healthz(self):
        return {"status": "ok", "env": settings.ENV}

@api_controller("v1", tags=["ask"])
class AskController:
    @http_post("/ask", response=AskOut)
    def ask(self, request,payload: AskIn):
        # For testing, you can use a fixed thread_id.
        # For a real application, you should generate a unique ID per user.
        thread_id = "test_thread_1" 

        # Create the config object with the thread_id
        config = {"configurable": {"thread_id": thread_id}}
        
        # Invoke the graph with both the input and the config
        result = graph.invoke({"question": payload.question}, config=config)
        return AskOut(answer=result["answer"])

@api_controller("v1", tags=["crawl"])
class CrawlController:
    @http_post("/crawl", response=CrawlOut)
    def crawl(self, request, payload: CrawlIn):
        """
        Initiate crawling of a website.
        Takes a URL and optional max_pages parameter.
        """
        try:
            # Convert HttpUrl to string for the crawler
            url_str = str(payload.url)
            max_pages = payload.max_pages or 100
            
            # Run the crawler service
            pages = crawl_website_sync(url_str, max_pages)
            
            return CrawlOut(
                message=f"Successfully crawled {url_str}",
                urls_discovered=len(pages),
                pages_crawled=len(pages)
            )
        except Exception as e:
            return CrawlOut(
                message=f"Error crawling {payload.url}: {str(e)}",
                urls_discovered=0,
                pages_crawled=0
            )

api.register_controllers(MetaController, AskController, CrawlController)
