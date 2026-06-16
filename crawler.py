import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
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
    "hiring"
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
    "data"
]


def clean_url(url):
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")


def get_page_with_requests(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)

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
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
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
        text = tag.get_text(" ", strip=True).lower()
        href = tag["href"]
        full_url = urljoin(base_url, href)

        links.append({
            "text": text,
            "url": full_url
        })

    return links


def find_career_page(company_url):
    company_url = clean_url(company_url)

    common_paths = [
        "/careers",
        "/jobs",
        "/join-us",
        "/work-with-us",
        "/company/careers",
        "/about/careers"
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
        text = link["text"]
        url = link["url"].lower()

        for keyword in CAREER_KEYWORDS:
            keyword_url = keyword.replace(" ", "-")

            if keyword in text or keyword_url in url:
                return link["url"]

    return None


def find_open_position(career_page_url):
    pages_to_check = [career_page_url]
    visited = set()

    job_board_domains = [
        "greenhouse.io",
        "lever.co",
        "ashbyhq.com",
        "workdayjobs.com",
        "smartrecruiters.com",
        "icims.com",
        "breezy.hr"
    ]

    next_page_keywords = [
        "see open roles",
        "open roles",
        "view jobs",
        "search jobs",
        "job openings",
        "all jobs",
        "explore roles",
        "browse jobs",
        "positions"
    ]

    bad_keywords = [
        "privacy",
        "terms",
        "benefits",
        "culture",
        "linkedin",
        "twitter",
        "facebook",
        "instagram",
        "youtube",
        "mailto:"
    ]

    for depth in range(2):
        new_pages = []

        for page_url in pages_to_check:
            if page_url in visited:
                continue

            visited.add(page_url)

            html = get_page(page_url)

            if not html:
                continue

            links = get_links(page_url, html)

            for link in links:
                text = link["text"].lower()
                url = link["url"].lower()

                bad_link = False

                for bad_keyword in bad_keywords:
                    if bad_keyword in url or bad_keyword in text:
                        bad_link = True

                if bad_link:
                    continue

                for domain in job_board_domains:
                    if domain in url:
                        if "/job" in url or "/jobs" in url or "posting" in url or len(url) > 45:
                            return link["url"]

                for keyword in JOB_KEYWORDS:
                    if keyword in text or keyword in url:
                        if "/job" in url or "/jobs" in url or "/careers" in url or "/positions" in url:
                            return link["url"]

            for link in links:
                text = link["text"].lower()
                url = link["url"].lower()

                for keyword in next_page_keywords:
                    if keyword in text or keyword.replace(" ", "-") in url:
                        if link["url"] not in visited:
                            new_pages.append(link["url"])

                for domain in job_board_domains:
                    if domain in url:
                        if link["url"] not in visited:
                            new_pages.append(link["url"])

        pages_to_check = new_pages

    return None