from django.core.management.base import BaseCommand
from apps.pipelines.langgraph.graph import build_graph
from apps.pipelines.schemas import PipelineState

class Command(BaseCommand):
    help = "Run crawl→extract→vectorize"

    def add_arguments(self, parser):
        parser.add_argument("--tenant", required=True)
        parser.add_argument("--url", required=True)
        parser.add_argument("--max_pages", type=int, default=200)

    def handle(self, *args, **opts):
        g = build_graph()
        final_state = g.invoke(PipelineState(tenant_id=opts["tenant"], root_url=opts["url"], max_pages=opts["max_pages"]))
        # LangGraph returns state as a dictionary, not a PipelineState object
        if isinstance(final_state, dict):
            out = final_state.get("result") or final_state.get("vectorization_summary") or {}
        else:
            out = final_state.result or final_state.vectorization_summary or {}
        self.stdout.write(self.style.SUCCESS(str(out)))

