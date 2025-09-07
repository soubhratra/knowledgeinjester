import os
from typing import List
from openai import OpenAI
from django.conf import settings


_client = OpenAI(api_key=settings.OPENAI_API_KEY)
_MODEL = settings.EMBEDDING_MODEL

def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts: return []
    resp = _client.embeddings.create(model=_MODEL, input=texts)
    return [d.embedding for d in resp.data]
