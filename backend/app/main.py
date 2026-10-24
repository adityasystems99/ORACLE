"""FastAPI Main Application Entrypoint for ORACLE."""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api.routes_copilot import router as copilot_router
from .api.routes_events import router as events_router
from .api.routes_graph import router as graph_router
from .api.routes_impact import router as impact_router
from .api.routes_ingest import router as ingest_router
from .api.routes_rag import router as rag_router
from .api.routes_rules import router as rules_router
from .api.routes_scheduler import router as scheduler_router
from .api.routes_system import router as system_router
from .change_detection.detector import ChangeDetector
from .config import get_settings
from .copilot.service import CopilotService
from .scheduler.engine import ScheduledMonitoringEngine
from .graph.store import KnowledgeGraphStore
from .impact.analyzer import ImpactAnalyzer
from .impact.investigation_service import InvestigationService
from .ingestion.engine import IngestionEngine
from .llm.factory import get_llm_adapter
from .retrieval.rag_pipeline import RAGPipeline
from .retrieval.temporal_graph_rag import TemporalGraphRAGEngine
from .retrieval.vector_store import VectorStore
from .storage.disk_store import DiskStore

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("oracle")


def init_app_state(app: FastAPI) -> None:
    """Initialize state singletons eagerly so they are immediately available."""
    if hasattr(app.state, "disk_store") and app.state.disk_store is not None:
        return
    settings = get_settings()
    disk_store = DiskStore(settings.DATA_DIR)
    graph_store = KnowledgeGraphStore(persist_path=settings.GRAPH_PERSIST_PATH)
    vector_store = VectorStore(persist_dir=settings.CHROMA_PERSIST_DIR)
    llm_adapter = get_llm_adapter()
    ingestion_engine = IngestionEngine(disk_store=disk_store)
    change_detector = ChangeDetector(disk_store=disk_store)
    impact_analyzer = ImpactAnalyzer(
        graph_store=graph_store,
        vector_store=vector_store,
        disk_store=disk_store,
        llm_adapter=llm_adapter,
    )
    rag_pipeline = RAGPipeline(
        disk_store=disk_store,
        vector_store=vector_store,
    )
    temporal_graph_rag = TemporalGraphRAGEngine(
        graph_store=graph_store,
        rag_pipeline=rag_pipeline,
    )
    investigation_service = InvestigationService(
        graph_store=graph_store,
        rag_pipeline=rag_pipeline,
    )
    copilot_service = CopilotService(
        disk_store=disk_store,
        rag_pipeline=rag_pipeline,
        graph_store=graph_store,
        investigation_service=investigation_service,
        llm_adapter=llm_adapter,
    )
    scheduler_engine = ScheduledMonitoringEngine(
        disk_store=disk_store,
        ingestion_engine=ingestion_engine,
        rag_pipeline=rag_pipeline,
        change_detector=change_detector,
        investigation_service=investigation_service,
    )

    app.state.disk_store = disk_store
    app.state.graph_store = graph_store
    app.state.vector_store = vector_store
    app.state.llm_adapter = llm_adapter
    app.state.ingestion_engine = ingestion_engine
    app.state.change_detector = change_detector
    app.state.impact_analyzer = impact_analyzer
    app.state.rag_pipeline = rag_pipeline
    app.state.temporal_graph_rag = temporal_graph_rag
    app.state.investigation_service = investigation_service
    app.state.copilot_service = copilot_service
    app.state.scheduler_engine = scheduler_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager initializing singletons and background resources."""
    settings = get_settings()
    logger.info(f"Initializing {settings.APP_NAME} in {settings.APP_ENV} mode...")
    init_app_state(app)
    if settings.SCHEDULER_ENABLED and hasattr(app.state, "scheduler_engine") and app.state.scheduler_engine:
        app.state.scheduler_engine.start(tick_seconds=settings.SCHEDULER_TICK_SECONDS)
    logger.info(f"{settings.APP_NAME} initialization complete. Ready to serve requests.")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")
    if hasattr(app.state, "scheduler_engine") and app.state.scheduler_engine:
        app.state.scheduler_engine.stop()


def create_app() -> FastAPI:
    """Application factory for ORACLE."""
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.APP_NAME} — Live Intelligence Copilot",
        description="Continuously monitors public technology information, detects changes, reasons over temporal knowledge graphs, and synthesizes evidence-backed impact reports.",
        version="0.1.0",
        lifespan=lifespan,
    )
    init_app_state(app)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception processing {request.method} {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred.", "error": str(exc)},
        )

    # Register API Routers
    app.include_router(ingest_router)
    app.include_router(rag_router)
    app.include_router(events_router)
    app.include_router(graph_router)
    app.include_router(impact_router)
    app.include_router(copilot_router, prefix="/api/copilot")
    app.include_router(copilot_router, prefix="/copilot")
    app.include_router(rules_router, prefix="/api")
    app.include_router(rules_router, prefix="")
    app.include_router(scheduler_router, prefix="/api")
    app.include_router(scheduler_router, prefix="")
    app.include_router(system_router)

    @app.get("/health")
    def health_check():
        return {"status": "healthy", "app": settings.APP_NAME}

    @app.get("/api/sources")
    def get_sources_alias(request: Request):
        raw_sources = request.app.state.ingestion_engine.get_sources()
        return [
            {
                "id": s.id,
                "name": s.name,
                "type": s.source_type.value if hasattr(s.source_type, "value") else str(s.source_type),
                "status": "healthy" if (s.last_status in ["healthy", "success", "initialized"] or not s.last_status) else s.last_status,
                "last": s.last_synced_at.isoformat() if s.last_synced_at else None,
                "items": 0,
            }
            for s in raw_sources
        ]

    @app.get("/api/signals")
    def get_signals_alias(request: Request):
        from .schemas.event import IntelligenceEvent
        events = request.app.state.disk_store.load_all("events", IntelligenceEvent)
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return [
            {
                "id": e.id,
                "title": e.title,
                "severity": e.severity.value,
                "category": e.category.value,
                "source": e.evidence[0].source_type if e.evidence else "Unknown",
                "published_at": e.timestamp.isoformat(),
                "summary": e.summary,
                "tech": e.primary_technology,
                "evidence": len(e.evidence),
                "demo": False,
            }
            for e in events
        ]

    @app.get("/api/graph")
    def get_graph_alias(request: Request):
        snapshot = request.app.state.graph_store.export_snapshot()
        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.name,
                    "type": n.node_type.value,
                    "version": n.version or n.latest_version or "",
                }
                for n in snapshot.nodes
            ],
            "edges": [
                {
                    "s": e.source,
                    "t": e.target,
                    "kind": "inferred" if e.modality.value == "inferred" else "observed",
                    "ev": e.source_url or (e.evidence_ids[0] if e.evidence_ids else ""),
                }
                for e in snapshot.edges
            ],
        }

    @app.get("/api/scheduler")
    def get_scheduler_alias(request: Request):
        scheduler = getattr(request.app.state, "scheduler_engine", None)
        if not scheduler:
            return {"status": "idle", "next_run": None}
        health = scheduler.get_health()
        next_run = None
        for s in health.sources:
            if s.next_scheduled_run_at:
                if next_run is None or s.next_scheduled_run_at < next_run:
                    next_run = s.next_scheduled_run_at
        return {
            "status": "running" if health.is_running else "paused",
            "next_run": next_run.isoformat() if next_run else None,
        }

    @app.get("/api/impact")
    async def get_impact_alias(request: Request, signal_id: str = ""):
        from .schemas.investigation import InvestigationRequest
        service = request.app.state.investigation_service
        req = InvestigationRequest(
            query=f"Investigate downstream impact of {signal_id}" if signal_id else "Assess technology risk",
            target_technology=None,
        )
        return await service.investigate(req)

    @app.get("/api/evidence/{evidence_id}")
    def get_evidence_alias(request: Request, evidence_id: str):
        from .schemas.event import IntelligenceEvent
        disk_store = request.app.state.disk_store
        events = disk_store.load_all("events", IntelligenceEvent)
        for e in events:
            if e.id == evidence_id or evidence_id in e.id:
                ev = e.evidence[0] if e.evidence else None
                return {
                    "url": ev.source_url if ev else "",
                    "publisher": ev.source_type if ev else "Official source",
                    "excerpt": ev.snippet if ev else e.summary,
                    "published_at": e.timestamp.isoformat(),
                    "version": "1.0",
                    "hash": ev.content_hash if ev else "",
                    "relationships": [f"{e.primary_technology} -> {ent}" for ent in e.affected_entities],
                }
        return {
            "url": "https://github.com/adityasystems99/ORACLE",
            "publisher": "ORACLE Knowledge Graph",
            "excerpt": f"Evidence reference for signal {evidence_id}",
            "published_at": "",
            "version": "1.0",
            "hash": "",
            "relationships": [],
        }

    @app.post("/api/copilot/chat")
    async def post_copilot_chat_alias(request: Request):
        from .schemas.copilot import CopilotChatRequest
        service = request.app.state.copilot_service
        body = await request.json()
        message = body.get("message", "")
        session_id = body.get("session_id")
        if not session_id or not service.get_session(session_id):
            sess = service.create_session(title="Investigation Chat", primary_technology="general", severity="medium")
            session_id = sess.id
        chat_req = CopilotChatRequest(message=message)
        resp = await service.chat(session_id, chat_req)
        return {
            "answer": resp.content,
            "citations": [
                {
                    "id": c.source_url,
                    "url": c.source_url,
                    "publisher": c.publisher,
                    "excerpt": c.snippet,
                    "published_at": c.publication_timestamp.isoformat() if c.publication_timestamp else "",
                }
                for c in resp.evidence_citations
            ],
        }

    @app.get("/")
    def root():
        return {
            "app": settings.APP_NAME,
            "version": "0.1.0",
            "docs_url": "/docs",
            "description": "Live Intelligence Copilot API",
        }

    return app


app = create_app()
