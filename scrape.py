"""Scrape job postings from applyjobs.spac.gov.jo and write a JSON feed.

Usage:
  python scrape.py              # one-time scrape to data/jobs.json
  python scrape.py --interval 1800  # scrape every 30 minutes
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://applyjobs.spac.gov.jo"
LIST_URL = f"{BASE_URL}/"

DETAIL_PATTERN = re.compile(r"JobDet\.aspx\?JobID=(\d+)")


@dataclass
class JobRecord:
    job_id: str
    title: str
    organization: str
    vacancy_spec: str
    experience_text: str
    experience_raw: str
    start_date: Optional[str]
    end_date: Optional[str]
    qualification: str
    location: str
    gender: str
    age: str
    vacancies: Optional[int]
    salary: Optional[float]
    requirements: str
    announcement_pdf: Optional[str]
    description_pdf: Optional[str]
    detail_url: str
    status: str
    scraped_at: str


def fetch(session: requests.Session, url: str) -> str:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_job_ids(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    job_ids: list[str] = []
    for anchor in soup.find_all("a", href=True):
        match = DETAIL_PATTERN.search(anchor["href"])
        if match:
            job_ids.append(match.group(1))
    # Preserve order while removing duplicates
    seen = set()
    unique_ids = []
    for job_id in job_ids:
        if job_id not in seen:
            seen.add(job_id)
            unique_ids.append(job_id)
    return unique_ids


def parse_list_experience_map(html: str) -> dict[str, str]:
    """Capture raw experience text from the listing page rows."""
    soup = BeautifulSoup(html, "html.parser")
    mapping: dict[str, str] = {}

    for link in soup.find_all("a", href=True):
        match = DETAIL_PATTERN.search(link["href"])
        if not match:
            continue
        job_id = match.group(1)
        tr = link.find_parent("tr")
        cursor = tr
        # Walk forward until we find the row containing the experience snippet or we hit the next job header.
        while cursor:
            cursor = cursor.find_next_sibling("tr")
            if cursor is None:
                break
            if cursor.find("a", href=DETAIL_PATTERN):
                break
            cells = cursor.find_all("td")
            for td in cells:
                text = " ".join(td.stripped_strings)
                if "خبرة فنية في مجال الوظيفة" in text:
                    # Keep raw text after the colon if present.
                    parts = text.split(":", 1)
                    raw_val = parts[1].strip() if len(parts) > 1 else text.strip()
                    mapping[job_id] = raw_val
                    cursor = None  # exit outer loop
                    break
    return mapping


def text_from_id(soup: BeautifulSoup, element_id: str) -> str:
    el = soup.find(id=element_id)
    if not el:
        return ""
    return " ".join(el.stripped_strings)


def multiline_text(soup: BeautifulSoup, element_id: str) -> str:
    el = soup.find(id=element_id)
    if not el:
        return ""
    return "\n".join(part.strip() for part in el.stripped_strings if part.strip())


def parse_int(value: str) -> Optional[int]:
    try:
        return int(value.strip())
    except Exception:
        return None


def parse_float(value: str) -> Optional[float]:
    try:
        return float(value.replace(",", "").strip())
    except Exception:
        return None


def parse_date(value: str) -> Optional[str]:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date().isoformat()
    except Exception:
        return None


def absolute_href(href: str) -> str:
    normalized = href.replace("\\", "/")
    if normalized.startswith("http"):
        return normalized
    if normalized.startswith("../"):
        normalized = normalized[3:]
    normalized = normalized.lstrip("./")
    normalized = normalized.lstrip("/")
    return f"{BASE_URL}/{normalized}"


def link_from_id(soup: BeautifulSoup, element_id: str) -> Optional[str]:
    container = soup.find(id=element_id)
    if not container:
        return None
    link = container.find("a")
    if link and link.get("href"):
        return absolute_href(link["href"])
    return None


def determine_status(end_date: Optional[str]) -> str:
    if not end_date:
        return "unknown"
    try:
        deadline = date.fromisoformat(end_date)
    except ValueError:
        return "unknown"
    return "open" if deadline >= date.today() else "closed"


def parse_job_detail(job_id: str, html: str) -> JobRecord:
    soup = BeautifulSoup(html, "html.parser")
    title = text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblJobTitle")
    organization = text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblChapt").strip(" /")
    vacancy_spec = text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblVacType")
    experience_text = text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblMinTechExp")
    start_date = parse_date(text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblJobPubDate"))
    end_date = parse_date(text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblJobEndDate"))
    qualification = text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblCertName")
    location = text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblGoverName")
    gender = text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblGender")
    age = text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblAgeDesc")
    vacancies = parse_int(text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblVacNo"))
    salary = parse_float(text_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblSal"))
    requirements = multiline_text(soup, "ContentPlaceHolder1_PubJobDetControl1_lblJobReqDet")
    announcement_pdf = link_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblJobTitleURL")
    description_pdf = link_from_id(soup, "ContentPlaceHolder1_PubJobDetControl1_lblJobDescURL")

    detail_url = f"{BASE_URL}/JobDet.aspx?JobID={job_id}"
    status = determine_status(end_date)

    return JobRecord(
        job_id=job_id,
        title=title,
        organization=organization,
        vacancy_spec=vacancy_spec,
        experience_text=experience_text,
        experience_raw=experience_text,
        start_date=start_date,
        end_date=end_date,
        qualification=qualification,
        location=location,
        gender=gender,
        age=age,
        vacancies=vacancies,
        salary=salary,
        requirements=requirements,
        announcement_pdf=announcement_pdf,
        description_pdf=description_pdf,
        detail_url=detail_url,
        status=status,
        scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def scrape_once(session: requests.Session) -> dict:
    list_html = fetch(session, LIST_URL)
    job_ids = parse_job_ids(list_html)
    list_experience = parse_list_experience_map(list_html)
    jobs: list[JobRecord] = []

    for job_id in job_ids:
        detail_html = fetch(session, f"{BASE_URL}/JobDet.aspx?JobID={job_id}")
        job = parse_job_detail(job_id, detail_html)
        if job_id in list_experience:
            list_val = list_experience[job_id]
            if list_val:
                job.experience_text = list_val
                job.experience_raw = list_val
            else:
                job.experience_raw = job.experience_text
        jobs.append(job)

    payload = {
        "source": LIST_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "job_count": len(jobs),
        "jobs": [asdict(job) for job in jobs],
    }
    return payload


def write_json(payload: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape applyjobs.spac.gov.jo job postings.")
    parser.add_argument("--interval", type=int, help="Seconds between scrapes (if set, runs forever).")
    parser.add_argument("--output", type=Path, default=Path("data/jobs.json"), help="Where to write JSON.")
    args = parser.parse_args()

    session = requests.Session()

    while True:
        payload = scrape_once(session)
        write_json(payload, args.output)
        print(f"Wrote {payload['job_count']} jobs to {args.output} at {payload['scraped_at']}")

        if not args.interval:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
