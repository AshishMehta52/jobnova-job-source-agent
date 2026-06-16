# jobnova-job-source-agent

I am making this project for Jobnova's AI Engineer take-home challenge.

The agent takes a company website or job listing input, finds the company's careers page, extracts one open job posting URL, and returns the result in a structured format.

Output format:
- Company name
- Career page URL
- Open position URL

Agent progress:
- Success handling when a job URL is found
- Partial-success handling when only the career page is found
- Failure handling when no career page is found
- Requests-first crawling
- Playwright fallback for dynamic pages
- CSV export through Streamlit