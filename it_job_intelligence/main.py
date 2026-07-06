import asyncio
from contextlib import suppress
from pathlib import Path

from apify import Actor, PP
from crawlee import (
    ConcurrencySettings,
    RequestState,
    service_locator,
)
from crawlee.crawlers import (
    CheerioCrawler,
    CrawlerRunLog,
    RequestTransformAction,
    TransformConfig,
)
from crawlee.utils.replicate import replicate_metadata

from .routes import router


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}

        start_urls = []
        for item in actor_input.get("urls") or []:
            url = item.get("url") if isinstance(item, dict) else item
            if url:
                start_urls.append(url)

        search_query = (actor_input.get("searchQuery") or "").strip()
        location = (actor_input.get("location") or "").strip()
        max_jobs = int(actor_input.get("maxJobs") or 50)
        max_pages = int(actor_input.get("maxPages") or 3)

        if not start_urls and search_query and location:
            start_urls = [
                f"https://www.indeed.com/jobs?q={search_query.replace(' ', '+')}&l={location.replace(' ', '+')}",
                f"https://www.dice.com/jobs?q={search_query.replace(' ', '+')}&l={location.replace(' ', '+')}",
            ]

        if not start_urls:
            Actor.log.info("No start URLs provided. Provide urls or searchQuery + location.")
            return

        crawler = CheerioCrawler(
            max_requests_per_crawl=max_pages * 20 + len(start_urls),
            max_request_retries=4,
            request_handler=router,
            concurrency_settings=ConcurrencySettings(min_concurrency=1, max_concurrency=2),
        )

        crawler_options = {
            "startUrls": start_urls,
            "searchQuery": search_query,
            "location": location,
            "maxJobs": max_jobs,
            "maxPages": max_pages,
        }

        try:
            await crawler.run()
        except Exception as exc:
            Actor.log.exception(f"Crawler run failed: {exc}")
            raise
        finally:
            await Actor.push_data(crawler._dataset or {})
