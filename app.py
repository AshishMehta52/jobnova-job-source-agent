import streamlit as st
import pandas as pd
from urllib.parse import urlparse, quote_plus

from agent import run_agent, run_direct_page_agent
from crawler import looks_like_job_or_career_page
from linkedin_extractor import extract_linkedin_job_info


st.set_page_config(page_title="AI Job Source Agent", layout="wide")

st.title("AI Job Source Agent")

st.write(
    "Enter a LinkedIn company page, LinkedIn job listing, company website, "
    "or company careers page. The agent returns the company name, careers page URL, "
    "and one open position URL."
)

input_url = st.text_input(
    "Input URL",
    value="https://www.linkedin.com/company/stripe/"
)

target_company = st.text_input(
    "Company Name",
    value="Stripe"
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


def build_linkedin_search_url(company_name):
    encoded_company = quote_plus(company_name.strip())
    return f"https://www.linkedin.com/jobs/search/?keywords={encoded_company}&location=United%20States"


def urls_are_same(url1, url2):
    if not url1 or not url2:
        return False

    return url1.rstrip("/") == url2.rstrip("/")


def linkedin_info_is_usable(linkedin_info):
    company_name = linkedin_info.get("company_name")
    company_website = linkedin_info.get("company_website")

    return bool(company_name and company_website)


def clean_final_result(result):
    return {
        "company_name": result.get("company_name"),
        "career_page_url": result.get("career_page_url"),
        "open_position_url": result.get("open_position_url")
    }


def show_result(result):
    final_result = clean_final_result(result)

    st.subheader("Result")

    df = pd.DataFrame([final_result])
    st.dataframe(df, use_container_width=True)

    csv_data = df.to_csv(index=False)

    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name="job_source_result.csv",
        mime="text/csv"
    )


def finish_linkedin_result(linkedin_info):
    company_name = linkedin_info.get("company_name")
    company_website = linkedin_info.get("company_website")
    linkedin_job_url = linkedin_info.get("linkedin_job_url")

    result = run_agent(company_name, company_website)

    if urls_are_same(result.get("career_page_url"), result.get("open_position_url")):
        result["open_position_url"] = None

    if not result.get("open_position_url") and linkedin_job_url:
        result["open_position_url"] = linkedin_job_url

    show_result(result)


def run_linkedin_pipeline(linkedin_url, company_name):
    linkedin_info = extract_linkedin_job_info(
        linkedin_url,
        count=25,
        target_company=company_name
    )

    if linkedin_info_is_usable(linkedin_info):
        finish_linkedin_result(linkedin_info)
        return

    fallback_search_url = build_linkedin_search_url(company_name)

    linkedin_info = extract_linkedin_job_info(
        fallback_search_url,
        count=25,
        target_company=company_name
    )

    if linkedin_info_is_usable(linkedin_info):
        finish_linkedin_result(linkedin_info)
        return

    st.error(
        "The agent could not extract enough company information from this source. "
        "Try a LinkedIn jobs listing URL, company website, or direct careers page."
    )


def run_universal_agent(url, company_name):
    url = url.strip()

    if is_linkedin_company_url(url):
        linkedin_jobs_url = convert_company_url_to_jobs_url(url)
        run_linkedin_pipeline(linkedin_jobs_url, company_name)
        return

    if is_linkedin_jobs_url(url):
        run_linkedin_pipeline(url, company_name)
        return

    if is_linkedin_url(url):
        st.error(
            "This LinkedIn URL is not supported. Use a LinkedIn company page, "
            "LinkedIn jobs listing, or LinkedIn job post URL."
        )
        return

    if looks_like_job_or_career_page(url):
        result = run_direct_page_agent(company_name, url)

        if urls_are_same(result.get("career_page_url"), result.get("open_position_url")):
            result["open_position_url"] = None

        if not result.get("open_position_url"):
            result["open_position_url"] = url

        show_result(result)
        return

    result = run_agent(company_name, url)

    if urls_are_same(result.get("career_page_url"), result.get("open_position_url")):
        result["open_position_url"] = None

    show_result(result)


if st.button("Run Agent"):
    with st.spinner("Running agent..."):
        run_universal_agent(input_url, target_company)