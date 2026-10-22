"""Base connector interface for all ORACLE live intelligence ingestion sources."""

import abc
import hashlib
import logging
from typing import List, Optional
import httpx
from ..config import get_settings
from ..schemas.ingestion import IngestionSource, RawSignal

logger = logging.getLogger(__name__)


class BaseIngestionConnector(abc.ABC):
    """Abstract connector protocol for pulling external technology intelligence."""

    def __init__(self, source: IngestionSource):
        self.source = source
        self.settings = get_settings()

    @staticmethod
    def compute_hash(text: str) -> str:
        """Calculate deterministic SHA-256 hash for deduplication and diff tracking."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    async def get_http_client(self) -> httpx.AsyncClient:
        """Provide a preconfigured asynchronous HTTP client."""
        headers = {
            "User-Agent": self.settings.USER_AGENT,
            "Accept": "*/*",
        }
        if self.source.etag:
            headers["If-None-Match"] = self.source.etag
        if self.source.last_modified:
            headers["If-Modified-Since"] = self.source.last_modified

        return httpx.AsyncClient(
            headers=headers,
            timeout=self.settings.REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    @abc.abstractmethod
    async def fetch_signals(self) -> List[RawSignal]:
        """Fetch raw signals from the external source. Returns empty list if 304 Not Modified."""
        pass
