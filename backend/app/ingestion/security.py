"""Security advisories and vulnerability bulletin connector."""

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

logger = logging.getLogger("oracle.ingestion.security")


class SecurityAdvisoryConnector(BaseIngestionConnector):
    """Parses security advisory feeds (GitHub Security Advisories, CISA, NVD/OSV)."""

    def _parse_entry_pub_date(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """Extract publication or updated date from entry without inventing timestamps."""
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
            logger.warning(f"Security advisory fetch failed {self.source.url}: HTTP {response.status_code}")
            return []

        # If JSON API format
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                data = response.json()
                items = data if isinstance(data, list) else data.get("vulns", data.get("advisories", []))
                for item in items[: self.settings.MAX_ITEMS_PER_FEED]:
                    cve_id = item.get("id") or item.get("cve_id") or "CVE-ADVISORY"
                    summary = item.get("summary") or item.get("details") or ""
                    link = item.get("references", [{}])[0].get("url", self.source.url) if item.get("references") else self.source.url

                    pub_dt = None
                    if "published" in item:
                        try:
                            pub_dt = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
                        except Exception:
                            pass

                    clean_text = f"CVE: {cve_id}\nDetails: {summary}"
                    content_hash = self.compute_hash(f"{cve_id}:{clean_text}")
                    doc_id = f"doc_sec_{self.compute_hash(link)[:16]}"

                    docs.append(
                        IngestedDocument(
                            id=doc_id,
                            source_id=self.source.id,
                            source_url=link,
                            publisher=self.source.name,
                            title=f"{cve_id}: {summary[:80]}",
                            content=clean_text,
                            publication_timestamp=pub_dt,
                            content_hash=content_hash,
                            document_version=1,
                            ingestion_status=IngestionStatus.SUCCESS,
                            ecosystem=self.source.ecosystem,
                            metadata={"cve_id": cve_id},
                        )
                    )
                return docs
            except Exception as e:
                logger.error(f"Error parsing JSON advisories from {self.source.url}: {e}")

        # Feed format
        try:
            feed = feedparser.parse(response.text)
            publisher = getattr(feed.feed, "title", self.source.name)
            for entry in feed.entries[: self.settings.MAX_ITEMS_PER_FEED]:
                title = entry.get("title", "Security Advisory").strip()
                link = entry.get("link", self.source.url).strip()
                raw_content = entry.get("summary") or entry.get("description") or ""
                clean_text = BeautifulSoup(raw_content, "html.parser").get_text(separator=" ").strip() or title
                pub_dt = self._parse_entry_pub_date(entry)
                content_hash = self.compute_hash(f"{title}:{clean_text}")
                doc_id = f"doc_sec_{self.compute_hash(link)[:16]}"

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
            logger.error(f"Error parsing XML security advisories from {self.source.url}: {e}")

        return docs

    async def fetch_signals(self) -> List[RawSignal]:
        docs = await self.fetch_documents()
        return [
            RawSignal(
                id=f"sig_sec_{d.content_hash[:12]}",
                source_id=self.source.id,
                source_type=SourceType.SECURITY_ADVISORY,
                title=d.title,
                url=d.source_url,
                content=d.content,
                published_at=d.publication_timestamp,
                content_hash=d.content_hash,
                metadata={"publisher": d.publisher},
            )
            for d in docs
        ]
