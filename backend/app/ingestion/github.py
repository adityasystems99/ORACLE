"""GitHub Releases and Changelog connector."""

import calendar
from datetime import datetime, timezone
import logging
import time
from typing import List, Optional
from bs4 import BeautifulSoup
import feedparser
from .base import BaseIngestionConnector
from ..schemas.ingestion import RawSignal, SourceType
from ..schemas.rag import IngestedDocument, IngestionStatus

logger = logging.getLogger("oracle.ingestion.github")


class GitHubReleasesConnector(BaseIngestionConnector):
    """Parses GitHub release feeds (Atom format or REST API endpoint) with provenance."""

    def _get_target_atom_url(self) -> str:
        target_url = self.source.url
        if "github.com" in target_url and not target_url.endswith(".atom") and "api.github.com" not in target_url:
            clean_url = target_url.rstrip("/")
            if not clean_url.endswith("/releases"):
                return f"{clean_url}/releases.atom"
            return f"{clean_url}.atom"
        return target_url

    def _extract_publisher(self) -> str:
        # Extract owner/repo name
        url = self.source.url
        if "github.com/" in url:
            parts = url.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
        return self.source.name

    def _parse_pub_date(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """Extract publication or update date from Atom entry without inventing timestamps."""
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime.fromtimestamp(calendar.timegm(entry.updated_parsed), tz=timezone.utc)
            except Exception:
                pass
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime.fromtimestamp(calendar.timegm(entry.published_parsed), tz=timezone.utc)
            except Exception:
                pass
        return None

    async def _fetch_and_parse(self) -> Optional[feedparser.FeedParserDict]:
        target_url = self._get_target_atom_url()
        response = await self.fetch_with_retry(target_url)
        if not response or response.status_code == 304:
            return None
        if response.status_code != 200:
            logger.warning(f"GitHub fetch failed for {target_url}: HTTP {response.status_code}")
            return None

        return feedparser.parse(response.text)

    async def fetch_documents(self) -> List[IngestedDocument]:
        docs: List[IngestedDocument] = []
        feed = await self._fetch_and_parse()
        if not feed or not feed.entries:
            return []

        publisher = self._extract_publisher()
        entries = feed.entries[: self.settings.MAX_ITEMS_PER_FEED]

        for entry in entries:
            title = entry.get("title", "GitHub Release").strip()
            link = entry.get("link", self.source.url).strip()
            raw_content = entry.get("content", [{}])[0].get("value") or entry.get("summary") or ""

            clean_text = BeautifulSoup(raw_content, "html.parser").get_text(separator="\n").strip()
            if not clean_text:
                clean_text = title

            pub_dt = self._parse_pub_date(entry)
            content_hash = self.compute_hash(f"{title}:{clean_text}")
            doc_id = f"doc_{self.compute_hash(link)[:16]}"
            tag = title.split()[-1] if title else "release"

            doc = IngestedDocument(
                id=doc_id,
                source_id=self.source.id,
                source_url=link,
                publisher=publisher,
                title=title,
                content=clean_text,
                publication_timestamp=pub_dt,
                content_hash=content_hash,
                document_version=1,
                ingestion_status=IngestionStatus.SUCCESS,
                ecosystem=self.source.ecosystem,
                metadata={
                    "repository": publisher,
                    "release_tag": tag,
                },
            )
            docs.append(doc)

        return docs

    async def fetch_signals(self) -> List[RawSignal]:
        signals: List[RawSignal] = []
        feed = await self._fetch_and_parse()
        if not feed or not feed.entries:
            return []

        publisher = self._extract_publisher()
        entries = feed.entries[: self.settings.MAX_ITEMS_PER_FEED]

        for entry in entries:
            title = entry.get("title", "GitHub Release").strip()
            link = entry.get("link", self.source.url).strip()
            raw_content = entry.get("content", [{}])[0].get("value") or entry.get("summary") or ""
            clean_text = BeautifulSoup(raw_content, "html.parser").get_text(separator="\n").strip() or title
            pub_dt = self._parse_pub_date(entry)
            content_hash = self.compute_hash(f"{title}:{clean_text}")

            signals.append(
                RawSignal(
                    id=f"sig_gh_{content_hash[:12]}",
                    source_id=self.source.id,
                    source_type=SourceType.GITHUB_RELEASES,
                    title=title,
                    url=link,
                    content=clean_text,
                    published_at=pub_dt,
                    content_hash=content_hash,
                    metadata={"publisher": publisher, "tag": title.split()[-1] if title else "unknown"},
                )
            )

        return signals
