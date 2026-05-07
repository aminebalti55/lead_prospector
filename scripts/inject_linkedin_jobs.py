"""One-shot: parse the LinkedIn MCP search dumps + inject as opportunities.

We pass the raw search-results text as a list of strings; the parser walks
the text in order, picking out (title, company, location, age, easy_apply)
tuples. Job IDs come from the parallel job_ids arrays returned by the MCP.

Each job gets stored as a `direct` opportunity, `lead_subtype='hiring'`,
with a stable `id = sha1("linkedin|<canonical-url>")`.
"""
from __future__ import annotations

import hashlib
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.supabase_client import get_client


# ---------------------------------------------------------------------------
# Raw inputs from the 6 LinkedIn searches.
# ---------------------------------------------------------------------------
# Each entry: (search_label, job_ids_in_order, raw_results_text)
# We only inject the union of job_ids; the text gives us enrichment.

SEARCHES = [
    ("software engineer", [
        "4409781810","4410484205","4409254221","4408803738","4409243840","4408994417",
        "4410456811","4411416908","4409227836","4390340773","4411201890","4409244429",
        "4411431154","4411216714","4411213208","4411215006","4409508232","4408894049",
        "4410988392","4408859444","4408874024","4400763990","4411414518","4401783989",
        "4382293095","4410992032","4390569541","4409929277","4378882779","4408497263",
        "4408800217","4408456652","4410742602",
    ]),
    ("next.js react developer", [
        "4409781810","4410484205","4409254221","4408803738","4409243840","4410456811",
        "4409227836","4409774976","4408497263","4408800217","4409244429","4411431154",
        "4411216714","4401783989","4410992032","4400708889","4304224854","4408660289",
        "4376308230","4408624896","4182016523","4411414518","4409798890","4408860426",
        "4408811562","4410709162","4410702183","4410592565","4407600501","4406555640",
        "4407345771",
    ]),
    ("ingénieur logiciel", [
        "4409781810","4410484205","4409254221","4408803738","4409243840","4410456811",
        "4409227836","4402277433","4411207076","4409908297","4409244429","4411431154",
        "4411216714","4390581382","4401783989","4410992032","4408874024","4408198630",
        "4370506638","4409336647","4409339558","4411414518","4390570524","4409904193",
        "4408856696","4409923762","4400708889","4286644677","4408660289","4410029433",
        "4376308230","4408624896",
    ]),
    ("développeur fullstack", [
        "4409781810","4410484205","4409254221","4408803738","4409243840","4410456811",
        "4409227836","4409923762","4408849096","4401345692","4409774976","4409244429",
        "4411431154","4411216714","4401783989","4410992032","4400708889","4408497263",
        "4410079310","4410040528","4408666019","4233375974","4411414518","4409798890",
        "4408860426","4408811562","4410709162","4410702183","4322593565","4407600501",
        "4406555640","4407345771","4407341566",
    ]),
    ("fullstack developer", [
        "4409781810","4410484205","4409254221","4408803738","4409243840","4410456811",
        "4409227836","4401345692","4409774976","4408497263","4409244429","4411431154",
        "4411216714","4401783989","4410992032","4400708889","4408800217","4304224854",
        "4410021797","4408660289","4376308230","4411414518","4409798890","4408831275",
        "4408811562","4410709162","4410702183","4410295731","4401435100","4407600501",
        "4406555640","4407345771",
    ]),
    ("développeur web", [
        "4409781810","4410484205","4409254221","4408803738","4409243840","4410456811",
        "4409227836","4408849096","4401345692","4409774976","4408497263","4409244429",
        "4411431154","4401783989","4410992032","4408811562","4408800217","4304224854",
        "4411414518","4409904193","4408860426","4400708889","4410709162","4410702183",
        "4322593565",
    ]),
]


