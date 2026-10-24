"""Connector for official technology registry APIs and primary security advisories."""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import feedparser
from .base import BaseIngestionConnector
from ..schemas.ingestion import RawSignal, SourceType
from ..schemas.rag import IngestedDocument, IngestionStatus

logger = logging.getLogger("oracle.ingestion.official")


class OfficialSourceConnector(BaseIngestionConnector):
    """Connector for official registries (PyPI, NPM) and structured advisory sources."""

    def _parse_iso_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Safely parse ISO-8601 or RFC-3339 timestamps."""
        if not date_str:
            return None
        try:
            # Handle trailing Z
            clean = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean)
        except Exception:
            return None

    async def fetch_documents(self) -> List[IngestedDocument]:
        """Fetch documents from official technology sources (JSON APIs or XML)."""
        docs: List[IngestedDocument] = []
        response = await self.fetch_with_retry(self.source.url)
        if not response or response.status_code == 304:
            return []
        if response.status_code != 200:
            logger.warning(f"Official source fetch failed for {self.source.url}: HTTP {response.status_code}")
            return []

        content_type = response.headers.get("content-type", "").lower()

        # 1. PyPI JSON API: e.g. https://pypi.org/pypi/fastapi/json
        if "pypi.org/pypi/" in self.source.url or "application/json" in content_type:
            try:
                data = response.json()
                info = data.get("info", {})
                pkg_name = info.get("name", self.source.name)
                version = info.get("version", "latest")
                summary = info.get("summary") or info.get("description") or ""
                author = info.get("author") or info.get("maintainer") or "PyPI Author"
                canonical_url = info.get("package_url") or info.get("project_url") or self.source.url

                # Check releases list for actual upload publication timestamp
                pub_dt = None
                releases = data.get("releases", {})
                if version in releases and releases[version]:
                    first_file = releases[version][0]
                    upload_time = first_file.get("upload_time_iso_8601") or first_file.get("upload_time")
                    pub_dt = self._parse_iso_date(upload_time)

                clean_text = f"Package: {pkg_name} {version}\nSummary: {summary}\nLicense: {info.get('license', 'unknown')}"
                content_hash = self.compute_hash(clean_text)
                doc_id = f"doc_pypi_{self.compute_hash(canonical_url)[:16]}"

                doc = IngestedDocument(
                    id=doc_id,
                    source_id=self.source.id,
                    source_url=canonical_url,
                    publisher=f"{pkg_name} Maintainers ({author})",
                    title=f"{pkg_name} {version} Release",
                    content=clean_text,
                    publication_timestamp=pub_dt,
                    content_hash=content_hash,
                    document_version=1,
                    ingestion_status=IngestionStatus.SUCCESS,
                    ecosystem="python",
                    metadata={
                        "package": pkg_name,
                        "version": version,
                        "requires_python": info.get("requires_python"),
                    },
                )
                docs.append(doc)
                return docs

            except Exception as e:
                logger.error(f"Error parsing official JSON payload for {self.source.url}: {e}", exc_info=True)

        # 2. CISA or Security Bulletins in XML / Atom format
        try:
            feed = feedparser.parse(response.text)
            publisher = getattr(feed.feed, "title", self.source.name)
            for entry in feed.entries[: self.settings.MAX_ITEMS_PER_FEED]:
                title = entry.get("title", "Advisory").strip()
                link = entry.get("link", self.source.url).strip()
                raw_body = entry.get("summary") or entry.get("description") or ""
                clean_body = BeautifulSoup(raw_body, "html.parser").get_text(separator=" ").strip() or title

                pub_dt = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    import calendar
                    pub_dt = datetime.fromtimestamp(calendar.timegm(entry.published_parsed), tz=timezone.utc)

                content_hash = self.compute_hash(f"{title}:{clean_body}")
                doc_id = f"doc_sec_{self.compute_hash(link)[:16]}"

                docs.append(
                    IngestedDocument(
                        id=doc_id,
                        source_id=self.source.id,
                        source_url=link,
                        publisher=publisher,
                        title=title,
                        content=clean_body,
                        publication_timestamp=pub_dt,
                        content_hash=content_hash,
                        document_version=1,
                        ingestion_status=IngestionStatus.SUCCESS,
                        ecosystem=self.source.ecosystem,
                        metadata={"source_title": publisher},
                    )
                )
        except Exception as e:
            logger.error(f"Error parsing official bulletin feed {self.source.url}: {e}", exc_info=True)

        return docs

    async def fetch_signals(self) -> List[RawSignal]:
        """Backwards-compatible signal generation."""
        docs = await self.fetch_documents()
        signals: List[RawSignal] = []
        for d in docs:
            signals.append(
                RawSignal(
                    id=f"sig_off_{d.content_hash[:12]}",
                    source_id=self.source.id,
                    source_type=SourceType.SECURITY_ADVISORY,
                    title=d.title,
                    url=d.source_url,
                    content=d.content,
                    published_at=d.publication_timestamp,
                    content_hash=d.content_hash,
                    metadata={"publisher": d.publisher},
                )
            )
        return signals
