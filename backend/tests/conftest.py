"""Pytest test configuration and fixtures."""

import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.config import Settings, get_settings
from app.graph.store import KnowledgeGraphStore
from app.llm.mock_adapter import MockLLMAdapter
from app.main import create_app
from app.retrieval.vector_store import VectorStore
from app.storage.disk_store import DiskStore


@pytest.fixture
def temp_dir():
    """Create isolated temporary directory for test persistence."""
    d = tempfile.mkdtemp(prefix="oracle_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def test_disk_store(temp_dir):
    return DiskStore(temp_dir)


@pytest.fixture
def test_graph_store(temp_dir):
    return KnowledgeGraphStore(persist_path=temp_dir / "test_graph.json")


@pytest.fixture
def test_vector_store(temp_dir):
    return VectorStore(persist_dir=temp_dir / "test_chroma")


@pytest.fixture
def test_llm_adapter():
    return MockLLMAdapter(model_name="mock-model")


@pytest.fixture
def client(temp_dir, monkeypatch):
    """TestClient configured with isolated storage."""
    test_settings = Settings(
        DATA_DIR=temp_dir,
        GRAPH_PERSIST_PATH=temp_dir / "graph.json",
        CHROMA_PERSIST_DIR=temp_dir / "chroma",
        LLM_PROVIDER="mock",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: test_settings)
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
