from crawler import find_career_page, find_open_position


def run_agent(company_name, company_website):
    career_page_url = find_career_page(company_website)

    if career_page_url:
        open_position_url = find_open_position(career_page_url)
        status = "success" if open_position_url else "career page found, no job link found"
    else:
        open_position_url = None
        status = "career page not found"

    return {
        "company_name": company_name,
        "company_website": company_website,
        "career_page_url": career_page_url,
        "open_position_url": open_position_url,
        "status": status
    }


if __name__ == "__main__":
    company_name = "Stripe"
    company_website = "https://stripe.com"

    result = run_agent(company_name, company_website)

    print("\nAI Job Source Agent Result")
    print("--------------------------")
    print("Company Name:", result["company_name"])
    print("Company Website:", result["company_website"])
    print("Career Page URL:", result["career_page_url"])
    print("Open Position URL:", result["open_position_url"])
    print("Status:", result["status"])