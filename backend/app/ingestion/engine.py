"""Ingestion Engine orchestrating connectors, deduplication, and persistence."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Type
from .base import BaseIngestionConnector
from .github import GitHubReleasesConnector
from .official import OfficialSourceConnector
from .rss import RSSConnector
from .security import SecurityAdvisoryConnector
from .status import StatusPageConnector
from ..config import get_settings
from ..schemas.ingestion import IngestionSource, RawSignal, SourceType
from ..storage.disk_store import DiskStore

logger = logging.getLogger(__name__)


CONNECTOR_REGISTRY: Dict[SourceType, Type[BaseIngestionConnector]] = {
    SourceType.RSS: RSSConnector,
    SourceType.CHANGELOG: RSSConnector,
    SourceType.GITHUB_RELEASES: GitHubReleasesConnector,
    SourceType.SECURITY_ADVISORY: SecurityAdvisoryConnector,
    SourceType.STATUS_PAGE: StatusPageConnector,
    SourceType.OFFICIAL_REGISTRY: OfficialSourceConnector,
}


DEFAULT_LIVE_SOURCES: List[IngestionSource] = [
    IngestionSource(
        id="src_fastapi_releases",
        name="FastAPI GitHub Releases",
        url="https://github.com/fastapi/fastapi/releases.atom",
        source_type=SourceType.GITHUB_RELEASES,
        ecosystem="python",
        refresh_interval_minutes=15,
    ),
    IngestionSource(
        id="src_pydantic_releases",
        name="Pydantic GitHub Releases",
        url="https://github.com/pydantic/pydantic/releases.atom",
        source_type=SourceType.GITHUB_RELEASES,
        ecosystem="python",
        refresh_interval_minutes=15,
    ),
    IngestionSource(
        id="src_python_insider",
        name="Python Insider Official Blog",
        url="https://feeds.feedburner.com/PythonInsider",
        source_type=SourceType.RSS,
        ecosystem="python",
        refresh_interval_minutes=30,
    ),
    IngestionSource(
        id="src_nodejs_releases",
        name="Node.js GitHub Releases",
        url="https://github.com/nodejs/node/releases.atom",
        source_type=SourceType.GITHUB_RELEASES,
        ecosystem="node",
        refresh_interval_minutes=30,
    ),
    IngestionSource(
        id="src_cloudflare_status",
        name="Cloudflare Status Incidents",
        url="https://www.cloudflarestatus.com/history.atom",
        source_type=SourceType.STATUS_PAGE,
        ecosystem="cloud",
        refresh_interval_minutes=10,
    ),
    IngestionSource(
        id="src_cisa_alerts",
        name="CISA Cybersecurity Advisories",
        url="https://www.cisa.gov/cybersecurity-advisories/all.xml",
        source_type=SourceType.SECURITY_ADVISORY,
        ecosystem="security",
        refresh_interval_minutes=60,
    ),
]


class IngestionEngine:
    """Manages sources and executes concurrent ingestion runs."""

    def __init__(self, disk_store: Optional[DiskStore] = None):
        self.settings = get_settings()
        self.disk_store = disk_store or DiskStore(self.settings.DATA_DIR)
        self._init_sources()

    def _init_sources(self) -> None:
        """Seed default sources if not present in disk store."""
        existing = self.disk_store.load_all("sources", IngestionSource)
        if not existing:
            self.disk_store.save_all("sources", DEFAULT_LIVE_SOURCES)
            logger.info(f"Initialized {len(DEFAULT_LIVE_SOURCES)} default live sources in disk store.")

    def get_sources(self) -> List[IngestionSource]:
        """List all configured ingestion sources."""
        return self.disk_store.load_all("sources", IngestionSource)

    def add_source(self, source: IngestionSource) -> None:
        """Add or update an ingestion source."""
        self.disk_store.upsert_item("sources", source)

    async def poll_source(self, source: IngestionSource) -> List[RawSignal]:
        """Poll a single source using its registered connector."""
        connector_cls = CONNECTOR_REGISTRY.get(source.source_type)
        if not connector_cls:
            logger.error(f"No connector registered for source type: {source.source_type}")
            return []

        connector = connector_cls(source)
        try:
            signals = await connector.fetch_signals()
            source.last_synced_at = datetime.now(timezone.utc)
            source.last_status = "success"
            self.disk_store.upsert_item("sources", source)
            return signals
        except Exception as e:
            source.last_synced_at = datetime.now(timezone.utc)
            source.last_status = f"error: {str(e)}"
            self.disk_store.upsert_item("sources", source)
            logger.error(f"Error polling source {source.id}: {e}")
            return []

    async def run_sync(self, source_id: Optional[str] = None) -> List[RawSignal]:
        """Run ingestion across enabled sources or a specific source."""
        sources = self.get_sources()
        if source_id:
            sources = [s for s in sources if s.id == source_id]
        else:
            sources = [s for s in sources if s.enabled]

        tasks = [self.poll_source(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        all_signals = [sig for sublist in results for sig in sublist]

        # Deduplicate against stored signals
        existing_signals = {s.content_hash: s for s in self.disk_store.load_all("raw_signals", RawSignal)}
        new_signals: List[RawSignal] = []

        for sig in all_signals:
            if sig.content_hash not in existing_signals:
                existing_signals[sig.content_hash] = sig
                new_signals.append(sig)

        if new_signals:
            self.disk_store.save_all("raw_signals", list(existing_signals.values()))
            logger.info(f"Ingested {len(new_signals)} new signals ({len(all_signals) - len(new_signals)} duplicates filtered).")

        return new_signals
