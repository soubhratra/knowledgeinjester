from langgraph.graph import StateGraph, END
from apps.pipelines.schemas import PipelineState
from .nodes import crawl_node, extract_node, vectorize_node

def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("crawl", crawl_node)
    g.add_node("extract", extract_node)
    g.add_node("vectorize", vectorize_node)
    g.set_entry_point("crawl")
    g.add_edge("crawl", "extract")
    g.add_edge("extract", "vectorize")
    g.add_edge("vectorize", END)
    return g.compile()

