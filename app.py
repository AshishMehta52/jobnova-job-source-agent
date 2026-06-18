import streamlit as st
import pandas as pd

from agent import run_agent
from linkedin_extractor import extract_linkedin_job_info


st.set_page_config(page_title="AI Job Source Agent", layout="wide")

st.title("AI Job Source Agent")

st.write(
    "Extracts company information from a LinkedIn jobs listing page, "
    "finds the company's careers page, and returns one open position URL."
)

input_mode = st.radio(
    "Choose input mode",
    ["LinkedIn Jobs Listing URL", "Company Website Test Mode"]
)


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


if input_mode == "LinkedIn Jobs Listing URL":
    linkedin_url = st.text_input(
        "LinkedIn Jobs Listing/Search URL",
        value="https://www.linkedin.com/jobs/search/?keywords=software%20engineer%20Stripe&location=United%20States"
    )

    target_company = st.text_input(
        "Target Company Name",
        value="Stripe"
    )

    st.info(
        "Use a LinkedIn jobs search/listing URL. The target company field prevents the agent "
        "from choosing the wrong company when LinkedIn returns multiple search results."
    )

    if st.button("Run LinkedIn Job Source Agent"):
        with st.spinner("Extracting company info from LinkedIn through Apify..."):
            linkedin_info = extract_linkedin_job_info(
                linkedin_url,
                count=50,
                target_company=target_company
            )

        st.subheader("LinkedIn Extraction Result")

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

        company_name = linkedin_info.get("company_name")
        company_website = linkedin_info.get("company_website")

        if not company_name or not company_website:
            st.error(
                "LinkedIn extraction did not return both company name and company website. "
                "Use a more specific LinkedIn jobs URL or change the target company."
            )
        else:
            with st.spinner("Finding careers page and open position URL..."):
                result = run_agent(company_name, company_website)

            result["linkedin_job_url"] = linkedin_info.get("linkedin_job_url")
            result["linkedin_status"] = linkedin_info.get("linkedin_status")
            result["job_title_from_linkedin"] = linkedin_info.get("job_title")
            result["company_linkedin_url"] = linkedin_info.get("company_linkedin_url")

            if not result.get("open_position_url") and linkedin_info.get("linkedin_job_url"):
                result["open_position_url"] = linkedin_info.get("linkedin_job_url")
                result["status"] = "career page found, used LinkedIn job URL fallback"

            show_result(result)


if input_mode == "Company Website Test Mode":
    st.warning(
        "This mode is only for testing the second half of the pipeline. "
        "The real challenge flow should use LinkedIn Jobs Listing URL mode."
    )

    company_name = st.text_input("Company Name", value="Stripe")
    company_website = st.text_input("Company Website URL", value="https://stripe.com")

    if st.button("Run Website Test Agent"):
        with st.spinner("Searching for career page and open position..."):
            result = run_agent(company_name, company_website)

        result["linkedin_job_url"] = None
        result["linkedin_status"] = "Skipped: company website test mode"
        result["job_title_from_linkedin"] = None
        result["company_linkedin_url"] = None

        show_result(result)