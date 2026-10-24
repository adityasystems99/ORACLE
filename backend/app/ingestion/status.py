"""Status page and incident advisory connector."""

from datetime import datetime, timezone
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
import feedparser
from .base import BaseIngestionConnector
from ..schemas.ingestion import RawSignal, SourceType
from ..schemas.rag import IngestedDocument, IngestionStatus

logger = logging.getLogger("oracle.ingestion.status")


class StatusPageConnector(BaseIngestionConnector):
    """Monitors status page incident feeds (Atlassian Statuspage JSON or Atom feeds)."""

    def _parse_entry_pub_date(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """Extract publication or updated date from entry without inventing timestamps."""
        import calendar
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

    async def fetch_documents(self) -> List[IngestedDocument]:
        docs: List[IngestedDocument] = []
        response = await self.fetch_with_retry(self.source.url)
        if not response or response.status_code == 304:
            return []
        if response.status_code != 200:
            logger.warning(f"Status page fetch failed {self.source.url}: HTTP {response.status_code}")
            return []

        # If Statuspage JSON endpoint (e.g. /api/v2/incidents.json)
        if response.headers.get("content-type", "").startswith("application/json") or "incidents.json" in self.source.url:
            try:
                data = response.json()
                incidents = data.get("incidents", [])[: self.settings.MAX_ITEMS_PER_FEED]
                for inc in incidents:
                    name = inc.get("name", "Service Incident")
                    status = inc.get("status", "investigating")
                    impact = inc.get("impact", "minor")
                    shortlink = inc.get("shortlink") or self.source.url
                    updates = inc.get("incident_updates", [])
                    latest_body = updates[0].get("body", "") if updates else ""

                    pub_dt = None
                    if "created_at" in inc:
                        try:
                            pub_dt = datetime.fromisoformat(inc["created_at"].replace("Z", "+00:00"))
                        except Exception:
                            pass

                    summary = f"[{status.upper()} - {impact.upper()} IMPACT] {name}. {latest_body}"
                    content_hash = self.compute_hash(f"{inc.get('id')}:{status}:{latest_body}")
                    doc_id = f"doc_stat_{self.compute_hash(shortlink)[:16]}"

                    docs.append(
                        IngestedDocument(
                            id=doc_id,
                            source_id=self.source.id,
                            source_url=shortlink,
                            publisher=self.source.name,
                            title=f"Incident: {name} ({impact})",
                            content=summary,
                            publication_timestamp=pub_dt,
                            content_hash=content_hash,
                            document_version=1,
                            ingestion_status=IngestionStatus.SUCCESS,
                            ecosystem=self.source.ecosystem,
                            metadata={"impact": impact, "status": status},
                        )
                    )
                return docs
            except Exception as e:
                logger.error(f"Error parsing JSON status incidents from {self.source.url}: {e}")

        # Feed format
        try:
            feed = feedparser.parse(response.text)
            publisher = getattr(feed.feed, "title", self.source.name)
            for entry in feed.entries[: self.settings.MAX_ITEMS_PER_FEED]:
                title = entry.get("title", "Status Update").strip()
                link = entry.get("link", self.source.url).strip()
                raw_content = entry.get("summary") or entry.get("description") or ""
                clean_text = BeautifulSoup(raw_content, "html.parser").get_text(separator=" ").strip() or title
                pub_dt = self._parse_entry_pub_date(entry)
                content_hash = self.compute_hash(f"{title}:{clean_text}")
                doc_id = f"doc_stat_{self.compute_hash(link)[:16]}"

                docs.append(
                    IngestedDocument(
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
                        metadata={"feed": publisher},
                    )
                )
        except Exception as e:
            logger.error(f"Error parsing XML status feed from {self.source.url}: {e}")

        return docs

    async def fetch_signals(self) -> List[RawSignal]:
        docs = await self.fetch_documents()
        return [
            RawSignal(
                id=f"sig_stat_{d.content_hash[:12]}",
                source_id=self.source.id,
                source_type=SourceType.STATUS_PAGE,
                title=d.title,
                url=d.source_url,
                content=d.content,
                published_at=d.publication_timestamp,
                content_hash=d.content_hash,
                metadata={"publisher": d.publisher},
            )
            for d in docs
        ]
