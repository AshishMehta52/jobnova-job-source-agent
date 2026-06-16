import streamlit as st
import pandas as pd
from agent import run_agent


st.set_page_config(page_title="AI Job Source Agent", layout="wide")

st.title("AI Job Source Agent")
st.write("Finds a company's careers page and one open job posting URL.")

company_name = st.text_input("Company Name", value="Stripe")
company_website = st.text_input("Company Website URL", value="https://stripe.com")

if st.button("Run Agent"):
    with st.spinner("Searching for career page and open position..."):
        result = run_agent(company_name, company_website)

    st.subheader("Result")

    df = pd.DataFrame([result])
    st.dataframe(df, use_container_width=True)

    csv_data = df.to_csv(index=False)

    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name="job_source_result.csv",
        mime="text/csv"
    )

    st.write("### Agent Output")
    st.write("Company Name:", result["company_name"])
    st.write("Company Website:", result["company_website"])
    st.write("Career Page URL:", result["career_page_url"])
    st.write("Open Position URL:", result["open_position_url"])
    st.write("Status:", result["status"])