"""Shared data access for the CLI and MCP server. No model or API key needed."""
import csv
import io
from pathlib import Path
import requests

SHEET = "https://docs.google.com/spreadsheets/d/1Kg6T-dJWaYx_JCPiRk3u0nBuAQcsCVRDPj1NFKP4WzM/gviz/tq?tqx=out:csv&headers=0&gid=368290478"
GLOSSARY = Path(__file__).parent / "data" / "security_glossary.csv"
LECTURE_DESCRIPTION = (
    "Look up the date, title, combined/separate session type, and tools for a numbered "
    "lecture in the 100xEngineers Cohort 8 course sheet (lectures 1 to 19). "
    "Use for lecture, class, or session schedule questions, including ordinal numbers "
    "like seventh or ten. In this course conversation, an unspecified class/session "
    "means Cohort 8. Do not use for another course such as Harvard CS50 or for general "
    "concept questions such as 'What is an API?'."
)
SECURITY_DESCRIPTION = (
    "Look up a term in this project's cybersecurity study glossary CSV and return its "
    "stored definition, category, and example. Use when the user explicitly asks for "
    "the project's glossary or study notes, even to check whether a term is missing. "
    "Accept a term or abbreviation such as MFA, SIEM, phishing, or least privilege. "
    "Do not use for general knowledge, arithmetic, course schedules, or live security advice."
)


def lookup_lecture(number: int) -> dict:
    if type(number) is not int or not 1 <= number <= 19:
        return {"error": "The lecture number must be an integer from 1 to 19."}
    try:
        response = requests.get(SHEET, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return {"error": "The course sheet could not be fetched. Please try again later."}
    rows = list(csv.reader(io.StringIO(response.text)))
    if not any(len(row) >= 4 and ". " in row[1] for row in rows):
        return {"error": "The course sheet did not return the expected lecture CSV."}
    for row in rows:
        if len(row) >= 4 and row[1].strip().startswith(f"{number}. "):
            return dict(zip(("date", "title", "type", "tools"), (cell.strip() for cell in row[:4])))
    return {"error": f"There is no lecture {number} in the current course sheet."}


def lookup_security_term(term: str) -> dict:
    if not isinstance(term, str) or not term.strip():
        return {"error": "Provide a non-empty glossary term."}
    query = " ".join(term.casefold().split())
    with GLOSSARY.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        names = [row["term"], *row["aliases"].split("|")]
        if query in (" ".join(name.casefold().split()) for name in names):
            return {key: row[key] for key in ("term", "category", "definition", "example")}
    return {"error": f"No entry for '{term}' in the project glossary.",
            "available_terms": [row["term"] for row in rows]}
