import os
from urllib.parse import urlparse

from apify_client import ApifyClient
from dotenv import load_dotenv


load_dotenv()

APIFY_ACTOR_ID = "curious_coder/linkedin-jobs-scraper"


def is_linkedin_jobs_url(url):
    if not url:
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    return "linkedin.com" in domain and "/jobs" in path


def clean_url(url):
    if not url:
        return None

    return url.strip()


def get_apify_token():
    token = os.getenv("APIFY_API_TOKEN")

    if token:
        token = token.strip().strip('"').strip("'")

    return token


def normalize_text(text):
    if not text:
        return ""

    cleaned = ""

    for char in text.lower():
        if char.isalnum():
            cleaned += char

    return cleaned


def company_matches(target_company, company_name):
    if not target_company or not company_name:
        return False

    target = normalize_text(target_company)
    name = normalize_text(company_name)

    if not target or not name:
        return False

    return target == name or target in name or name in target


def is_valid_company_website(url):
    if not url:
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    blocked_domains = [
        "linkedin.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "instagram.com",
        "youtube.com",
        "google.com",
    ]

    for blocked in blocked_domains:
        if blocked in domain:
            return False

    return parsed.scheme in ["http", "https"] and "." in domain


def pick_first_value(item, possible_keys):
    for key in possible_keys:
        value = item.get(key)

        if value:
            return value

    return None


def get_default_dataset_id(run):
    if run is None:
        return None

    if isinstance(run, dict):
        return run.get("defaultDatasetId") or run.get("default_dataset_id")

    dataset_id = getattr(run, "default_dataset_id", None)

    if dataset_id:
        return dataset_id

    dataset_id = getattr(run, "defaultDatasetId", None)

    if dataset_id:
        return dataset_id

    if hasattr(run, "model_dump"):
        data = run.model_dump()
        return data.get("defaultDatasetId") or data.get("default_dataset_id")

    if hasattr(run, "dict"):
        data = run.dict()
        return data.get("defaultDatasetId") or data.get("default_dataset_id")

    return None


def get_dataset_items(client, dataset_id):
    try:
        dataset_items_response = client.dataset(dataset_id).list_items()
        return dataset_items_response.items
    except Exception:
        try:
            return list(client.dataset(dataset_id).iterate_items())
        except Exception:
            return []


def extract_company_info_from_apify_item(item):
    company_name = pick_first_value(
        item,
        [
            "companyName",
            "company_name",
            "company",
            "companyTitle",
            "organization",
        ],
    )

    company_website = pick_first_value(
        item,
        [
            "companyWebsite",
            "company_website",
            "companyWebsiteUrl",
            "company_url",
            "website",
            "websiteUrl",
        ],
    )

    if not is_valid_company_website(company_website):
        company_website = None

    company_linkedin_url = pick_first_value(
        item,
        [
            "companyLinkedinUrl",
            "companyLinkedInUrl",
            "company_linkedin_url",
            "companyUrl",
        ],
    )

    job_title = pick_first_value(
        item,
        [
            "title",
            "jobTitle",
            "job_title",
            "position",
        ],
    )

    linkedin_job_url = pick_first_value(
        item,
        [
            "link",
            "job_link",
            "jobUrl",
            "job_url",
            "url",
        ],
    )

    return {
        "company_name": company_name,
        "company_website": company_website,
        "company_linkedin_url": company_linkedin_url,
        "job_title": job_title,
        "linkedin_job_url": linkedin_job_url,
        "raw_item": item,
    }


def score_extracted_item(extracted):
    score = 0

    if extracted["company_name"]:
        score += 10

    if extracted["company_website"]:
        score += 25

    if extracted["linkedin_job_url"]:
        score += 5

    if extracted["job_title"]:
        score += 3

    return score


