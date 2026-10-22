"""FastAPI Main Application Entrypoint for ORACLE."""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api.routes_events import router as events_router
from .api.routes_graph import router as graph_router
from .api.routes_impact import router as impact_router
from .api.routes_ingest import router as ingest_router
from .api.routes_system import router as system_router
from .change_detection.detector import ChangeDetector
from .config import get_settings
from .graph.store import KnowledgeGraphStore
from .impact.analyzer import ImpactAnalyzer
from .ingestion.engine import IngestionEngine
from .llm.factory import get_llm_adapter
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

    app.state.disk_store = disk_store
    app.state.graph_store = graph_store
    app.state.vector_store = vector_store
    app.state.llm_adapter = llm_adapter
    app.state.ingestion_engine = ingestion_engine
    app.state.change_detector = change_detector
    app.state.impact_analyzer = impact_analyzer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager initializing singletons and background resources."""
    settings = get_settings()
    logger.info(f"Initializing {settings.APP_NAME} in {settings.APP_ENV} mode...")
    init_app_state(app)
    logger.info(f"{settings.APP_NAME} initialization complete. Ready to serve requests.")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


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
    app.include_router(events_router)
    app.include_router(graph_router)
    app.include_router(impact_router)
    app.include_router(system_router)

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
