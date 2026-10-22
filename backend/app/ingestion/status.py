"""Status page and incident advisory connector."""

import logging
from datetime import datetime, timezone
from typing import List
from bs4 import BeautifulSoup
import feedparser
from .base import BaseIngestionConnector
from ..schemas.ingestion import RawSignal, SourceType

logger = logging.getLogger(__name__)


class StatusPageConnector(BaseIngestionConnector):
    """Monitors status page incident feeds (Atlassian Statuspage JSON or Atom feeds)."""

    async def fetch_signals(self) -> List[RawSignal]:
        signals: List[RawSignal] = []
        try:
            async with await self.get_http_client() as client:
                response = await client.get(self.source.url)
                if response.status_code == 304:
                    return []
                if response.status_code != 200:
                    logger.warning(f"Status page fetch failed {self.source.url}: HTTP {response.status_code}")
                    return []

                content = response.text

            # If Statuspage JSON endpoint (e.g. /api/v2/incidents.json)
            if response.headers.get("content-type", "").startswith("application/json") or "incidents.json" in self.source.url:
                data = response.json()
                incidents = data.get("incidents", [])[: self.settings.MAX_ITEMS_PER_FEED]
                for inc in incidents:
                    name = inc.get("name", "Service Incident")
                    status = inc.get("status", "investigating")
                    impact = inc.get("impact", "minor")
                    shortlink = inc.get("shortlink") or self.source.url
                    updates = inc.get("incident_updates", [])
                    latest_body = updates[0].get("body", "") if updates else ""

                    summary = f"[{status.upper()} - {impact.upper()} IMPACT] {name}. {latest_body}"
                    content_hash = self.compute_hash(f"{inc.get('id')}:{status}:{latest_body}")

                    signals.append(
                        RawSignal(
                            id=f"sig_stat_{content_hash[:12]}",
                            source_id=self.source.id,
                            source_type=SourceType.STATUS_PAGE,
                            title=f"Incident: {name} ({impact})",
                            url=shortlink,
                            content=summary,
                            published_at=datetime.now(timezone.utc),
                            content_hash=content_hash,
                            metadata={"impact": impact, "status": status},
                        )
                    )
            else:
                feed = feedparser.parse(content)
                for entry in feed.entries[: self.settings.MAX_ITEMS_PER_FEED]:
                    title = entry.get("title", "Status Update")
                    link = entry.get("link", self.source.url)
                    raw_content = entry.get("summary") or entry.get("description") or ""
                    clean_text = BeautifulSoup(raw_content, "html.parser").get_text(separator=" ").strip()

                    content_hash = self.compute_hash(f"{title}:{clean_text}")
                    signals.append(
                        RawSignal(
                            id=f"sig_stat_{content_hash[:12]}",
                            source_id=self.source.id,
                            source_type=SourceType.STATUS_PAGE,
                            title=title,
                            url=link,
                            content=clean_text or title,
                            published_at=datetime.now(timezone.utc),
                            content_hash=content_hash,
                            metadata={"source_name": self.source.name},
                        )
                    )

        except Exception as e:
            logger.error(f"Error fetching status updates from {self.source.url}: {e}", exc_info=True)

        return signals