def extract_best_company_info(items, fallback_url, target_company=None):
    if not items:
        return {
            "company_name": None,
            "company_website": None,
            "company_linkedin_url": None,
            "job_title": None,
            "linkedin_job_url": fallback_url,
            "raw_item": None,
            "target_match_found": False,
        }

    extracted_items = []

    for item in items:
        extracted = extract_company_info_from_apify_item(item)
        extracted_items.append(extracted)

    if target_company:
        matching_items = []

        for extracted in extracted_items:
            if company_matches(target_company, extracted["company_name"]):
                matching_items.append(extracted)

        if not matching_items:
            return {
                "company_name": None,
                "company_website": None,
                "company_linkedin_url": None,
                "job_title": None,
                "linkedin_job_url": fallback_url,
                "raw_item": None,
                "target_match_found": False,
            }

        extracted_items = matching_items

    best_item = None
    best_score = -1

    for extracted in extracted_items:
        score = score_extracted_item(extracted)

        if score > best_score:
            best_score = score
            best_item = extracted

    if not best_item:
        return {
            "company_name": None,
            "company_website": None,
            "company_linkedin_url": None,
            "job_title": None,
            "linkedin_job_url": fallback_url,
            "raw_item": None,
            "target_match_found": False,
        }

    best_item["target_match_found"] = True
    return best_item


def extract_linkedin_job_info(linkedin_url, count=50, target_company=None):
    linkedin_url = clean_url(linkedin_url)

    if not is_linkedin_jobs_url(linkedin_url):
        return {
            "company_name": None,
            "company_website": None,
            "company_linkedin_url": None,
            "job_title": None,
            "linkedin_job_url": linkedin_url,
            "linkedin_status": "Invalid LinkedIn jobs URL",
            "raw_item": None,
        }

    token = get_apify_token()

    if not token:
        return {
            "company_name": None,
            "company_website": None,
            "company_linkedin_url": None,
            "job_title": None,
            "linkedin_job_url": linkedin_url,
            "linkedin_status": "Missing APIFY_API_TOKEN in .env",
            "raw_item": None,
        }

    try:
        client = ApifyClient(token)

        run_input = {
            "urls": [linkedin_url],
            "count": max(count, 10),
        }

        run = client.actor(APIFY_ACTOR_ID).call(run_input=run_input)

        dataset_id = get_default_dataset_id(run)

        if not dataset_id:
            return {
                "company_name": None,
                "company_website": None,
                "company_linkedin_url": None,
                "job_title": None,
                "linkedin_job_url": linkedin_url,
                "linkedin_status": "Apify run completed but no default dataset ID was found",
                "raw_item": None,
            }

        items = get_dataset_items(client, dataset_id)

        if not items:
            return {
                "company_name": None,
                "company_website": None,
                "company_linkedin_url": None,
                "job_title": None,
                "linkedin_job_url": linkedin_url,
                "linkedin_status": "Apify returned no LinkedIn job results",
                "raw_item": None,
            }

        extracted = extract_best_company_info(
            items,
            fallback_url=linkedin_url,
            target_company=target_company,
        )

        if target_company and not extracted.get("target_match_found"):
            status = f"Target company '{target_company}' was not found in Apify results"
        elif extracted["company_name"] and extracted["company_website"]:
            status = "Apify LinkedIn extraction successful"
        elif extracted["company_name"]:
            status = "Apify found company name but not company website"
        else:
            status = "Apify extraction incomplete"

        return {
            "company_name": extracted["company_name"],
            "company_website": extracted["company_website"],
            "company_linkedin_url": extracted["company_linkedin_url"],
            "job_title": extracted["job_title"],
            "linkedin_job_url": extracted["linkedin_job_url"] or linkedin_url,
            "linkedin_status": status,
            "raw_item": extracted["raw_item"],
        }

    except Exception as error:
        return {
            "company_name": None,
            "company_website": None,
            "company_linkedin_url": None,
            "job_title": None,
            "linkedin_job_url": linkedin_url,
            "linkedin_status": f"Apify extraction error: {error}",
            "raw_item": None,
        }