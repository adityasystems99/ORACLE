"""RSS and Atom feed connector for blogs, release feeds, and announcements."""

import logging
from datetime import datetime, timezone
import time
from typing import List
from bs4 import BeautifulSoup
import feedparser
from .base import BaseIngestionConnector
from ..schemas.ingestion import RawSignal, SourceType

logger = logging.getLogger(__name__)


class RSSConnector(BaseIngestionConnector):
    """Parses standard RSS 2.0 and Atom XML feeds."""

    async def fetch_signals(self) -> List[RawSignal]:
        signals: List[RawSignal] = []
        try:
            async with await self.get_http_client() as client:
                response = await client.get(self.source.url)
                if response.status_code == 304:
                    logger.info(f"Source {self.source.id} ({self.source.name}) not modified (304).")
                    return []
                if response.status_code != 200:
                    logger.warning(f"Failed fetching {self.source.url}: HTTP {response.status_code}")
                    return []

                # Update etag/last-modified on source
                if "etag" in response.headers:
                    self.source.etag = response.headers["etag"]
                if "last-modified" in response.headers:
                    self.source.last_modified = response.headers["last-modified"]

                content = response.text

            # Parse with feedparser
            feed = feedparser.parse(content)
            entries = feed.entries[: self.settings.MAX_ITEMS_PER_FEED]

            for entry in entries:
                title = entry.get("title", "Untitled Notice")
                link = entry.get("link", self.source.url)
                raw_summary = entry.get("summary") or entry.get("description") or ""

                # Strip HTML tags for clean text content
                clean_text = BeautifulSoup(raw_summary, "html.parser").get_text(separator=" ").strip()
                if not clean_text:
                    clean_text = title

                # Parse publication time
                pub_dt = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
                else:
                    pub_dt = datetime.now(timezone.utc)

                content_hash = self.compute_hash(f"{title}:{clean_text}")
                signal_id = f"sig_rss_{content_hash[:12]}"

                signals.append(
                    RawSignal(
                        id=signal_id,
                        source_id=self.source.id,
                        source_type=SourceType.RSS,
                        title=title,
                        url=link,
                        content=clean_text,
                        published_at=pub_dt,
                        content_hash=content_hash,
                        metadata={
                            "author": entry.get("author", "unknown"),
                            "tags": [t.get("term") for t in entry.get("tags", []) if isinstance(t, dict)],
                            "feed_title": feed.feed.get("title", self.source.name),
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Error parsing RSS feed {self.source.url}: {e}", exc_info=True)

        return signals
