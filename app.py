import streamlit as st
import pandas as pd
from urllib.parse import urlparse, quote_plus

from agent import run_agent, run_direct_page_agent
from crawler import looks_like_job_or_career_page
from linkedin_extractor import extract_linkedin_job_info


st.set_page_config(page_title="AI Job Source Agent", layout="wide")

st.title("AI Job Source Agent")

st.write(
    "Extracts company information from LinkedIn or company career pages, "
    "finds the company's careers page, and returns one open position URL."
)

input_mode = st.radio(
    "Choose input mode",
    [
        "Universal URL Mode",
        "LinkedIn Company Page URL",
        "LinkedIn Jobs Listing or Post URL",
        "Company Website URL",
        "Company Careers or Job Page URL"
    ]
)


def is_linkedin_url(url):
    if not url:
        return False

    parsed = urlparse(url)
    return "linkedin.com" in parsed.netloc.lower()


def is_linkedin_company_url(url):
    if not url:
        return False

    parsed = urlparse(url)
    path = parsed.path.lower()

    return "linkedin.com" in parsed.netloc.lower() and "/company/" in path


def is_linkedin_jobs_url(url):
    if not url:
        return False

    parsed = urlparse(url)
    path = parsed.path.lower()

    return "linkedin.com" in parsed.netloc.lower() and "/jobs" in path


def convert_company_url_to_jobs_url(company_url):
    company_url = company_url.strip()

    if company_url.endswith("/"):
        company_url = company_url[:-1]

    if "/jobs" in company_url:
        return company_url + "/"

    return company_url + "/jobs/"


def build_linkedin_search_url(target_company):
    encoded_company = quote_plus(target_company.strip())
    return f"https://www.linkedin.com/jobs/search/?keywords={encoded_company}&location=United%20States"


def show_result(result):
    st.subheader("Final Agent Result")

    df = pd.DataFrame([result])
    st.dataframe(df, use_container_width=True)

    csv_data = df.to_csv(index=False)

    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name="job_source_result.csv",
        mime="text/csv"
    )

    st.write("### Required Output")
    st.write("Company Name:", result.get("company_name"))
    st.write("Career Page URL:", result.get("career_page_url"))
    st.write("Open Position URL:", result.get("open_position_url"))

    st.write("### Extra Debug Info")
    st.write("Company Website:", result.get("company_website"))
    st.write("LinkedIn Job URL:", result.get("linkedin_job_url"))
    st.write("LinkedIn Status:", result.get("linkedin_status"))
    st.write("Job Title From LinkedIn:", result.get("job_title_from_linkedin"))
    st.write("Company LinkedIn URL:", result.get("company_linkedin_url"))
    st.write("Status:", result.get("status"))


def linkedin_info_is_usable(linkedin_info):
    company_name = linkedin_info.get("company_name")
    company_website = linkedin_info.get("company_website")

    return bool(company_name and company_website)


def run_linkedin_pipeline_once(linkedin_url, target_company, label):
    st.write(f"Trying LinkedIn source: **{label}**")
    st.write(linkedin_url)

    with st.spinner("Extracting company info from LinkedIn through Apify..."):
        linkedin_info = extract_linkedin_job_info(
            linkedin_url,
            count=100,
            target_company=target_company
        )

    st.subheader(f"LinkedIn Extraction Result: {label}")

    st.json(
        {
            "company_name": linkedin_info.get("company_name"),
            "company_website": linkedin_info.get("company_website"),
            "company_linkedin_url": linkedin_info.get("company_linkedin_url"),
            "job_title": linkedin_info.get("job_title"),
            "linkedin_job_url": linkedin_info.get("linkedin_job_url"),
            "linkedin_status": linkedin_info.get("linkedin_status"),
        }
    )

    return linkedin_info


def urls_are_same(url1, url2):
    if not url1 or not url2:
        return False

    return url1.rstrip("/") == url2.rstrip("/")


def finish_linkedin_result(linkedin_info):
    company_name = linkedin_info.get("company_name")
    company_website = linkedin_info.get("company_website")
    linkedin_job_url = linkedin_info.get("linkedin_job_url")

    with st.spinner("Finding careers page and open position URL..."):
        result = run_agent(company_name, company_website)

    result["linkedin_job_url"] = linkedin_job_url
    result["linkedin_status"] = linkedin_info.get("linkedin_status")
    result["job_title_from_linkedin"] = linkedin_info.get("job_title")
    result["company_linkedin_url"] = linkedin_info.get("company_linkedin_url")

    if urls_are_same(result.get("career_page_url"), result.get("open_position_url")):
        result["open_position_url"] = None
        result["status"] = "career page found, no separate company job link found"

    if not result.get("open_position_url") and linkedin_job_url:
        result["open_position_url"] = linkedin_job_url

        if result.get("career_page_url"):
            result["status"] = "career page found, used LinkedIn job URL fallback"
        else:
            result["status"] = "career page not found, used LinkedIn job URL fallback"

        st.warning(
            "The company careers page did not expose a separate job posting URL, so the agent used "
            "the LinkedIn job URL from the LinkedIn crawler result."
        )

    show_result(result)


