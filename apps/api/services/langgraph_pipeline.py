from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

class State(TypedDict):
    question: str
    answer: str | None

def llm_node(state: State) -> State:
    q = state["question"]
    resp = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a concise helpful API."},
            {"role": "user", "content": q},
        ],
        temperature=0.2,
        max_tokens=300,
    )
    answer = resp.choices[0].message.content
    return {"answer": answer, "question": q}

def build_graph():
    g = StateGraph(State)
    g.add_node("llm", llm_node)
    g.set_entry_point("llm")
    g.set_finish_point("llm")
    memory = MemorySaver()
    return g.compile(checkpointer=memory)

graph = build_graph()
