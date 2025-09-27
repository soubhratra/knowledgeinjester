from .celery import app as celery_app  # noqa

# Initialize LangSmith tracing
import os
from django.conf import settings

# Only initialize LangSmith if the API key is available
if hasattr(settings, 'LANGSMITH_API_KEY') and settings.LANGSMITH_API_KEY:
    try:
        import langsmith
        from langsmith import Client
        
        # Set up LangSmith client
        client = Client(
            api_url=settings.LANGCHAIN_ENDPOINT,
            api_key=settings.LANGSMITH_API_KEY
        )
        
        # Initialize tracing
        langsmith.tracing_v2_enabled = True
        
        print(f"LangSmith tracing initialized for project: {settings.LANGCHAIN_PROJECT}")
    except ImportError:
        print("LangSmith not installed. Install with: pip install langsmith[otel]")
    except Exception as e:
        print(f"Failed to initialize LangSmith: {e}")
else:
    print("LangSmith API key not found. Set LANGCHAIN_API_KEY environment variable.")

__all__ = ("celery_app",)
