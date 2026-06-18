# AI Job Source Agent

This project implements Part 2 of the Jobnova AI Engineer take-home challenge.

The agent starts from a LinkedIn jobs listing/search URL, extracts company information using a third-party LinkedIn crawler API, navigates from the company website to the careers page, extracts one open position URL, and returns the result in the required format.

## Required Output

- Company name
- Career page URL
- Open position URL

## Workflow

1. User enters a LinkedIn jobs listing/search URL.
2. The app sends the URL to an Apify LinkedIn Jobs Scraper actor.
3. The actor returns structured job data, including company name and company website when available.
4. The agent visits the company website.
5. The agent finds the careers page.
6. The agent extracts one open position URL.
7. The app returns the final result in a table and downloadable CSV.

## Note

The challenge allows the use of a third-party LinkedIn crawler API. This demo uses Apify for LinkedIn extraction because direct LinkedIn scraping is often restricted or blocked.