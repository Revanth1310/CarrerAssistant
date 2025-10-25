import os
import urllib
import asyncio
import aiohttp
import requests
import json
from typing import List, Literal, Union, Optional
from asgiref.sync import sync_to_async
from linkedin_api import Linkedin
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
#----------------------------------- WEB SCRAPING USING SERPER & FIRECRAWL APIS ------------------------------------------#
def firecrawl_scrape(url: str) -> str:
    if not FIRECRAWL_API_KEY:
        return "Firecrawl API key not set."
    try:
        api = "https://api.firecrawl.dev/v2/scrape"
        headers = {
            "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {"url": url, "formats": ["markdown"]}
        resp = requests.post(api, headers=headers, json=body, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("markdown", "") or ""
    except Exception as e:
        # fallback: gentle requests.get (obey site rules yourself)
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            r.raise_for_status()
            # limit size to avoid huge responses
            return r.text[:20000]
        except Exception as e2:
            return f"Firecrawl error: {str(e)}; fallback error: {str(e2)}"
def get_pages_content(query: str, top_n: int = 3) -> dict:
    if not SERPER_API_KEY:
        return {"error": "SERPER_API_KEY is not set."}
    search_url = "https://google.serper.dev/search"
    payload = {"q": query, "location": "India"}
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    try:
        res = requests.post(search_url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        data = res.json()
        links = [r.get("link") for r in data.get("organic", []) if r.get("link")]
        links = links[:top_n]
    except Exception as e:
        return {"error": f"Serper search error: {str(e)}"}

    pages = {}
    for link in links:
        pages[link] = firecrawl_scrape(link)
    return pages

#------------------------------------------LINKEDIN JOB SEARCH ------------------------------------------#
employment_type_mapping = {
    "full-time": "F", "contract": "C", "part-time": "P", "temporary": "T",
    "internship": "I", "volunteer": "V", "other": "O"
}
experience_type_mapping = {
    "internship": "1", "entry-level": "2", "associate": "3",
    "mid-senior-level": "4", "director": "5", "executive": "6"
}
job_type_mapping = {"onsite": "1", "remote": "2", "hybrid": "3"}

def build_linkedin_job_url(keywords, location=None, employment_type=None, experience_level=None, job_type=None):
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search/"
    query_params = {"keywords": keywords}
    if location:
        query_params["location"] = location
    if employment_type:
        if isinstance(employment_type, str):
            employment_type = [employment_type]
        query_params["f_WT"] = ",".join(employment_type)
    if experience_level:
        if isinstance(experience_level, str):
            experience_level = [experience_level]
        query_params["f_E"] = ",".join(experience_level)
    if job_type:
        if isinstance(job_type, str):
            job_type = [job_type]
        query_params["f_JT"] = ",".join(job_type)
    query_string = urllib.parse.urlencode(query_params)
    return f"{base_url}?{query_string}&sortBy=R"

def get_job_ids(keywords: str, location_name: str, limit: int = 10, employment_type: Optional[List[str]] = None, job_type: Optional[List[str]] = None, experience: Optional[List[str]] = None):
    # Prefer linkedin_api if env flag is set
    if os.environ.get("LINKEDIN_SEARCH") == "linkedin_api":
        try:
            api = Linkedin(os.getenv("LINKEDIN_EMAIL"), os.getenv("LINKEDIN_PASS"))
            job_postings = api.search_jobs(
                keywords=keywords, job_type=employment_type, location_name=location_name,
                remote=job_type, limit=limit, experience=experience
            )
            job_ids = [job["trackingUrn"].split("jobPosting:")[1] for job in job_postings if "trackingUrn" in job]
            return job_ids[:limit]
        except Exception as e:
            print(f"LinkedIn API error: {e}")
            return []

    # Fallback scraping of guest endpoint
    try:
        job_url = build_linkedin_job_url(keywords, location_name, employment_type, experience, job_type)
        response = requests.get(job_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        list_soup = BeautifulSoup(response.text, "html.parser")
        page_jobs = list_soup.find_all("li")
        job_ids = []
        for job in page_jobs:
            base_card_div = job.find("div", {"class": "base-card"})
            if base_card_div and base_card_div.get("data-entity-urn"):
                parts = base_card_div.get("data-entity-urn").split(":")
                if len(parts) >= 4:
                    job_ids.append(parts[3])
        return job_ids[:limit]
    except Exception as e:
        print(f"Error fetching job ids from LinkedIn: {e}")
        return []

# Async fetch of each job details from guest job endpoint
async def fetch_job_details(session, job_id: str) -> dict:
    job_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    job_post = {}
    try:
        async with session.get(job_url, timeout=30) as resp:
            text = await resp.text()
            job_soup = BeautifulSoup(text, "html.parser")
            job_post["job_title"] = (job_soup.find("h2") or {}).get_text(strip=True) if job_soup.find("h2") else ""
            job_post["company_name"] = (job_soup.find("a", {"class": "topcard__org-name-link"}) or {}).get_text(strip=True) if job_soup.find("a", {"class": "topcard__org-name-link"}) else ""
            desc_tag = job_soup.find("div", {"class": "decorated-job-posting__details"})
            job_post["job_desc_text"] = desc_tag.get_text("\n", strip=True) if desc_tag else ""
            apply_link_tag = job_soup.find("a", class_="topcard__link")
            job_post["apply_link"] = apply_link_tag.get("href") if apply_link_tag else job_url
    except Exception as e:
        job_post["error"] = str(e)
    return job_post

async def fetch_all_jobs_async(job_ids: List[str]) -> List[dict]:
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_job_details(session, jid) for jid in job_ids]
        results = await asyncio.gather(*tasks)
    return results