# Title + company tuples for every unique job we saw, keyed by id. Pulled
# straight from the raw search-results text so we don't need to call
# get_job_details. Companies + titles only — descriptions stay empty until
# the user clicks through.
JOB_META: dict[str, dict] = {
    "4409781810": {"title": "Backend/Cloud engineer", "company": "Rakam AI", "location": "Tunisia", "remote": "Remote", "age": "28m"},
    "4410484205": {"title": "Senior Java Software Engineer", "company": "Adentis Portugal", "location": "Tunisia", "remote": "Remote", "age": "28m"},
    "4409254221": {"title": "AI Systems & Automation Developer", "company": "BGTS", "location": "EMEA", "remote": "Remote", "age": "44m"},
    "4408803738": {"title": "Senior .NET Developer - Europe, Remote - £300-325/day", "company": "VirtueTech Recruitment Group", "location": "EMEA", "remote": "Remote", "age": "46m"},
    "4409243840": {"title": "Lead Tech- Développeur Applicatif C++ / C# - Temps réel", "company": "SATELIANCE", "location": "Tunis, Tunisia", "remote": "On-site", "age": "1h"},
    "4408994417": {"title": "Healthcare Web Research Specialist", "company": "OpenData Systems", "location": "Tunisia", "remote": "Remote", "age": "1h"},
    "4410456811": {"title": "Software Developer @ SIXT SE", "company": "DEVjobs", "location": "EMEA", "remote": "Remote", "age": "2h"},
    "4411416908": {"title": "Ingénieur Industrialisation F/H - SAFRAN SEATS TUNISIE", "company": "AEROCONTACT", "location": "Soliman, Nabeul, Tunisia", "remote": "On-site", "age": "2h"},
    "4409227836": {"title": "Senior AI Backend Engineer (LLMs & AI Agents)", "company": "Tappz GmbH", "location": "Tunis, Tunisia", "remote": "On-site", "age": "2h"},
    "4390340773": {"title": "Escalation Specialist - French and Italian Language", "company": "TunUp_A Cimpress Company", "location": "Tunis, Tunisia", "remote": "Hybrid", "age": "16h"},
    "4411201890": {"title": "Technicien Support Applicatif H/F", "company": "SEPTEO", "location": "Tunis, Tunisia", "remote": "Remote", "age": "16h"},
    "4409244429": {"title": "Senior Full-Stack Engineer", "company": "Tappz GmbH", "location": "Tunis, Tunisia", "remote": "On-site", "age": "2h"},
    "4411431154": {"title": "Java Web Developer", "company": "E-Solutions", "location": "Tunis, Tunisia", "remote": "On-site", "age": "4h"},
    "4411216714": {"title": "Ruby on Rails Developer", "company": "OnTheGoSystems", "location": "EMEA", "remote": "Remote", "age": "14h"},
    "4411213208": {"title": "Architecte Entreprise", "company": "Amaris Consulting", "location": "Tunis, Tunisia", "remote": "On-site", "age": "15h"},
    "4411215006": {"title": "Mid-level AI Engineer/Data Scientist", "company": "Capgemini Engineering", "location": "Ariana, Tunisia", "remote": "Hybrid", "age": "16h"},
    "4409508232": {"title": "Full Stack Engineer (Freelance)", "company": "LAN DYNAMIC", "location": "Tunisia", "remote": "Remote", "age": "16h"},
    "4408894049": {"title": "Ingénieur Avant-Vente GED & BPM | Tunis", "company": "Dot-IT", "location": "Tunis, Tunisia", "remote": "On-site", "age": "16h"},
    "4410988392": {"title": "Chef de projet", "company": "Sopra Steria", "location": "Tunis, Tunisia", "remote": "On-site", "age": "18h"},
    "4408859444": {"title": "Opportunité Freelance – Réalisation Vidéo 2D", "company": "RedStart Tunisie", "location": "Tunis, Tunisia", "remote": "Hybrid", "age": "19h"},
    "4408874024": {"title": "Software Engineer | Remote", "company": "Crossing Hurdles", "location": "EMEA", "remote": "Remote", "age": "19h"},
    "4400763990": {"title": "Tunisia Senior Reliability Engineer", "company": "RINA", "location": "Tunis, Tunisia", "remote": "Hybrid", "age": "19h"},
    "4411414518": {"title": "DevOps Engineer", "company": "E-Solutions", "location": "Tunis, Tunisia", "remote": "On-site", "age": "5h"},
    "4401783989": {"title": "Fullstack Developer – ETRM / TRMS", "company": "Amaris Consulting", "location": "Tunis, Tunisia", "remote": "On-site", "age": "1d"},
    "4382293095": {"title": "Finance Opération Manager Tunis", "company": "ODDO BHF", "location": "Tunis, Tunisia", "remote": "On-site", "age": "17h"},
    "4410992032": {"title": "Full-Stack Engineer (JSON Schema Developer)", "company": "micro1", "location": "EMEA", "remote": "Remote", "age": "18h"},
    "4390569541": {"title": "Member of Engineering (Pre-training / Data Engineering)", "company": "Poolside", "location": "EMEA", "remote": "Remote", "age": "19h"},
    "4409929277": {"title": "Senior Backend Rust Developer", "company": "Proxify", "location": "EMEA", "remote": "Remote", "age": "19h"},
    "4378882779": {"title": "Contrôleur de gestion industriel / Comptable Stäubli BIZERTE H/F", "company": "STÄUBLI", "location": "Bizerte, Tunisia", "remote": "On-site", "age": "19h"},
    "4408497263": {"title": "DevOps Engineer", "company": "IT Ridge Technologies", "location": "Tunis, Tunisia", "remote": "Hybrid", "age": "1d"},
    "4408800217": {"title": "DevOps Engineer", "company": "Zensar Technologies", "location": "Tunis, Tunisia", "remote": "Hybrid", "age": "1d"},
    "4408456652": {"title": "Monteur Vidéo", "company": "Teliosa", "location": "Tunisia", "remote": "Remote", "age": "1d"},
    "4410742602": {"title": "Chargé Développement des Compétences H/F F/H - SAFRAN", "company": "AEROCONTACT", "location": "Soliman, Nabeul, Tunisia", "remote": "On-site", "age": "1d"},
    "4409774976": {"title": "Junior Frontend Developer", "company": "Linedata", "location": "Tunis, Tunisia", "remote": "On-site", "age": "1d"},
    "4400708889": {"title": "Back End Developer - Python & Go | $80/hr Remote", "company": "Crossing Hurdles", "location": "EMEA", "remote": "Remote", "age": "22h"},
    "4304224854": {"title": "Junior AI Engineer", "company": "Devoteam", "location": "Tunis, Tunisia", "remote": "On-site", "age": "1d"},
    "4408660289": {"title": "Ingénieur.e Développement ASP.NET H/F", "company": "SAGEMCOM", "location": "Ben Arous, Tunisia", "remote": "Remote", "age": "2d"},
    "4376308230": {"title": "Full Stack Developer", "company": "Affi Biotech", "location": "La Marsa, Tunis, Tunisia", "remote": "On-site", "age": "2d"},
    "4408624896": {"title": "Frontend Developer | AI-Augmented Development | React, Next.js, TypeScript", "company": "bid.", "location": "EMEA", "remote": "Remote", "age": "3d"},
    "4182016523": {"title": "Web Developer", "company": "Canonical", "location": "EMEA", "remote": "Remote", "age": "3d"},
    "4409798890": {"title": "Ingénieur Senior Automatisation Cloud & Infrastructures", "company": "Amaris Consulting", "location": "Tunis, Tunisia", "remote": "On-site", "age": "18h"},
    "4408860426": {"title": "Cross-Platform Engine Developer (Cocos2d-x)", "company": "micro1", "location": "EMEA", "remote": "Remote", "age": "19h"},
    "4408811562": {"title": "Software Engineer (ElixirJS) | Remote", "company": "Crossing Hurdles", "location": "EMEA", "remote": "Remote", "age": "22h"},
    "4410709162": {"title": "Lead Front End TypeScript Developer (Healthcare) - H/F", "company": "Orisha", "location": "Tunis, Tunisia", "remote": "On-site", "age": "1d"},
    "4410702183": {"title": "Senior .NET Developer", "company": "Clearscale", "location": "EMEA", "remote": "Remote", "age": "1d"},
    "4410592565": {"title": "Frontend Developer (HTML, CSS)", "company": "micro1", "location": "EMEA", "remote": "Remote", "age": "1d"},
    "4407600501": {"title": "Ingénieur Développement – QML (F/H)", "company": "Sofrecom Tunisie", "location": "Tunis, Tunisia", "remote": "Hybrid", "age": "6d"},
    "4406555640": {"title": "Expert IT Software Engineering", "company": "LEONI TUNISIA", "location": "Sousse, Tunisia", "remote": "On-site", "age": "6d"},
    "4407345771": {"title": "Back-End Developer | Remote", "company": "Crossing Hurdles", "location": "EMEA", "remote": "Remote", "age": "6d"},
    "4402277433": {"title": "Software Engineer, Automotive and Industrial Architecture", "company": "Canonical", "location": "EMEA", "remote": "Remote", "age": "18h"},
    "4411207076": {"title": "Software Engineer - Open 3D Engine (O3DE)", "company": "micro1", "location": "EMEA", "remote": "Remote", "age": "18h"},
    "4409908297": {"title": "Talent Pool - Forum des entreprises ESPRIT – Spring 2026", "company": "SEGULA Technologies", "location": "Tunis, Tunisia", "remote": "On-site", "age": "18h"},
    "4390581382": {"title": "Senior Software Engineer", "company": "LevelUP HCS", "location": "EMEA", "remote": "Remote", "age": "1d"},
    "4408198630": {"title": "Technical Lead C#", "company": "Inetum", "location": "Tunis, Tunisia", "remote": "On-site", "age": "1d"},
    "4370506638": {"title": "(Senior) Software Engineer", "company": "Medius", "location": "Tunis, Tunisia", "remote": "Hybrid", "age": "1d"},
    "4409336647": {"title": "Staff Software Engineer: Consumer (Money)", "company": "Consensys", "location": "EMEA", "remote": "Remote", "age": "1d"},
    "4409339558": {"title": "Member of Engineering (Data Platform Lead)", "company": "Poolside", "location": "EMEA", "remote": "Remote", "age": "16h"},
    "4390570524": {"title": "Test & Qualité 5GC", "company": "Amaris Consulting", "location": "Tunis, Tunisia", "remote": "On-site", "age": "18h"},
    "4409904193": {"title": "Software Developer (C)", "company": "micro1", "location": "MENA", "remote": "Remote", "age": "18h"},
    "4408856696": {"title": "Senior WordPress Developer", "company": "Proxify", "location": "EMEA", "remote": "Remote", "age": "19h"},
    "4409923762": {"title": "Senior WordPress Developer", "company": "Proxify", "location": "EMEA", "remote": "Remote", "age": "19h"},
    "4286644677": {"title": "Senior Fullstack Engineer (Go/TypeScript)", "company": "X-FLOW", "location": "EMEA", "remote": "Remote", "age": "3d"},
    "4410029433": {"title": "Senior Développeur Back-End JAVA 17 ou plus", "company": "Devoteam", "location": "Tunis, Tunisia", "remote": "Remote", "age": "2d"},
    "4408849096": {"title": "Software Engineer", "company": "Stackdrop", "location": "Tunisia", "remote": "Remote", "age": "21h"},
    "4401345692": {"title": "Senior Full-Stack Engineer", "company": "MyEdSpace", "location": "EMEA", "remote": "Remote", "age": "21h"},
    "4410079310": {"title": "IP/MPLS Engineer (BGP / Python)", "company": "Ooredoo Tunisie", "location": "Tunis, Tunisia", "remote": "On-site", "age": "2d"},
    "4410040528": {"title": "Software Engineer", "company": "Aklass Solutions", "location": "EMEA", "remote": "Remote", "age": "2d"},
    "4408666019": {"title": "Game Developer", "company": "NAPHORA GAMES GROUP", "location": "EMEA", "remote": "Remote", "age": "2d"},
    "4233375974": {"title": "Senior Next.js Developer", "company": "Proxify", "location": "EMEA", "remote": "Remote", "age": "2d"},
    "4322593565": {"title": "Senior Data Engineer", "company": "Blauwtrust Tunisia", "location": "Tunis, Tunisia", "remote": "Hybrid", "age": "2d"},
    "4407341566": {"title": "Golang Developer | $80/hr Remote", "company": "Crossing Hurdles", "location": "EMEA", "remote": "Remote", "age": "1w"},
    "4410021797": {"title": "Fullstack Developer", "company": "micro1", "location": "MENA", "remote": "Remote", "age": "2d"},
    "4408831275": {"title": "Software Developer – Cloud ERP (AI-First)", "company": "Everfield", "location": "Tunisia", "remote": "Remote", "age": "1d"},
    "4410295731": {"title": "Junior AI Engineer", "company": "Devoteam", "location": "Tunis, Tunisia", "remote": "On-site", "age": "1d"},
    "4401435100": {"title": "Senior Data Engineer", "company": "Blauwtrust Tunisia", "location": "Tunis, Tunisia", "remote": "Hybrid", "age": "2d"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_age_to_dt(age: str) -> datetime:
    """'2h' / '1d' / '1w' → a real datetime relative to now (UTC)."""
    now = datetime.now(timezone.utc)
    s = age.lower().strip()
    m = re.match(r"(\d+)\s*([smhdw])", s)
    if not m:
        return now
    n = int(m.group(1))
    unit = m.group(2)
    if unit == "m":
        return now - timedelta(minutes=n)
    if unit == "h":
        return now - timedelta(hours=n)
    if unit == "d":
        return now - timedelta(days=n)
    if unit == "w":
        return now - timedelta(weeks=n)
    return now


def stable_id(url: str) -> str:
    return hashlib.sha1(f"linkedin|{url}".encode("utf-8")).hexdigest()


def detect_skills(title: str) -> list[str]:
    """Cheap keyword scan to surface matched skills in the inbox."""
    t = title.lower()
    skills = []
    for k in (
        "react", "next.js", "nextjs", "node", "typescript", "javascript",
        "python", "fastapi", "postgres", "java", "c#", ".net", "go",
        "rust", "elixir", "golang", "devops", "aws", "azure", "gcp",
        "kubernetes", "docker",
    ):
        if k in t:
            skills.append(k)
    return list(dict.fromkeys(skills))


def estimated_value(title: str, location: str) -> int:
    t = title.lower()
    if any(s in t for s in ("senior", "lead", "staff", "principal")):
        return 2500
    if any(s in t for s in ("freelance", "contract", "$", "/hr", "/day")):
        return 2000
    if "remote" in (location or "").lower() or "emea" in (location or "").lower():
        return 1500
    return 1000


def detect_subtype(company: str, title: str) -> str:
    """Recruiting-firm listings → mark as 'agency' so the user knows
    they'll go through a recruiter, not direct to the hiring company."""
    agencies = (
        "virtuetech", "crossing hurdles", "aerocontact", "amaris consulting",
        "e-solutions", "proxify", "micro1", "devjobs",
    )
    c = (company or "").lower()
    if any(a in c for a in agencies):
        return "agency"
    return "hiring"


# ---------------------------------------------------------------------------
# Build rows
# ---------------------------------------------------------------------------


def build_rows() -> list[dict]:
    # Union of all job_ids across the 6 searches.
    seen: set[str] = set()
    union: list[str] = []
    for _, ids in SEARCHES:
        for i in ids:
            if i not in seen:
                seen.add(i)
                union.append(i)

    rows: list[dict] = []
    for jid in union:
        meta = JOB_META.get(jid)
        if not meta:
            continue
        url = f"https://www.linkedin.com/jobs/view/{jid}/"
        title = meta["title"]
        company = meta["company"]
        location = meta["location"]
        if meta.get("remote"):
            location = f"{location} ({meta['remote']})"
        posted = parse_age_to_dt(meta["age"])

        rows.append({
            "id": stable_id(url),
            "type": "direct",
            "source": "linkedin",
            "lead_subtype": detect_subtype(company, title),
            "title": title,
            "description": (
                f"{title} at {company}. Location: {location}. "
                f"Click 'Open original' to view the full posting on LinkedIn."
            ),
            "url": url,
            "posted_date": posted.isoformat(),
            "company_name": company,
            "location": location,
            "score": 50 + (10 if "senior" in title.lower() or "lead" in title.lower() else 0),
            "priority": "warm",
            "stage": "new",
            "estimated_value_usd": estimated_value(title, location),
            "matched_skills": detect_skills(title),
            "budget_signal": "",
            "urgency_signal": "",
            "notes": "Imported from LinkedIn MCP search (past_week, sort=date)",
        })
    return rows


def main():
    rows = build_rows()
    print(f"Built {len(rows)} unique LinkedIn job rows")

    if not rows:
        return

    client = get_client()
    # Insert in chunks of 50
    for i in range(0, len(rows), 50):
        chunk = rows[i:i + 50]
        client.table("opportunities").upsert(chunk, on_conflict="id").execute()
        print(f"  upserted {i+len(chunk)}/{len(rows)}")

    # Quick verification
    resp = client.table("opportunities").select("id", count="exact").eq("source", "linkedin").execute()
    print(f"\nLinkedIn opportunities now in DB: {resp.count}")


if __name__ == "__main__":
    main()
