from celery import shared_task
from apps.pipelines.langgraph.graph import build_graph
from apps.pipelines.schemas import PipelineState

@shared_task
def ingest_task(tenant_id: str, root_url: str, max_pages: int = 200):
    graph = build_graph()
    state = PipelineState(tenant_id=tenant_id, root_url=root_url, max_pages=max_pages)
    final_state = graph.invoke(state)
    # LangGraph returns state as a dictionary, not a PipelineState object
    if isinstance(final_state, dict):
        result = final_state.get("result") or final_state.get("vectorization_summary") or {}
    else:
        result = final_state.result or final_state.vectorization_summary or {}
    return result
