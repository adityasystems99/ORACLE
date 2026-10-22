"""Security advisories and vulnerability bulletin connector."""

import logging
from datetime import datetime, timezone
from typing import List
from bs4 import BeautifulSoup
import feedparser
from .base import BaseIngestionConnector
from ..schemas.ingestion import RawSignal, SourceType

logger = logging.getLogger(__name__)


class SecurityAdvisoryConnector(BaseIngestionConnector):
    """Parses security advisory feeds (GitHub Security Advisories, CISA, NVD/OSV)."""

    async def fetch_signals(self) -> List[RawSignal]:
        signals: List[RawSignal] = []
        try:
            async with await self.get_http_client() as client:
                response = await client.get(self.source.url)
                if response.status_code == 304:
                    return []
                if response.status_code != 200:
                    logger.warning(f"Security advisory fetch failed {self.source.url}: HTTP {response.status_code}")
                    return []

                content = response.text

            # Check if JSON API or XML/Atom feed
            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                items = data if isinstance(data, list) else data.get("vulns", data.get("advisories", []))
                for item in items[: self.settings.MAX_ITEMS_PER_FEED]:
                    cve_id = item.get("id") or item.get("cve_id") or "CVE-UNKNOWN"
                    summary = item.get("summary") or item.get("details") or ""
                    link = item.get("references", [{}])[0].get("url", self.source.url) if item.get("references") else self.source.url
                    content_hash = self.compute_hash(f"{cve_id}:{summary}")
                    signals.append(
                        RawSignal(
                            id=f"sig_sec_{content_hash[:12]}",
                            source_id=self.source.id,
                            source_type=SourceType.SECURITY_ADVISORY,
                            title=f"{cve_id}: {summary[:80]}",
                            url=link,
                            content=summary,
                            published_at=datetime.now(timezone.utc),
                            content_hash=content_hash,
                            metadata={"cve_id": cve_id, "ecosystem": self.source.ecosystem},
                        )
                    )
            else:
                feed = feedparser.parse(content)
                for entry in feed.entries[: self.settings.MAX_ITEMS_PER_FEED]:
                    title = entry.get("title", "Security Advisory")
                    link = entry.get("link", self.source.url)
                    raw_content = entry.get("summary") or entry.get("description") or ""
                    clean_text = BeautifulSoup(raw_content, "html.parser").get_text(separator=" ").strip()

                    content_hash = self.compute_hash(f"{title}:{clean_text}")
                    signals.append(
                        RawSignal(
                            id=f"sig_sec_{content_hash[:12]}",
                            source_id=self.source.id,
                            source_type=SourceType.SECURITY_ADVISORY,
                            title=title,
                            url=link,
                            content=clean_text or title,
                            published_at=datetime.now(timezone.utc),
                            content_hash=content_hash,
                            metadata={"ecosystem": self.source.ecosystem},
                        )
                    )

        except Exception as e:
            logger.error(f"Error fetching security advisories from {self.source.url}: {e}", exc_info=True)

        return signals
