from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from apify import Actor
from crawlee.crawlers import Router
from crawlee.requests import RequestTransformAction

router = Router[None]()


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip() or ""


def _extract_text(dom, selector: str) -> str:
    with suppress(Exception):
        el = dom(selector).first()
        if el and el.length:
            return _clean_text(el.text())
    return ""


def _emit_charge(event_name: str) -> None:
    with suppress(RuntimeError):
        Actor.charge(event_name, {"event": event_name})


def _page_snapshot(dom) -> dict:
    snapshot = {"toolMentions": {}}
    texts = []
    try:
        texts.append(dom("body").text() or "")
    except Exception:
        pass

    normalized = " ".join(texts).lower()
    TOOLS = [
        "python", "java", "golang", "go", "node.js", "javascript", "typescript",
        "aws", "azure", "gcp", "terraform", "ansible", "kubernetes", "docker",
        "react", "angular", "vue", "spring", "django", "fastapi", "sql",
        "postgres", "mysql", "mongodb", "redis", "kafka", "spark", "databricks",
        "linux", "git", "ci/cd", "jenkins", "github actions", "llm", "rag",
        "prompt engineering", "mcp", "api", "rest", "graphql", "microservices",
    ]
    for tool in TOOLS:
        count = normalized.count(tool)
        if count:
            snapshot["toolMentions"][tool] = count
    return snapshot


def _extract_job(dom) -> dict:
    return {
        "title": _extract_text(dom, "h1, h2.jobTitle, [data-testid='jobTitle']"),
        "company": _extract_text(dom, "span.companyName, [data-testid='companyName']"),
        "location": _extract_text(dom, "div#recJobLocation, [data-testid='location']"),
        "salary": _extract_text(dom, "span.salaryText, span.estimated-salary"),
        "remote": "remote" in _extract_text(dom, "body").lower(),
        "postedAt": _extract_text(
            dom,
            "span.date, span.postedAge, [data-testid='job-age']",
        ),
        "url": "",
        "skills": [],
    }


@router.default
async def handle_listing(context) -> None:  # type: ignore[override]
    request = context.request
    Actor.log.info(f"LISTING: {request.url}")
    response = await context.router.send_request(request)
    await response.text()

    page_data = {}
    page_type = "listing"
    jobs = []
    seen_urls = set()

    if isinstance(response, str):
        from crawlee.crawlers._cheerio import CheerioCrawlerContext
        if hasattr(response, "dom"):
            dom = response.dom
        else:
            return
    else:
        if hasattr(response, "dom"):
            dom = response.dom
        else:
            return

    page_data = _page_snapshot(dom)
    job_cards = dom(".jobsearch-ResultsList li, .job_seen_beacon, [data-testid='jobListItem'], .job").to_list() if hasattr(dom(".jobsearch-ResultsList li, .job_seen_beacon, [data-testid='jobListItem'], .job"), "to_list") else dom(".jobsearch-ResultsList li, .job_seen_beacon, [data-testid='jobListItem'], .job")

    try:
        job_cards = dom(".jobsearch-ResultsList li, .job_seen_beacon, [data-testid='jobListItem'], .job")
        if hasattr(job_cards, "to_list"):
            job_cards = job_cards.to_list()
    except Exception:
        job_cards = []

    for card in job_cards:
        try:
            card_dom = dom(card)
            link_el = card_dom("a.jobTitle, a[data-jk], a[data-testid='jobTitle']").first()
            href = ""
            if link_el and link_el.length:
                href = link_el.attr("href") or ""
                href = urljoin(request.url, href)

            title = _extract_text(card_dom, "a.jobTitle, a[data-jk], a[data-testid='jobTitle']")
            company = _extract_text(card_dom, "span.companyName, span.company")
            location = _extract_text(card_dom, "div.recJobLoc, [data-testid='location']")
            salary = _extract_text(card_dom, "span.salaryText, span.estimated-salary")
            snippet = _clean_text(card_dom.text() or "")

            remote = "remote" in f"{title} {snippet} {location}".lower()
            posted_at = _extract_text(card_dom, "span.date, span.postedAge")

            if href and href not in seen_urls:
                seen_urls.add(href)
                job = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "remote": remote,
                    "postedAt": posted_at,
                    "url": href,
                    "skills": [],
                }
                jobs.append(job)
                try:
                    await Actor.push_data({"job_posting": job})
                    _emit_charge("job_posting")
                except Exception:
                    Actor.log.debug("Failed to push job_posting data.")
        except Exception:
            Actor.log.debug("Card parse failed.")

    await context.add_requests(
        [{"url": u, "userData": {"pageType": "detail"}} for u in list(seen_urls)[:10]]
    )

    snapshot = {
        "url": request.url,
        "pageType": page_type,
        "skillCounts": page_data.get("toolMentions", {}),
        "jobCount": len(jobs),
        "crawledAt": "",
    }
    try:
        await Actor.push_data({"skills_snapshot": snapshot})
        _emit_charge("skills_snapshot")
    except Exception:
        Actor.log.debug("Failed to push skills_snapshot data.")

    next_pages = dom("a[href*='start='], a[href*='page='], a[href*='pageOf='], button[aria-label='Next']").to_list() if hasattr(dom("a[href*='start='], a[href*='page='], a[href*='pageOf='], button[aria-label='Next']"), "to_list") else dom("a[href*='start='], a[href*='page='], a[href*='pageOf='], button[aria-label='Next']")

    try:
        next_pages = dom("a[href*='start='], a[href*='page='], a[href*='pageOf='], button[aria-label='Next']")
        if hasattr(next_pages, "to_list"):
            next_pages = next_pages.to_list()
        else:
            next_pages = []
    except Exception:
        next_pages = []

    for el in next_pages[:1]:
        try:
            href = el.attrib.get("href", "")
            if href and not str(href).startswith("http"):
                href = urljoin(request.url, str(href))
            if href:
                await context.add_requests([{"url": href, "userData": {"pageType": "listing"}}])
        except Exception:
            pass


@router.handler("detail")
async def handle_detail(context) -> None:  # type: ignore[override]
    request = context.request
    Actor.log.info(f"DETAIL: {request.url}")

    snapshot = {
        "url": request.url,
        "pageType": "detail",
        "skillCounts": {},
        "jobCount": 1,
        "crawledAt": "",
    }

    try:
        await Actor.push_data({"skills_snapshot": snapshot})
        _emit_charge("skills_snapshot")
    except Exception:
        Actor.log.debug("Failed to push skills_snapshot data.")
