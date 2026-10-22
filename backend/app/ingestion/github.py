"""GitHub Releases and Changelog connector."""

import logging
from datetime import datetime, timezone
import time
from typing import List
from bs4 import BeautifulSoup
import feedparser
from .base import BaseIngestionConnector
from ..schemas.ingestion import RawSignal, SourceType

logger = logging.getLogger(__name__)


class GitHubReleasesConnector(BaseIngestionConnector):
    """Parses GitHub release feeds (Atom format or REST API endpoint)."""

    async def fetch_signals(self) -> List[RawSignal]:
        signals: List[RawSignal] = []
        target_url = self.source.url

        # If user provides standard repo URL e.g. https://github.com/fastapi/fastapi,
        # convert to releases.atom automatically for unauthenticated rate-limit resilience
        if "github.com" in target_url and not target_url.endswith(".atom") and "api.github.com" not in target_url:
            clean_url = target_url.rstrip("/")
            if not clean_url.endswith("/releases"):
                target_url = f"{clean_url}/releases.atom"
            else:
                target_url = f"{clean_url}.atom"

        try:
            async with await self.get_http_client() as client:
                response = await client.get(target_url)
                if response.status_code == 304:
                    return []
                if response.status_code != 200:
                    logger.warning(f"GitHub fetch failed for {target_url}: HTTP {response.status_code}")
                    return []

                content = response.text

            # Parse Atom feed
            feed = feedparser.parse(content)
            entries = feed.entries[: self.settings.MAX_ITEMS_PER_FEED]

            for entry in entries:
                title = entry.get("title", "GitHub Release")
                link = entry.get("link", target_url)
                raw_content = entry.get("content", [{}])[0].get("value") or entry.get("summary") or ""

                clean_text = BeautifulSoup(raw_content, "html.parser").get_text(separator="\n").strip()
                if not clean_text:
                    clean_text = title

                pub_dt = None
                if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
                else:
                    pub_dt = datetime.now(timezone.utc)

                content_hash = self.compute_hash(f"{title}:{clean_text}")
                signal_id = f"sig_gh_{content_hash[:12]}"

                signals.append(
                    RawSignal(
                        id=signal_id,
                        source_id=self.source.id,
                        source_type=SourceType.GITHUB_RELEASES,
                        title=title,
                        url=link,
                        content=clean_text,
                        published_at=pub_dt,
                        content_hash=content_hash,
                        metadata={
                            "repository": self.source.name,
                            "tag": title.split()[-1] if title else "unknown",
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Error fetching GitHub releases for {target_url}: {e}", exc_info=True)

        return signals