def run_linkedin_pipeline(linkedin_url, target_company):
    linkedin_info = run_linkedin_pipeline_once(
        linkedin_url,
        target_company,
        "primary LinkedIn URL"
    )

    if linkedin_info_is_usable(linkedin_info):
        finish_linkedin_result(linkedin_info)
        return

    if is_linkedin_company_url(linkedin_url) and target_company:
        search_url = build_linkedin_search_url(target_company)

        st.warning(
            "The LinkedIn company jobs page did not return usable data. "
            "Trying a LinkedIn jobs search URL built from the target company name."
        )

        linkedin_info = run_linkedin_pipeline_once(
            search_url,
            target_company,
            "fallback LinkedIn jobs search URL"
        )

        if linkedin_info_is_usable(linkedin_info):
            finish_linkedin_result(linkedin_info)
            return

    st.error(
        "LinkedIn extraction did not return both company name and company website. "
        "Try a LinkedIn jobs search/post URL, a company website URL, or a direct careers/job page URL."
    )


def run_universal_pipeline(input_url, target_company):
    input_url = input_url.strip()

    if is_linkedin_company_url(input_url):
        jobs_url = convert_company_url_to_jobs_url(input_url)

        st.write("Detected input type: **LinkedIn company page**")
        st.write("Converted LinkedIn jobs URL:", jobs_url)

        run_linkedin_pipeline(jobs_url, target_company)
        return

    if is_linkedin_jobs_url(input_url):
        st.write("Detected input type: **LinkedIn jobs listing/post URL**")
        run_linkedin_pipeline(input_url, target_company)
        return

    if is_linkedin_url(input_url):
        st.error(
            "This LinkedIn URL is not recognized as a company page or jobs URL. "
            "Use a LinkedIn company page, jobs search URL, or job post URL."
        )
        return

    if looks_like_job_or_career_page(input_url):
        st.write("Detected input type: **company careers/job page**")

        with st.spinner("Scanning company careers/job page..."):
            result = run_direct_page_agent(target_company, input_url)

        result["linkedin_job_url"] = None
        result["linkedin_status"] = "Skipped: universal direct company careers/job page mode"
        result["job_title_from_linkedin"] = None
        result["company_linkedin_url"] = None

        show_result(result)
        return

    st.write("Detected input type: **company website**")

    with st.spinner("Finding careers page and open position URL..."):
        result = run_agent(target_company, input_url)

    result["linkedin_job_url"] = None
    result["linkedin_status"] = "Skipped: universal company website mode"
    result["job_title_from_linkedin"] = None
    result["company_linkedin_url"] = None

    show_result(result)


if input_mode == "Universal URL Mode":
    input_url = st.text_input(
        "Paste any supported URL",
        value="https://www.linkedin.com/company/stripe/"
    )

    target_company = st.text_input(
        "Target Company Name",
        value="Stripe"
    )

    st.info(
        "Supported inputs: LinkedIn company page, LinkedIn jobs page, LinkedIn job post, "
        "company website, company careers page, or company job post URL."
    )

    if st.button("Run Universal Agent"):
        run_universal_pipeline(input_url, target_company)


if input_mode == "LinkedIn Company Page URL":
    company_url = st.text_input(
        "LinkedIn Company Page URL",
        value="https://www.linkedin.com/company/stripe/"
    )

    target_company = st.text_input(
        "Target Company Name",
        value="Stripe"
    )

    st.info(
        "Paste a LinkedIn company profile URL. The app converts it to the company's LinkedIn jobs page, "
        "then falls back to a LinkedIn jobs search URL if needed."
    )

    if st.button("Run Company Page Agent"):
        jobs_url = convert_company_url_to_jobs_url(company_url)

        st.write("Converted LinkedIn Jobs URL:", jobs_url)

        run_linkedin_pipeline(jobs_url, target_company)


if input_mode == "LinkedIn Jobs Listing or Post URL":
    linkedin_url = st.text_input(
        "LinkedIn Jobs Listing/Search/Post URL",
        value="https://www.linkedin.com/jobs/search/?keywords=software%20engineer%20Stripe&location=United%20States"
    )

    target_company = st.text_input(
        "Target Company Name",
        value="Stripe"
    )

    st.info("Use a LinkedIn jobs search, company jobs, or job post URL.")

    if st.button("Run LinkedIn Job Source Agent"):
        run_linkedin_pipeline(linkedin_url, target_company)


if input_mode == "Company Website URL":
    company_name = st.text_input("Company Name", value="Stripe")
    company_website = st.text_input("Company Website URL", value="https://stripe.com")

    st.info(
        "Use this when you already know the company's main website. "
        "The app will find the careers page and one job URL."
    )

    if st.button("Run Company Website Agent"):
        with st.spinner("Finding careers page and open position URL..."):
            result = run_agent(company_name, company_website)

        result["linkedin_job_url"] = None
        result["linkedin_status"] = "Skipped: company website mode"
        result["job_title_from_linkedin"] = None
        result["company_linkedin_url"] = None

        show_result(result)


if input_mode == "Company Careers or Job Page URL":
    company_name = st.text_input("Company Name", value="Lockheed Martin")
    job_page_url = st.text_input(
        "Company Careers or Job Page URL",
        value="https://www.lockheedmartinjobs.com/"
    )

    st.info(
        "Use this when you already have a company careers page or specific job page. "
        "The app will scan it and return one job URL."
    )

    if st.button("Run Direct Careers Page Agent"):
        with st.spinner("Scanning company careers/job page..."):
            result = run_direct_page_agent(company_name, job_page_url)

        result["linkedin_job_url"] = None
        result["linkedin_status"] = "Skipped: direct company careers/job page mode"
        result["job_title_from_linkedin"] = None
        result["company_linkedin_url"] = None

        show_result(result)