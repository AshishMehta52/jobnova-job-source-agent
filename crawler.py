import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

CAREER_KEYWORDS = [
    "careers",
    "jobs",
    "join us",
    "work with us",
    "open roles",
    "open positions",
    "hiring",
    "employment",
    "opportunities"
]

JOB_KEYWORDS = [
    "engineer",
    "developer",
    "intern",
    "analyst",
    "designer",
    "manager",
    "scientist",
    "specialist",
    "associate",
    "software",
    "product",
    "data",
    "consultant",
    "research",
    "technical",
    "solutions"
]

JOB_BOARD_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workdayjobs.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "icims.com",
    "breezy.hr",
    "jobvite.com",
    "recruitee.com",
    "boards.greenhouse.io",
    "jobs.lever.co"
]

BAD_KEYWORDS = [
    "privacy",
    "terms",
    "benefits",
    "culture",
    "linkedin",
    "twitter",
    "facebook",
    "instagram",
    "youtube",
    "mailto:",
    "login",
    "sign-in",
    "signin"
]


def clean_url(url):
    if not url:
        return None

    url = url.strip()

    if not url.startswith("http"):
        url = "https://" + url

    return url.rstrip("/")


def same_domain_or_job_board(base_url, test_url):
    try:
        base_domain = urlparse(base_url).netloc.lower().replace("www.", "")
        test_domain = urlparse(test_url).netloc.lower().replace("www.", "")

        if base_domain and base_domain in test_domain:
            return True

        for domain in JOB_BOARD_DOMAINS:
            if domain in test_domain:
                return True

    except Exception:
        return False

    return False


def looks_like_job_or_career_page(url):
    if not url:
        return False

    lower_url = url.lower()

    useful_parts = [
        "/careers",
        "/career",
        "/jobs",
        "/job",
        "/positions",
        "/openings",
        "/roles",
        "greenhouse.io",
        "lever.co",
        "ashbyhq.com",
        "workdayjobs.com",
        "myworkdayjobs.com",
        "smartrecruiters.com",
        "icims.com"
    ]

    for part in useful_parts:
        if part in lower_url:
            return True

    return False


def is_bad_link(text, url):
    text = text.lower()
    url = url.lower()

    for bad_keyword in BAD_KEYWORDS:
        if bad_keyword in text or bad_keyword in url:
            return True

    return False


def get_page_with_requests(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=12,
            allow_redirects=True
        )

        if response.status_code >= 200 and response.status_code < 400:
            return response.text

    except requests.RequestException:
        return None

    return None


def get_page_with_playwright(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
            return html

    except Exception:
        return None


def get_page(url):
    html = get_page_with_requests(url)

    if html:
        return html

    html = get_page_with_playwright(url)

    return html


def get_links(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for tag in soup.find_all("a", href=True):
        text = tag.get_text(" ", strip=True)
        href = tag["href"]
        full_url = urljoin(base_url, href)

        links.append({
            "text": text,
            "url": full_url
        })

    return links


def extract_json_ld_job_url(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        try:
            data = json.loads(script.string)
        except Exception:
            continue

        job_url = find_jobposting_url_in_json(data)

        if job_url:
            return urljoin(base_url, job_url)

    return None


def find_jobposting_url_in_json(data):
    if isinstance(data, dict):
        item_type = data.get("@type")

        if item_type == "JobPosting":
            url = data.get("url") or data.get("sameAs")

            if url:
                return url

        for value in data.values():
            found = find_jobposting_url_in_json(value)

            if found:
                return found

    if isinstance(data, list):
        for item in data:
            found = find_jobposting_url_in_json(item)

            if found:
                return found

    return None


def find_career_page(company_url):
    company_url = clean_url(company_url)

    if not company_url:
        return None

    if looks_like_job_or_career_page(company_url):
        return company_url

    common_paths = [
        "/careers",
        "/career",
        "/jobs",
        "/job",
        "/join-us",
        "/work-with-us",
        "/company/careers",
        "/about/careers",
        "/en/careers",
        "/us/en/careers",
        "/employment",
        "/opportunities"
    ]

    for path in common_paths:
        test_url = company_url + path
        html = get_page(test_url)

        if html:
            return test_url

    html = get_page(company_url)

    if not html:
        return None

    links = get_links(company_url, html)

    for link in links:
        text = link["text"].lower()
        url = link["url"].lower()

        if is_bad_link(text, url):
            continue

        for keyword in CAREER_KEYWORDS:
            keyword_url = keyword.replace(" ", "-")

            if keyword in text or keyword_url in url:
                if same_domain_or_job_board(company_url, link["url"]):
                    return link["url"]

    return None


def link_looks_like_job_post(link):
    text = link["text"].lower()
    url = link["url"].lower()

    if is_bad_link(text, url):
        return False

    for domain in JOB_BOARD_DOMAINS:
        if domain in url:
            if "/job" in url or "/jobs" in url or "posting" in url or len(url) > 45:
                return True

    for keyword in JOB_KEYWORDS:
        if keyword in text or keyword in url:
            if (
                "/job" in url
                or "/jobs" in url
                or "/careers" in url
                or "/positions" in url
                or "/openings" in url
                or "/roles" in url
            ):
                return True

    return False


def link_looks_like_next_jobs_page(link):
    text = link["text"].lower()
    url = link["url"].lower()

    if is_bad_link(text, url):
        return False

    next_page_keywords = [
        "see open roles",
        "open roles",
        "view jobs",
        "search jobs",
        "job openings",
        "all jobs",
        "explore roles",
        "browse jobs",
        "positions",
        "view openings",
        "current openings"
    ]

    for keyword in next_page_keywords:
        if keyword in text or keyword.replace(" ", "-") in url:
            return True

    for domain in JOB_BOARD_DOMAINS:
        if domain in url:
            return True

    return False


def find_open_position(start_url, max_depth=3):
    start_url = clean_url(start_url)

    if not start_url:
        return None

    pages_to_check = [start_url]
    visited = set()

    for depth in range(max_depth):
        new_pages = []

        for page_url in pages_to_check:
            if page_url in visited:
                continue

            visited.add(page_url)

            html = get_page(page_url)

            if not html:
                continue

            json_ld_job_url = extract_json_ld_job_url(page_url, html)

            if json_ld_job_url:
                return json_ld_job_url

            links = get_links(page_url, html)

            for link in links:
                if link_looks_like_job_post(link):
                    return link["url"]

            for link in links:
                if link["url"] in visited:
                    continue

                if link_looks_like_next_jobs_page(link):
                    new_pages.append(link["url"])

        pages_to_check = new_pages

    return None