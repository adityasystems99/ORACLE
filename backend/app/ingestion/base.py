"""Base connector interface for all ORACLE live intelligence ingestion sources."""

import abc
import asyncio
import hashlib
import logging
from typing import List, Optional
import httpx
from ..config import get_settings
from ..schemas.ingestion import IngestionSource, RawSignal
from ..schemas.rag import IngestedDocument, IngestionStatus

logger = logging.getLogger("oracle.ingestion")


class BaseIngestionConnector(abc.ABC):
    """Abstract connector protocol for pulling external technology intelligence with retries and timeouts."""

    def __init__(
        self,
        source: IngestionSource,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.source = source
        self.settings = get_settings()
        self._injected_client = client

    @staticmethod
    def compute_hash(text: str) -> str:
        """Calculate deterministic SHA-256 hash for deduplication and diff tracking."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    async def get_http_client(self) -> httpx.AsyncClient:
        """Provide a preconfigured asynchronous HTTP client."""
        if self._injected_client:
            return self._injected_client

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

    async def fetch_with_retry(
        self,
        url: str,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> Optional[httpx.Response]:
        """Fetch URL with exponential backoff, rate limit handling, and structured logging."""
        headers = {
            "User-Agent": self.settings.USER_AGENT,
            "Accept": "*/*",
        }
        if self.source.etag:
            headers["If-None-Match"] = self.source.etag
        if self.source.last_modified:
            headers["If-Modified-Since"] = self.source.last_modified

        # Use injected client if provided, else create one for this request
        owns_client = self._injected_client is None
        client = self._injected_client or httpx.AsyncClient(
            headers=headers,
            timeout=self.settings.REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        )

        try:
            for attempt in range(1, max_retries + 1):
                try:
                    logger.debug(
                        f"Fetching source {self.source.id} from {url} (attempt {attempt}/{max_retries})"
                    )
                    response = await client.get(url, headers=headers)

                    # 304 Not Modified
                    if response.status_code == 304:
                        logger.info(f"Source {self.source.id} not modified (304).")
                        return response

                    # Rate limited: 429
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", 2.0))
                        logger.warning(
                            f"Rate limit encountered for {url} (HTTP 429). Retrying after {retry_after}s..."
                        )
                        await asyncio.sleep(min(retry_after, 5.0))
                        continue

                    # Server errors: 500, 502, 503, 504 -> retry
                    if response.status_code in {500, 502, 503, 504} and attempt < max_retries:
                        sleep_time = backoff_factor * (2 ** (attempt - 1))
                        logger.warning(
                            f"Transient HTTP {response.status_code} from {url}. Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                    # Update ETag / Last-Modified on source
                    if "etag" in response.headers:
                        self.source.etag = response.headers["etag"]
                    if "last-modified" in response.headers:
                        self.source.last_modified = response.headers["last-modified"]

                    return response

                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as exc:
                    if attempt < max_retries:
                        sleep_time = backoff_factor * (2 ** (attempt - 1))
                        logger.warning(
                            f"Network error on {url} ({exc.__class__.__name__}: {exc}). Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                    else:
                        logger.error(
                            f"Exceeded max retries ({max_retries}) connecting to {url}: {exc}"
                        )
                        return None
                except Exception as e:
                    logger.error(f"Unexpected error fetching {url}: {e}", exc_info=True)
                    return None

            return None
        finally:
            if owns_client:
                await client.aclose()

    @abc.abstractmethod
    async def fetch_signals(self) -> List[RawSignal]:
        """Fetch raw signals for backwards-compatible change detection."""
        pass

    @abc.abstractmethod
    async def fetch_documents(self) -> List[IngestedDocument]:
        """Fetch normalized IngestedDocument items with publisher, version, and provenance."""
        pass
