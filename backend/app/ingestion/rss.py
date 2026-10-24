"""RSS and Atom feed connector for blogs, release feeds, and announcements."""

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

logger = logging.getLogger("oracle.ingestion.rss")


class RSSConnector(BaseIngestionConnector):
    """Parses standard RSS 2.0 and Atom XML feeds with reliable provenance tracking."""

    def _extract_publisher(self, feed: feedparser.FeedParserDict) -> str:
        """Derive authoritative publisher from feed metadata."""
        if hasattr(feed, "feed") and feed.feed:
            if "author" in feed.feed and feed.feed.author:
                return str(feed.feed.author).strip()
            if "title" in feed.feed and feed.feed.title:
                return str(feed.feed.title).strip()
        return self.source.name

    def _parse_pub_date(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """Extract authoritative upstream publication timestamp.

        Reliability Rule: Do NOT invent publication time or substitute retrieval time!
        Returns None if source does not provide publication or update date.
        """
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime.fromtimestamp(calendar.timegm(entry.published_parsed), tz=timezone.utc)
            except Exception:
                pass
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime.fromtimestamp(calendar.timegm(entry.updated_parsed), tz=timezone.utc)
            except Exception:
                pass
        return None

    async def _fetch_and_parse_feed(self) -> Optional[feedparser.FeedParserDict]:
        """Fetch feed text with retries and parse."""
        response = await self.fetch_with_retry(self.source.url)
        if not response or response.status_code == 304:
            return None
        if response.status_code != 200:
            logger.warning(f"Failed fetching {self.source.url}: HTTP {response.status_code}")
            return None

        return feedparser.parse(response.text)

    async def fetch_documents(self) -> List[IngestedDocument]:
        """Fetch documents with source URL, publisher, timestamps, and hashes."""
        docs: List[IngestedDocument] = []
        feed = await self._fetch_and_parse_feed()
        if not feed or not feed.entries:
            return []

        publisher = self._extract_publisher(feed)
        entries = feed.entries[: self.settings.MAX_ITEMS_PER_FEED]

        for entry in entries:
            title = entry.get("title", "Untitled Notice").strip()
            link = entry.get("link", self.source.url).strip()
            raw_summary = entry.get("summary") or entry.get("description") or ""

            # Strip HTML tags cleanly
            clean_text = BeautifulSoup(raw_summary, "html.parser").get_text(separator=" ").strip()
            if not clean_text:
                clean_text = title

            pub_dt = self._parse_pub_date(entry)
            content_hash = self.compute_hash(f"{title}:{clean_text}")
            doc_id = f"doc_{self.compute_hash(link)[:16]}"

            entry_author = entry.get("author") or publisher

            doc = IngestedDocument(
                id=doc_id,
                source_id=self.source.id,
                source_url=link,
                publisher=entry_author,
                title=title,
                content=clean_text,
                publication_timestamp=pub_dt,
                content_hash=content_hash,
                document_version=1,
                ingestion_status=IngestionStatus.SUCCESS,
                ecosystem=self.source.ecosystem,
                metadata={
                    "feed_title": publisher,
                    "tags": [t.get("term") for t in entry.get("tags", []) if isinstance(t, dict)],
                },
            )
            docs.append(doc)

        return docs

    async def fetch_signals(self) -> List[RawSignal]:
        """Fetch raw signals for backwards-compatible change detection."""
        signals: List[RawSignal] = []
        feed = await self._fetch_and_parse_feed()
        if not feed or not feed.entries:
            return []

        publisher = self._extract_publisher(feed)
        entries = feed.entries[: self.settings.MAX_ITEMS_PER_FEED]

        for entry in entries:
            title = entry.get("title", "Untitled Notice").strip()
            link = entry.get("link", self.source.url).strip()
            raw_summary = entry.get("summary") or entry.get("description") or ""
            clean_text = BeautifulSoup(raw_summary, "html.parser").get_text(separator=" ").strip() or title
            pub_dt = self._parse_pub_date(entry)
            content_hash = self.compute_hash(f"{title}:{clean_text}")

            signals.append(
                RawSignal(
                    id=f"sig_rss_{content_hash[:12]}",
                    source_id=self.source.id,
                    source_type=SourceType.RSS,
                    title=title,
                    url=link,
                    content=clean_text,
                    published_at=pub_dt,
                    content_hash=content_hash,
                    metadata={"publisher": publisher},
                )
            )

        return signals
